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
            invoice_data["supplier_email"] = inv_json.supplier_email
            invoice_data["supplier_phone"] = inv_json.supplier_phone
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

    # Check if existing trader hasn't completed onboarding (no GSTIN yet)
    if not trader.get("gstin"):
        # Resume the onboarding where we left off
        conv_state = get_conversation_state(phone)
        state_name = conv_state.get("state") if conv_state else None
        if state_name in ["awaiting_name", "awaiting_ca_number", "awaiting_language", "awaiting_gstin"]:
            await _process_registration_step(phone, text, trader, state_name)
        else:
            # State was lost (Redis restart / reload) — figure out where they are
            if not trader.get("language_pref") or (trader.get("language_pref") == "hi" and not trader.get("name")):
                set_conversation_state(phone, "awaiting_language")
                await whatsapp.send_text_message(
                    phone,
                    "Namaste! 🙏 Main Munim hun — aapka AI GST compliance agent.\n\n"
                    "Aap kis bhasha mein baat karna pasand karenge?\n\n"
                    "1️⃣ Hindi\n2️⃣ English\n3️⃣ Marathi\n4️⃣ Gujarati"
                )
            elif not trader.get("name"):
                set_conversation_state(phone, "awaiting_name")
                await whatsapp.send_text_message(phone, "Aapka naam aur business ka naam kya hai?")
            elif not trader.get("ca_whatsapp_number"):
                set_conversation_state(phone, "awaiting_ca_number")
                await whatsapp.send_text_message(phone, "Aapke CA ya accountant ka mobile number kya hai?")
            else:
                set_conversation_state(phone, "awaiting_gstin")
                await whatsapp.send_text_message(phone, "Aapka GSTIN number kya hai? (Example: 27AABCU9603R1ZM)")
        return

    # Check conversation state for registered traders mid-flow
    conv_state = get_conversation_state(phone)
    if conv_state:
        state_name = conv_state.get("state")
        if state_name in ["awaiting_name", "awaiting_ca_number", "awaiting_language", "awaiting_gstin"]:
            await _process_registration_step(phone, text, trader, state_name)
            return

    # Fully registered user — handle queries
    from app.services.gemini import understand_intent
    intent_data = await understand_intent(text_lower)
    intent = intent_data.get("intent", "unknown")

    if intent == "itc_status":
        await _send_itc_status(phone, trader)
    elif intent == "change_language":
        lang = intent_data.get("entities", {}).get("language_code", "hi")
        if not lang or lang not in ["en", "hi", "mr", "gu"]:
            lang = "hi"
        from app.services.supabase_client import update_trader
        await update_trader(trader["id"], {"language_pref": lang})
        if lang == "hi":
            await whatsapp.send_text_message(phone, "Theek hai, ab se main aapse Hindi mein baat karunga. 💬")
        elif lang == "mr":
            await whatsapp.send_text_message(phone, "Theek aahe, aathapasun mi tumchyashi Marathi madhe bolel. 💬")
        elif lang == "gu":
            await whatsapp.send_text_message(phone, "Barabar, have thi hu tamari sathe Gujarati ma vaat karish. 💬")
        else:
            await whatsapp.send_text_message(phone, "Got it, I will speak with you in English from now on. 💬")
    elif intent == "help":
        await _send_help(phone, trader)
    elif intent == "general_query":
        await _answer_general_query(phone, text, trader)
    elif any(kw in text_lower for kw in ["hi", "hello", "namaste", "hey"]):
        name = trader.get("name") or trader.get("business_name") or "dost"
        await whatsapp.send_text_message(
            phone,
            f"Namaste {name}! 👋\n\n"
            f"Invoice ka photo bhejo — main ITC check kar dunga.\n"
            f"Ya 'status' likh ke apna ITC summary dekho."
        )
    else:
        gstin_match = text.strip().upper()
        if is_valid_gstin_format(gstin_match):
            await whatsapp.send_text_message(
                phone,
                "Yeh GSTIN lag raha hai. Agar apna GSTIN update karna chahte ho toh 'update gstin' likh ke bhejo."
            )
        else:
            await _answer_general_query(phone, text, trader)


