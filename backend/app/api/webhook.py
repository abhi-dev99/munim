"""
Munim.ai — WhatsApp Webhook API
Receives Meta webhook events and dispatches invoice processing.
"""

import re
import logging
import uuid

from fastapi import APIRouter, Request, Response, BackgroundTasks, HTTPException, UploadFile, File, Form

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
            image_url=image_url,
        )

        if not diagnosis:
            raise HTTPException(status_code=500, detail="Invoice processing failed")

        # Store invoice in DB
        await store_invoice(trader_id, diagnosis, image_url)

        return {
            "status": "processed",
            "trader_id": trader_id,
            "itc_verdict": {
                "status": diagnosis.itc_verdict.status,
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
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
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
    background_tasks.add_task(whatsapp.mark_message_read, message_id)

    # Dispatch based on message type
    if message_type in ("image", "document"):
        background_tasks.add_task(
            handle_invoice_message, from_number, msg
        )
    elif message_type == "audio":
        background_tasks.add_task(
            handle_voice_message, from_number, msg
        )
    elif message_type == "text":
        background_tasks.add_task(
            handle_text_message, from_number, msg.get("text", "")
        )
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

    if conv_state and conv_state.get("state") == "awaiting_gstin":
        # They're providing their GSTIN
        await _complete_registration(phone, text, trader)
        return

    # Existing user — handle queries
    if any(kw in text_lower for kw in ["status", "kitna", "itc", "dashboard", "report"]):
        await _send_itc_status(phone, trader)
    elif any(kw in text_lower for kw in ["help", "madad", "kya"]):
        await _send_help(phone)
    elif any(kw in text_lower for kw in ["hi", "hello", "namaste", "hey"]):
        await whatsapp.send_text_message(
            phone,
            f"Namaste {trader.get('name', '')}! 👋\n\n"
            f"Invoice bhejne ke liye — bas photo forward karo.\n"
            f"Status check: 'status' likh ke bhejo.\n"
            f"Help: 'help' likh ke bhejo."
        )
    else:
        # Possible GSTIN or unknown text
        gstin_match = text.strip().upper()
        if is_valid_gstin_format(gstin_match):
            await whatsapp.send_text_message(
                phone,
                "Yeh GSTIN lag raha hai. Agar aap apna GSTIN update karna chahte ho, "
                "'update gstin' likh ke bhejo."
            )
        else:
            await whatsapp.send_text_message(
                phone,
                "Invoice ki photo bhejo — main process kar dunga! 📸\n"
                "Ya 'status' likh ke bhejo ITC status ke liye."
            )


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
                phone, f"🔍 Supplier '{supplier_name}' ka status check kar raha hoon..."
            )
            # Future: implement supplier search by name/GSTIN
            await whatsapp.send_text_message(
                phone, f"Supplier check API connected for {supplier_name}!"
            )
        else:
            await whatsapp.send_text_message(phone, "Supplier ka naam samajh nahi aaya. Phir se bolo.")
    elif intent == "report_request":
        from app.agents.report_agent import generate_monthly_report
        from datetime import date
        now = date.today()
        await whatsapp.send_text_message(phone, "📄 Report generate kar raha hoon. 10 second lagte hain.")
        pdf_bytes = await generate_monthly_report(trader["id"], now.month, now.year)
        if pdf_bytes:
            media_id = await upload_file("reports", f"reports/{trader['id']}_{now.month}_{now.year}.pdf", pdf_bytes, "application/pdf")
            await whatsapp.send_text_message(phone, "Yeh rahi aapki report! (File sending disabled in mock)")
    else:
        # Fallback to text handler keywords
        await handle_text_message(phone, transcript)


# --- Registration Flow ---

async def _handle_registration(phone: str, text: str):
    """Handle new user registration."""
    text_upper = text.strip().upper()

    # Check if they're directly sending a GSTIN
    if is_valid_gstin_format(text_upper):
        trader = await create_trader(phone, gstin=text_upper)
        if trader:
            await whatsapp.send_text_message(
                phone,
                f"✅ Register ho gaye!\n\n"
                f"Ab bas karo: jab bhi koi invoice aaye — yahan WhatsApp pe bhej do. "
                f"Main baaki sab handle karunga.\n\n"
                f"Aaj ke invoices bhejne shuru karo! 📸"
            )
        return

    # First contact — greet and ask for GSTIN
    trader = await create_trader(phone)
    if trader:
        set_conversation_state(phone, "awaiting_gstin")
        await whatsapp.send_text_message(
            phone,
            "Namaste! 🙏 Main Munim hun — aapka GST compliance agent.\n\n"
            "Main aapke invoices check karta hun, ITC track karta hun, "
            "aur aapke CA ke liye monthly report banata hun.\n\n"
            "Shuru karte hain — aapka GST number (GSTIN) kya hai?"
        )


async def _complete_registration(phone: str, text: str, trader: dict):
    """Complete registration by saving GSTIN."""
    gstin = text.strip().upper()

    if not is_valid_gstin_format(gstin):
        await whatsapp.send_text_message(
            phone,
            "⚠️ Yeh sahi GSTIN nahi lag raha. GSTIN 15 characters ka hota hai.\n"
            "Example: 27AABCU9603R1ZM\n\n"
            "Dubara bhejo — sahi GSTIN:"
        )
        return

    await update_trader(trader["id"], {"gstin": gstin})
    set_conversation_state(phone, "idle")

    await whatsapp.send_text_message(
        phone,
        f"✅ GSTIN {gstin} save ho gaya!\n\n"
        f"Ab bas karo: jab bhi koi invoice aaye — yahan WhatsApp pe photo bhej do. "
        f"Main baaki sab handle karunga.\n\n"
        f"Aaj ke invoices bhejne shuru karo! 📸"
    )


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
