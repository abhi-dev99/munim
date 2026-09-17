"""
Munim.ai — WhatsApp Webhook API
Receives Meta webhook events and dispatches invoice processing.
"""

import re
import logging
import uuid

from fastapi import APIRouter, Request, Response, HTTPException, UploadFile, File, Form
import asyncio

from app.config import get_settings
from app.services import whatsapp
from app.services.redis_cache import (
    get_conversation_state,
    set_conversation_state,
    check_rate_limit,
)
from app.services.supabase_client import (
    get_supabase,
    get_trader_by_phone,
    create_trader,
    update_trader,
    upload_file,
    store_invoice,
)
from app.services.gstin import is_valid_gstin_format
from app.agents.invoice_agent import process_invoice
from app.models.invoice import ITCStatus
from app.domain.reconciler import GSTR2BReconciler

logger = logging.getLogger(__name__)

settings = get_settings()

router = APIRouter(prefix="/api/v1", tags=["webhook"])

# GSTIN regex: 2 digits + 5 alpha + 4 digits + 1 alpha + 1 alphanumeric + Z + 1 alphanumeric
GSTIN_REGEX = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z\d]$")


@router.post("/webhook/upload-invoice")
async def upload_invoice_direct(
    file: UploadFile = File(...),
    trader_id: str = Form(...),
):
    """
    Direct invoice upload from the Trader PWA (no WhatsApp).
    Accepts image or PDF, runs the full LangGraph pipeline, returns diagnosis.
    """
    try:
        file_bytes = await file.read()
        mime_type = file.content_type or "image/jpeg"

        # Upload to Supabase Storage first
        filename = f"invoices/{trader_id}/{uuid.uuid4()}_{file.filename or 'invoice'}"
        image_url = await upload_file("invoices", filename, file_bytes, mime_type)

        # Run the full invoice processing pipeline
        diagnosis = await process_invoice(
            trader_id=trader_id,
            image_bytes=file_bytes,
            mime_type=mime_type,
        )

        if not diagnosis:
            raise HTTPException(status_code=500, detail="Invoice processing failed")

        # Store invoice in DB — build the same dict structure as WhatsApp handler
        inv_json = diagnosis.invoice_json
        invoice_data = {
            "trader_id": trader_id,
            "image_url": image_url,
            "status": "validated" if diagnosis.itc_verdict.status == ITCStatus.CONFIRMED else "flagged",
            "itc_status": diagnosis.itc_verdict.status.value,
            "itc_amount_eligible": diagnosis.itc_verdict.itc_amount,
            "itc_amount_blocked": diagnosis.itc_verdict.itc_blocked,
            "itc_block_reason": diagnosis.itc_verdict.reason,
            "processing_duration_ms": diagnosis.processing_duration_ms,
        }
        if diagnosis.gstr2b_match:
            invoice_data["gstr2b_match_status"] = diagnosis.gstr2b_match.status.value
            invoice_data["gstr2b_match_confidence"] = diagnosis.gstr2b_match.confidence
        if inv_json:
            invoice_data["gstin_supplier"] = inv_json.gstin_supplier
            invoice_data["gstin_buyer"] = inv_json.gstin_buyer
            invoice_data["invoice_number"] = inv_json.invoice_number
            invoice_data["invoice_date"] = inv_json.invoice_date
            invoice_data["supplier_name"] = inv_json.supplier_name
            invoice_data["taxable_amount"] = inv_json.total_taxable_amount
            invoice_data["total_amount"] = inv_json.total_amount
            invoice_data["cgst_amount"] = sum((li.cgst_amount or 0) for li in inv_json.line_items)
            invoice_data["sgst_amount"] = sum((li.sgst_amount or 0) for li in inv_json.line_items)
            invoice_data["igst_amount"] = sum((li.igst_amount or 0) for li in inv_json.line_items)
        if diagnosis.fraud_result:
            invoice_data["fraud_score"] = diagnosis.fraud_result.total_score
        stored_invoice = await store_invoice(invoice_data)

        # Store line items
        if stored_invoice and inv_json and inv_json.line_items:
            from app.services.supabase_client import store_invoice_line_items
            await store_invoice_line_items(stored_invoice["id"], inv_json.line_items, diagnosis.hsn_validations)

        return {
            "status": "processed",
            "invoice_id": stored_invoice["id"] if stored_invoice else None,
            "trader_id": trader_id,
            "itc_verdict": {
                "status": diagnosis.itc_verdict.status.value,
                "itc_amount": diagnosis.itc_verdict.itc_amount,
                "itc_blocked": diagnosis.itc_verdict.itc_blocked,
                "reason": diagnosis.itc_verdict.reason,
            },
            "diagnosis_hi": diagnosis.diagnosis_hi,
            "diagnosis_en": diagnosis.diagnosis_en,
            "action_items": diagnosis.action_items,
            "processing_duration_ms": diagnosis.processing_duration_ms,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Direct invoice upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/webhook")
async def verify_webhook(request: Request):
    """Meta webhook verification (GET challenge-response)."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.meta_verify_token:
        logger.info("Webhook verified successfully")
        return Response(content=challenge, media_type="text/plain")
    else:
        raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_webhook(request: Request):
    """Receive and process incoming WhatsApp messages."""
    body = await request.json()

    # Parse the message
    msg = whatsapp.parse_webhook_message(body)
    if not msg:
        return {"status": "ok"}  # Not a message event (could be status update)

    from_number = msg["from_number"]
    message_id = msg["message_id"]
    message_type = msg["message_type"]

    # Rate limiting
    if not check_rate_limit(f"wa:{from_number}", max_requests=20, window_seconds=60):
        await whatsapp.send_text_message(
            from_number, "Thoda ruko bhai! Bahut jaldi messages aa rahe hain. Ek minute ruko."
        )
        return {"status": "rate_limited"}

    # Mark as read
    asyncio.create_task(whatsapp.mark_message_read(message_id))

    # Dispatch based on message type
    if message_type in ("image", "document"):
        asyncio.create_task(handle_invoice_message(from_number, msg))
    elif message_type == "audio":
        asyncio.create_task(handle_voice_message(from_number, msg))
    elif message_type == "text":
        asyncio.create_task(handle_text_message(from_number, msg.get("text", "")))
    else:
        logger.info(f"Ignoring message type: {message_type}")

    return {"status": "ok"}


async def handle_text_message(phone: str, text: str):
    """Handle text messages — registration flow, status queries, etc."""
    text_lower = text.strip().lower()

    # Check if trader exists
    trader = await get_trader_by_phone(phone)

    if not trader:
        # New user — start registration
        await _handle_registration(phone, text)
        return

    # Check conversation state
    conv_state = get_conversation_state(phone)
    if conv_state:
        state_name = conv_state.get("state")
        if state_name in ["awaiting_name", "awaiting_ca_number", "awaiting_language", "awaiting_gstin"]:
            await _process_registration_step(phone, text, trader, state_name)
            return

    # Existing user — handle queries via Gemini intent router
    from app.services.gemini import understand_intent
    intent_data = await understand_intent(text_lower)
    intent = intent_data.get("intent", "unknown")

    if intent == "itc_status":
        await _send_itc_status(phone, trader)
    elif intent == "help":
        await _send_help(phone)
    elif intent == "general_query":
        await _answer_general_query(phone, text, trader)
    elif any(kw in text_lower for kw in ["hi", "hello", "namaste", "hey"]):
        await whatsapp.send_text_message(
            phone,
            f"Namaste {trader.get('name', '')}! 👋\n\n"
            f"Invoice bhejne ke liye — bas photo forward karo.\n"
            f"Kuch bhi poochna ho — bas text type karo ya voice note bhejo!"
        )
    else:
        gstin_match = text.strip().upper()
        if is_valid_gstin_format(gstin_match):
            await whatsapp.send_text_message(
                phone,
                "Yeh GSTIN lag raha hai. Agar aap apna GSTIN update karna chahte ho, 'update gstin' likh ke bhejo."
            )
        else:
            await _answer_general_query(phone, text, trader)


async def handle_invoice_message(phone: str, msg: dict):
    """Handle image/document messages — process as invoice."""
    trader = await get_trader_by_phone(phone)

    if not trader:
        await whatsapp.send_text_message(
            phone,
            "Pehle register karo! 'Hi' likh ke bhejo."
        )
        return

    # Send acknowledgment
    await whatsapp.send_text_message(
        phone, "📄 Invoice mil gaya! Processing ho raha hai... ek minute."
    )

    try:
        # Download media from WhatsApp
        media_id = msg.get("media_id")
        if not media_id:
            await whatsapp.send_text_message(phone, "⚠️ Image download nahi ho paya. Dubara bhejo.")
            return

        image_bytes, mime_type = await whatsapp.download_media(media_id)
        if not image_bytes:
            await whatsapp.send_text_message(phone, "⚠️ Image download nahi ho paya. Dubara bhejo.")
            return

        # Upload to Supabase Storage
        file_ext = "jpg" if "jpeg" in (mime_type or "") or "jpg" in (mime_type or "") else "pdf"
        storage_path = f"invoices/{trader['id']}/{uuid.uuid4()}.{file_ext}"
        image_url = await upload_file("invoices", storage_path, image_bytes, mime_type)

        # Process through LangGraph agent
        diagnosis = await process_invoice(
            trader_id=trader["id"],
            image_bytes=image_bytes,
            mime_type=mime_type or "image/jpeg",
        )

        # Store invoice in DB
        invoice_data = {
            "trader_id": trader["id"],
            "image_url": image_url,
            "status": "validated" if diagnosis.itc_verdict.status == ITCStatus.CONFIRMED else "flagged",
            "itc_status": diagnosis.itc_verdict.status.value,
            "itc_amount_eligible": diagnosis.itc_verdict.itc_amount,
            "itc_amount_blocked": diagnosis.itc_verdict.itc_blocked,
            "itc_block_reason": diagnosis.itc_verdict.reason,
            "processing_duration_ms": diagnosis.processing_duration_ms,
        }

        # Add GSTR-2B reconciliation status
        if diagnosis.gstr2b_match:
            invoice_data["gstr2b_match_status"] = diagnosis.gstr2b_match.status.value
            invoice_data["gstr2b_match_confidence"] = diagnosis.gstr2b_match.confidence

        # Add extracted fields if available
        inv_json = diagnosis.invoice_json
        if inv_json:
            invoice_data["gstin_supplier"] = inv_json.gstin_supplier
            invoice_data["gstin_buyer"] = inv_json.gstin_buyer
            invoice_data["invoice_number"] = inv_json.invoice_number
            invoice_data["invoice_date"] = inv_json.invoice_date
            invoice_data["supplier_name"] = inv_json.supplier_name
            invoice_data["taxable_amount"] = inv_json.total_taxable_amount
            invoice_data["total_amount"] = inv_json.total_amount
            invoice_data["cgst_amount"] = sum(
                (li.cgst_amount or 0) for li in inv_json.line_items
            )
            invoice_data["sgst_amount"] = sum(
                (li.sgst_amount or 0) for li in inv_json.line_items
            )
            invoice_data["igst_amount"] = sum(
                (li.igst_amount or 0) for li in inv_json.line_items
            )

        # Add invoice hash for duplicate detection
        supplier_gstin = inv_json.gstin_supplier if inv_json else ""
        inv_number = inv_json.invoice_number if inv_json else ""
        if supplier_gstin:
            invoice_data["invoice_hash"] = GSTR2BReconciler.compute_hash(
                supplier_gstin,
                inv_number or str(uuid.uuid4())[:8],
                str(diagnosis.total_amount or 0),
            )

        # Add fraud score
        if diagnosis.fraud_result:
            invoice_data["fraud_score"] = diagnosis.fraud_result.total_score
            invoice_data["fraud_signals"] = {
                s.signal_name: {"triggered": s.triggered, "detail": s.detail}
                for s in diagnosis.fraud_result.signals
            }

        stored_invoice = await store_invoice(invoice_data)

        # Store line items with HSN validation results
        if stored_invoice and inv_json and inv_json.line_items:
            from app.services.supabase_client import store_invoice_line_items
            await store_invoice_line_items(
                stored_invoice["id"],
                inv_json.line_items,
                diagnosis.hsn_validations,
            )

        # Auto-create supplier and link to trader (builds compliance graph)
        if supplier_gstin:
            from app.services.supabase_client import get_or_create_supplier, link_supplier_to_trader
            supplier = await get_or_create_supplier(
                supplier_gstin,
                legal_name=diagnosis.supplier_name,
            )
            if supplier:
                invoice_data_supplier_id = supplier["id"]
                if stored_invoice:
                    # Update invoice with supplier_id FK
                    db = get_supabase()
                    db.table("invoices").update(
                        {"supplier_id": supplier["id"]}
                    ).eq("id", stored_invoice["id"]).execute()
                await link_supplier_to_trader(trader["id"], supplier["id"])

        # Send diagnosis to trader
        await whatsapp.send_text_message(phone, diagnosis.diagnosis_hi)

        logger.info(
            f"Invoice processed for {phone} in {diagnosis.processing_duration_ms}ms — "
            f"ITC: {diagnosis.itc_verdict.status.value}"
        )

    except Exception as e:
        logger.error(f"Invoice processing failed for {phone}: {e}", exc_info=True)
        await whatsapp.send_text_message(
            phone,
            "⚠️ Invoice process mein problem aayi. Dubara try karo.\n"
            "Agar problem bani rahe — photo clear hai check karo aur dubara bhejo."
        )


async def handle_voice_message(phone: str, msg: dict):
    """Handle voice notes — transcribe and acknowledge."""
    from app.services.gemini import transcribe_voice_note

    trader = await get_trader_by_phone(phone)
    if not trader:
        await whatsapp.send_text_message(phone, "Pehle register karo! 'Hi' likh ke bhejo.")
        return

    media_id = msg.get("media_id")
    if not media_id:
        return

    audio_bytes, mime_type = await whatsapp.download_media(media_id)
    if not audio_bytes:
        await whatsapp.send_text_message(phone, "⚠️ Audio sun nahi paya. Text mein likh ke bhejo.")
        return

    transcript = await transcribe_voice_note(audio_bytes, mime_type or "audio/ogg")
    if not transcript:
        await whatsapp.send_text_message(
            phone, "⚠️ Audio samajh nahi aaya. Text mein likh ke bhejo."
        )
        return

    await whatsapp.send_text_message(
        phone, f"🎤 Aapne kaha: \"{transcript}\"\n\n⚙️ Intent process kar raha hoon..."
    )

    from app.services.gemini import understand_intent
    parsed = await understand_intent(transcript)
    intent = parsed.get("intent", "unknown")

    if intent == "itc_status":
        await _send_itc_status(phone, trader)
    elif intent == "supplier_check":
        supplier_name = parsed.get("entities", {}).get("supplier_name", "")
        if supplier_name:
            await whatsapp.send_text_message(
                phone, f"🔍 '{supplier_name}' ka status check kar raha hoon..."
            )
            await _send_supplier_check(phone, trader, supplier_name)
        else:
            await whatsapp.send_text_message(phone, "Supplier ka naam samajh nahi aaya. Phir se bolo.")
    elif intent == "report_request":
        from app.agents.report_agent import generate_munim_report, send_report_to_trader
        from datetime import date
        now = date.today()
        await whatsapp.send_text_message(phone, "📄 Munim Report bana raha hoon. 15 second lagte hain...")
        pdf_url = await generate_munim_report(trader["id"], now.month, now.year)
        if pdf_url:
            await send_report_to_trader(trader["id"], pdf_url)
        else:
            await whatsapp.send_text_message(phone, "Report generate karne mein dikkat aayi. CA se contact karo.")
    elif intent == "general_query":
        await _answer_general_query(phone, transcript, trader)
    else:
        # Fallback to general query for voice notes too!
        await _answer_general_query(phone, transcript, trader)


# --- Registration Flow ---

async def _handle_registration(phone: str, text: str):
    """Handle new user registration."""
    trader = await create_trader(phone)
    if trader:
        set_conversation_state(phone, "awaiting_language")
        await whatsapp.send_text_message(
            phone,
            "Namaste! 🙏 Main Munim hun — aapka AI GST compliance agent.\n\n"
            "Aap kis bhasha mein baat karna pasand karenge? (Hindi / English / Marathi / Gujarati)"
        )

async def _process_registration_step(phone: str, text: str, trader: dict, state: str):
    """Handle the multi-step onboarding flow."""
    text_clean = text.strip()
    
    if state == "awaiting_language":
        text_lower = text_clean.lower()
        if "english" in text_lower or "en" in text_lower:
            lang = "en"
        elif "marathi" in text_lower:
            lang = "mr"
        elif "gujarati" in text_lower:
            lang = "gu"
        else:
            lang = "hi"
            
        await update_trader(trader["id"], {"language_pref": lang})
        set_conversation_state(phone, "awaiting_name")
        
        if lang == "en":
            msg = "Awesome! What is your name and business name?"
        elif lang == "mr":
            msg = "उत्तम! तुमचे नाव आणि व्यवसायाचे नाव काय आहे?"
        elif lang == "gu":
            msg = "સરસ! તમારું નામ અને વ્યવસાયનું નામ શું છે?"
        else:
            msg = "Bahut badhiya! Aapka naam aur business ka naam kya hai?"
        await whatsapp.send_text_message(phone, msg)

    elif state == "awaiting_name":
        await update_trader(trader["id"], {"name": text_clean, "business_name": text_clean})
        set_conversation_state(phone, "awaiting_ca_number")
        lang = trader.get("language_pref", "hi")
        if lang == "en":
            msg = "What is your CA or accountant's mobile number? (So I can send them reports)"
        elif lang == "mr":
            msg = "तुमच्या CA किंवा अकाउंटंटचा मोबाईल नंबर काय आहे? (जेणेकरून मी त्यांना अहवाल पाठवू शकेन)"
        elif lang == "gu":
            msg = "તમારા CA અથવા એકાઉન્ટન્ટનો મોબાઈલ નંબર શું છે? (જેથી હું તેમને રિપોર્ટ મોકલી શકું)"
        else:
            msg = "Aapke CA ya accountant ka mobile number kya hai? (Toh main reports unhe bhej saku)"
        await whatsapp.send_text_message(phone, msg)
    
    elif state == "awaiting_ca_number":
        await update_trader(trader["id"], {"ca_whatsapp_number": text_clean})
        set_conversation_state(phone, "awaiting_gstin")
        lang = trader.get("language_pref", "hi")
        if lang == "en":
            msg = "What is your GSTIN number?"
        elif lang == "mr":
            msg = "तुमचा GSTIN नंबर काय आहे?"
        elif lang == "gu":
            msg = "તમારો GSTIN નંબર શું છે?"
        else:
            msg = "Aapka GSTIN number kya hai?"
        await whatsapp.send_text_message(phone, msg)
        
    elif state == "awaiting_gstin":
        gstin = text_clean.upper()
        if not is_valid_gstin_format(gstin):
            lang = trader.get("language_pref", "hi")
            if lang == "en":
                msg = "⚠️ Invalid GSTIN. Example: 27AABCU9603R1ZM\n\nSend again:"
            elif lang == "mr":
                msg = "⚠️ हा वैध GSTIN वाटत नाही. उदाहरण: 27AABCU9603R1ZM\n\nपुन्हा पाठवा:"
            elif lang == "gu":
                msg = "⚠️ આ માન્ય GSTIN લાગતું નથી. ઉદાહરણ: 27AABCU9603R1ZM\n\nફરીથી મોકલો:"
            else:
                msg = "⚠️ Yeh sahi GSTIN nahi lag raha. Example: 27AABCU9603R1ZM\n\nDubara bhejo:"
            await whatsapp.send_text_message(phone, msg)
            return
            
        await update_trader(trader["id"], {"gstin": gstin})
        set_conversation_state(phone, "idle")
        lang = trader.get("language_pref", "hi")
        if lang == "en":
            msg = f"✅ GSTIN {gstin} saved!\n\nJust send photos of your invoices here and I'll handle the rest.\n\nSend your first invoice! 📸"
        elif lang == "mr":
            msg = f"✅ GSTIN {gstin} सेव्ह झाला!\n\nआता फक्त तुमचे इनव्हॉइसचे फोटो येथे पाठवा आणि मी बाकी सर्व हाताळेन.\n\nतुमचे पहिले इनव्हॉइस पाठवा! 📸"
        elif lang == "gu":
            msg = f"✅ GSTIN {gstin} સેવ થઈ ગયો છે!\n\nહવે ફક્ત તમારા ઇન્વૉઇસના ફોટા અહીં મોકલો અને હું બાકીનું સંભાળીશ.\n\nતમારું પહેલું ઇન્વૉઇસ મોકલો! 📸"
        else:
            msg = f"✅ GSTIN {gstin} save ho gaya!\n\nAb bas karo: jab bhi koi invoice aaye — yahan WhatsApp pe photo bhej do. Main baaki sab handle karunga.\n\nAaj ke invoices bhejne shuru karo! 📸"
        await whatsapp.send_text_message(phone, msg)

async def _answer_general_query(phone: str, text: str, trader: dict):
    from app.services.supabase_client import get_itc_summary, get_recent_invoices
    from app.services.gemini import answer_trader_question
    buckets = await get_itc_summary(trader["id"])
    recent = await get_recent_invoices(trader["id"], limit=3)
    
    context_data = {
        "business_name": trader.get("business_name"),
        "itc_summary_totals": buckets,
        "recent_invoices": recent
    }
    answer = await answer_trader_question(text, context_data)
    await whatsapp.send_text_message(phone, answer)


async def _send_itc_status(phone: str, trader: dict):
    """Send ITC status summary to trader."""
    from app.services.supabase_client import get_itc_summary

    buckets = await get_itc_summary(trader["id"])
    if not buckets:
        await whatsapp.send_text_message(
            phone,
            "Abhi tak koi invoice process nahi hua. Pehle invoices bhejo! 📸"
        )
        return

    confirmed = buckets.get("confirmed", 0)
    blocked = buckets.get("fixable_blocked", 0)
    at_risk = buckets.get("at_risk", 0)
    missed = buckets.get("missed", 0)
    total_recovery = blocked + at_risk + missed

    msg = (
        f"📊 Aapka ITC Status:\n\n"
        f"✅ Confirmed ITC: ₹{confirmed:,.0f}\n"
        f"⚠️ Blocked ITC: ₹{blocked:,.0f} (fix ho sakte hain)\n"
        f"🚨 At-Risk ITC: ₹{at_risk:,.0f} (supplier issues)\n"
        f"💰 Missed ITC: ₹{missed:,.0f} (unclaimed)\n\n"
        f"➡️ Total recovery possible: ₹{total_recovery:,.0f}\n\n"
        f"Details ke liye dashboard dekho. Sabse badi problem pehle fix karein!"
    )
    await whatsapp.send_text_message(phone, msg)


async def _send_help(phone: str):
    """Send help message."""
    await whatsapp.send_text_message(
        phone,
        "🤖 Munim Help:\n\n"
        "📸 Invoice bhejo → Main ITC check karunga\n"
        "📊 'status' → ITC ka summary\n"
        "🎤 Voice note → Main sun lunga\n\n"
        "Bas itna hi! Invoice bhejte raho, main sab track karunga."
    )


async def _send_supplier_check(phone: str, trader: dict, supplier_name: str):
    """Look up a supplier by name and send health status to trader."""
    db = get_supabase()

    try:
        # Search suppliers linked to this trader by name (case-insensitive)
        links = db.table("supplier_trader_links").select(
            "supplier_id, suppliers(id, legal_name, gstin, health_score, taxpayer_type, last_verified_at)"
        ).eq("trader_id", trader["id"]).execute()

        if not links.data:
            await whatsapp.send_text_message(
                phone,
                f"❌ '{supplier_name}' aapki supplier list mein nahi mila.\n"
                "Pehle unka invoice process karo, phir woh automatically track hoga."
            )
            return

        # Find best match by supplier name (case-insensitive partial match)
        supplier_name_lower = supplier_name.lower()
        matched = None
        for link in links.data:
            sup = link.get("suppliers", {})
            if not sup:
                continue
            if supplier_name_lower in (sup.get("legal_name") or "").lower():
                matched = sup
                break

        if not matched:
            # List all supplier names as hint
            names = [link["suppliers"]["legal_name"] for link in links.data if link.get("suppliers")]
            await whatsapp.send_text_message(
                phone,
                f"❌ '{supplier_name}' nahi mila.\n\n"
                f"Aapke suppliers: {', '.join(names[:5])}\n"
                "Sahi naam bolo."
            )
            return

        # Get active flags
        flags_resp = db.table("supplier_flags").select("flag_type, detail").eq(
            "supplier_id", matched["id"]
        ).eq("is_active", True).execute()
        flags = flags_resp.data or []

        health = matched.get("health_score", 100)
        health_emoji = "✅" if health >= 70 else ("⚠️" if health >= 40 else "🚨")

        msg = (
            f"{health_emoji} *{matched.get('legal_name', supplier_name)}*\n\n"
            f"GSTIN: {matched.get('gstin', 'Unknown')}\n"
            f"Type: {matched.get('taxpayer_type', 'Regular')}\n"
            f"Health Score: {health}/100\n"
        )

        if flags:
            flag_text = "\n".join(f"• {f['flag_type']}: {f.get('detail', '')}" for f in flags)
            msg += f"\n⚠️ Issues found:\n{flag_text}\n\nIn supplier ke saath payment se pehle CA se consult karo."
        else:
            msg += "\n✅ Koi active issues nahi hain. Safe hai!"

        await whatsapp.send_text_message(phone, msg)

    except Exception as e:
        logger.error(f"Supplier check failed: {e}")
        await whatsapp.send_text_message(phone, "Supplier check mein dikkat aayi. Dobara try karo.")