async def handle_voice_message(phone: str, msg: dict):
    """Handle incoming voice messages."""
    from app.services.whatsapp import download_media
    from app.config import get_settings
    from groq import AsyncGroq
    import io

    settings = get_settings()

    await whatsapp.send_text_message(phone, "🎤 Sun raha hun... ek minute.")

    media_id = msg.get("media_id")
    if not media_id:
        await whatsapp.send_text_message(phone, "Voice message load nahi ho paya.")
        return

    # 1. Download audio bytes from Meta
    audio_bytes, mime = await download_media(media_id)
    if not audio_bytes:
        await whatsapp.send_text_message(phone, "Voice message download karne me samasya aayi.")
        return

    # 2. Transcribe via Groq Whisper
    try:
        client = AsyncGroq(api_key=settings.groq_api_key)
        transcription = await client.audio.transcriptions.create(
            file=("audio.ogg", audio_bytes),
            model="whisper-large-v3"
        )
        transcribed_text = transcription.text.strip()
        logger.info(f"Voice Transcribed: {transcribed_text}")
    except Exception as e:
        logger.error(f"Groq Transcription Error: {e}")
        await whatsapp.send_text_message(phone, "Transcription me error aaya. Kripya type karein.")
        return

    if not transcribed_text:
        await whatsapp.send_text_message(phone, "Aapki aawaz samajh nahi aayi.")
        return

    # 3. Send transcribed text to general query handler
    trader = await get_trader_by_phone(phone)
    if trader:
        await _answer_general_query(phone, transcribed_text, trader)
    else:
        await whatsapp.send_text_message(phone, "Pehle register karo! 'Hi' likh ke bhejo.")


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
            invoice_data["supplier_email"] = inv_json.supplier_email
            invoice_data["supplier_phone"] = inv_json.supplier_phone
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
            inv_hash = GSTR2BReconciler.compute_hash(
                supplier_gstin,
                inv_number or str(uuid.uuid4())[:8],
                str(diagnosis.total_amount or 0),
            )
            invoice_data["invoice_hash"] = inv_hash
            
            from app.services.supabase_client import check_duplicate_invoice
            is_duplicate = await check_duplicate_invoice(inv_hash)
            if is_duplicate:
                invoice_data["itc_status"] = "DUPLICATE"
                invoice_data["status"] = "flagged"
                invoice_data["itc_amount_blocked"] = invoice_data.get("itc_amount_eligible", 0)
                invoice_data["itc_amount_eligible"] = 0
                invoice_data["itc_block_reason"] = "Duplicate invoice detected based on GSTIN, Invoice Number and Amount."

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
        err_str = str(e)
        logger.error(f"Invoice processing failed for {phone}: {e}", exc_info=True)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower() or "API_QUOTA_EXCEEDED" in err_str or "all API keys rate-limited" in err_str:
            await whatsapp.send_text_message(
                phone,
                "⚠️ Munim abhi thodi der ke liye available nahi hai.\n"
                "Kripya 2-3 minute baad dobara try karein. 🙏\n"
                "Aapki invoice safe hai — koi data miss nahi hogi!"
            )
        else:
            await whatsapp.send_text_message(
                phone,
                "⚠️ Invoice process mein problem aayi. Dubara try karo.\n"
                "Agar problem bani rahe — photo clear hai check karo aur dubara bhejo."
            )




# --- Registration Flow ---

async def _handle_registration(phone: str, text: str):
    """Handle new user registration."""
    trader = await create_trader(phone)
    if trader:
        set_conversation_state(phone, "awaiting_language")
        await whatsapp.send_text_message(
            phone,
            "Namaste! 🙏 Main Munim hun — aapka AI GST compliance agent.\n\n"
            "Kaunsi bhasha mein baat karein?\n\n"
            "1️⃣ Hindi\n2️⃣ English\n3️⃣ Marathi\n4️⃣ Gujarati"
        )

async def _process_registration_step(phone: str, text: str, trader: dict, state: str):
    """Handle the multi-step onboarding flow — powered by Gemini for context awareness."""
    from app.services.gemini import run_onboarding_llm

    current_lang = trader.get("language_pref") or "hi"

    # Call Gemini to intelligently parse what the user said
    result = await run_onboarding_llm(
        user_message=text,
        current_step=state,
        trader=trader,
        language=current_lang,
    )

    # Removed auto-language switching here because simple names (e.g. 'Aayush') 
    # were aggressively triggering an English language switch. We will strictly 
    # honor the language they picked in step 1.

    if result.get("status") == "reprompt":
        # Gemini determined the input was invalid — send its friendly reply and stay on this step
        await whatsapp.send_text_message(phone, result["reply"])
        return

    # status == "ok" — valid answer extracted, process it
    extracted = result.get("extracted", {})

    if state == "awaiting_language":
        lang = extracted.get("language_code", "hi")
        await update_trader(trader["id"], {"language_pref": lang})
        set_conversation_state(phone, "awaiting_name")

        next_questions = {
            "en": "Great! What's your name? (and your business name if different)",
            "mr": "उत्तम! तुमचे नाव काय आहे? (आणि व्यवसायाचे नाव वेगळे असल्यास ते पण)",
            "gu": "સરસ! તમારું નામ શું છે? (અને વ્યવસાયનું નામ અલગ હોય તો તે પણ)",
            "hi": "Bahut accha! Aapka naam kya hai? (aur business ka naam agar alag ho toh woh bhi)",
        }
        await whatsapp.send_text_message(phone, next_questions.get(lang, next_questions["hi"]))

    elif state == "awaiting_name":
        name = extracted.get("name", text.strip())
        business_name = extracted.get("business_name", name)
        await update_trader(trader["id"], {"name": name, "business_name": business_name})
        # Update local dict so next message gets correct language
        trader["language_pref"] = current_lang
        set_conversation_state(phone, "awaiting_ca_number")

        next_questions = {
            "en": f"Nice to meet you, {name}! 👋\n\nWhat's your CA or accountant's WhatsApp number?\n(So I can send them monthly reports. Type 'skip' if you don't have one yet.)",
            "mr": f"भेटून आनंद झाला, {name}! 👋\n\nतुमच्या CA किंवा अकाउंटंटचा WhatsApp नंबर काय आहे?\n('skip' टाइप करा जर आत्ता नाही.)",
            "gu": f"મળીને આનંદ થયો, {name}! 👋\n\nતમારા CA અથવા એકાઉન્ટન્ટનો WhatsApp નંબર શું છે?\n(જો અત્યારે નથી તો 'skip' ટાઇપ કરો.)",
            "hi": f"Mil ke khushi hui, {name}! 👋\n\nAapke CA ya accountant ka WhatsApp number kya hai?\n(Toh main unhe monthly reports bhej saku. Agar abhi nahi hai toh 'skip' likho.)",
        }
        await whatsapp.send_text_message(phone, next_questions.get(current_lang, next_questions["hi"]))

    elif state == "awaiting_ca_number":
        ca_number = extracted.get("ca_number", "")
        if ca_number and ca_number != "skip":
            await update_trader(trader["id"], {"ca_whatsapp_number": ca_number})
        set_conversation_state(phone, "awaiting_gstin")

        next_questions = {
            "en": "Almost done! 🎉\n\nWhat is your GSTIN number?\n(Example: 27AABCU9603R1ZM — 15 characters)",
            "mr": "जवळजवळ झाले! 🎉\n\nतुमचा GSTIN नंबर काय आहे?\n(उदाहरण: 27AABCU9603R1ZM — 15 अक्षरे)",
            "gu": "લગભગ થઈ ગયું! 🎉\n\nતમારો GSTIN નંબર શું છે?\n(ઉદાહરણ: 27AABCU9603R1ZM — 15 અક્ષરો)",
            "hi": "Bas thoda aur! 🎉\n\nAapka GSTIN number kya hai?\n(Example: 27AABCU9603R1ZM — 15 characters)",
        }
        await whatsapp.send_text_message(phone, next_questions.get(current_lang, next_questions["hi"]))

    elif state == "awaiting_gstin":
        gstin = extracted.get("gstin", "").upper().strip()
        # Final validation with our deterministic regex
        if not is_valid_gstin_format(gstin):
            error_msgs = {
                "en": f"⚠️ That doesn't look like a valid GSTIN.\n\nFormat: 2 digits + 5 letters + 4 digits + 1 letter + 1 digit + Z + 1 alphanumeric\nExample: 27AABCU9603R1ZM\n\nPlease try again:",
                "mr": f"⚠️ हा वैध GSTIN वाटत नाही.\n\nउदाहरण: 27AABCU9603R1ZM\n\nपुन्हा टाइप करा:",
                "gu": f"⚠️ આ માન્ય GSTIN લાગતું નથી.\n\nઉદાહરણ: 27AABCU9603R1ZM\n\nફરીથી ટાઇપ કરો:",
                "hi": f"⚠️ Yeh sahi GSTIN nahi lag raha.\n\nExample: 27AABCU9603R1ZM\n\nDubara try karo:",
            }
            await whatsapp.send_text_message(phone, error_msgs.get(current_lang, error_msgs["hi"]))
            return

        updated = await update_trader(trader["id"], {"gstin": gstin})
        
        if not updated:
            # If update fails (e.g. Unique constraint violation because they used the dummy example GSTIN)
            fail_msgs = {
                "en": f"⚠️ This GSTIN ({gstin}) is already registered to another user or an error occurred. Please enter YOUR unique GSTIN.",
                "mr": f"⚠️ हा GSTIN ({gstin}) आधीच दुसऱ्या वापरकर्त्याकडे नोंदणीकृत आहे. कृपया तुमचा स्वतःचा GSTIN एंटर करा.",
                "gu": f"⚠️ આ GSTIN ({gstin}) પહેલેથી જ બીજા વપરાશકર્તા સાથે નોંધાયેલ છે. કૃપા કરીને તમારો પોતાનો GSTIN દાખલ કરો.",
                "hi": f"⚠️ Yeh GSTIN ({gstin}) pehle se kisi aur user ke paas registered hai. Kripya apna real GSTIN enter karein.",
            }
            await whatsapp.send_text_message(phone, fail_msgs.get(current_lang, fail_msgs["hi"]))
            return

        set_conversation_state(phone, "idle")

        name = trader.get("name") or "dost"
        completion_msgs = {
            "en": f"✅ You're all set, {name}!\n\nGSTIN {gstin} saved.\n\n📸 Now just send me photos of your invoices and I'll check your ITC eligibility in seconds.\n\nSend your first invoice!",
            "mr": f"✅ सर्व तयार, {name}!\n\nGSTIN {gstin} सेव्ह झाला.\n\n📸 आता फक्त इनव्हॉइसचा फोटो पाठवा — मी ITC लगेच तपासेन.\n\nपहिला इनव्हॉइस पाठवा!",
            "gu": f"✅ બધું તૈયાર, {name}!\n\nGSTIN {gstin} સેવ થઈ ગયો.\n\n📸 હવે ફક્ત ઇન્વૉઇસ ફોટો મોકલો — હું ITC તુરંત ચેક કરીશ.\n\nપહેલો ઇન્વૉઇસ મોકલો!",
            "hi": f"✅ Sab set ho gaya, {name}!\n\nGSTIN {gstin} save ho gaya.\n\n📸 Ab bas invoice ka photo bhejo — main ITC eligibility 10 second mein check kar dunga.\n\nPehla invoice bhejo!",
        }
        await whatsapp.send_text_message(phone, completion_msgs.get(current_lang, completion_msgs["hi"]))

        email_msgs = {
            "en": "📧 You've also been assigned an official Munim-AI email address:\n\n*11c6f792d6e48b4d78d2@cloudmailin.net*\n\nYou can give this to your vendors so that all invoices sent by them directly sync with your dashboard!",
            "mr": "📧 तुम्हाला अधिकृत मुनीम-AI ईमेल दिला गेला आहे:\n\n*11c6f792d6e48b4d78d2@cloudmailin.net*\n\nतुम्ही हे तुमच्या विक्रेत्यांना देऊ शकता जेणेकरून त्यांचे इनव्हॉइस थेट डॅशबोर्डवर सिंक होतील!",
            "gu": "📧 તમને સત્તાવાર મુનિમ-AI ઈમેલ આપવામાં આવ્યો છે:\n\n*11c6f792d6e48b4d78d2@cloudmailin.net*\n\nતમે આ તમારા વિક્રેતાઓને આપી શકો છો જેથી તેમના ઇન્વૉઇસ સીધા ડેશબોર્ડ પર સિંક થાય!",
            "hi": "📧 Aapko ek official Munim-AI email address bhi diya gaya hai:\n\n*11c6f792d6e48b4d78d2@cloudmailin.net*\n\nAap yeh apne vendors ko de sakte hain taaki unke bheje gaye invoices seedhe dashboard se sync ho jayein!"
        }
        await whatsapp.send_text_message(phone, email_msgs.get(current_lang, email_msgs["hi"]))

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


async def _send_help(phone: str, trader: dict = None):
    """Send help message."""
    lang = trader.get("language_pref", "hi") if trader else "hi"
    if lang == "en":
        msg = (
            "Munim AI — here's what I can do:\n\n"
            "📸 Send an invoice photo → I'll check your ITC eligibility instantly\n"
            "📊 Type 'status' → Get your ITC summary\n"
            "🎤 Send a voice note → I'll understand and respond\n\n"
            "Just send your invoices here. I handle the rest."
        )
    elif lang == "mr":
        msg = (
            "Munim AI — मी काय करतो:\n\n"
            "📸 इनव्हॉइसचा फोटो पाठवा → मी ITC पात्रता लगेच तपासेन\n"
            "📊 'status' टाइप करा → ITC सारांश मिळवा\n"
            "🎤 व्हॉइस नोट पाठवा → मी समजून उत्तर देईन\n\n"
            "फक्त इनव्हॉइस पाठवत राहा."
        )
    elif lang == "gu":
        msg = (
            "Munim AI — હું શું કરી શકું:\n\n"
            "📸 ઇન્વૉઇસ ફોટો મોકલો → હું ITC પાત્રતા તુરંત ચેક કરીશ\n"
            "📊 'status' ટાઇપ કરો → ITC સારાંશ મેળવો\n"
            "🎤 વૉઇસ નોટ મોકલો → હું સમજી જઈશ\n\n"
            "ફક્ત ઇન્વૉઇસ મોકલતા રહો."
        )
    else:
        msg = (
            "Munim AI — main kya kar sakta hoon:\n\n"
            "📸 Invoice ka photo bhejo → Main ITC eligibility check karunga\n"
            "📊 'status' likho → Apna ITC summary dekho\n"
            "🎤 Voice note bhejo → Main samajh lunga\n\n"
            "Bas invoices bhejte raho. Baaki sab main karunga."
        )
    await whatsapp.send_text_message(phone, msg)


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
