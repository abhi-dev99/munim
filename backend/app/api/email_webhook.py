import logging
import uuid
import asyncio

from fastapi import APIRouter, Request, Response, HTTPException, UploadFile, File, Form
from app.services.supabase_client import (
    get_trader_by_inbound_email,
    upload_file,
    store_invoice,
)
from app.agents.invoice_agent import process_invoice
from app.models.invoice import ITCStatus
from app.services import whatsapp
from app.services.llm_router import llm_router, LLMTask
from app.domain.reconciler import GSTR2BReconciler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhook/email", tags=["email_webhook"])

async def generate_informal_notification(language_pref: str, supplier_name: str, total_amount: float) -> str:
    lang_map = {"hi": "Hindi", "mr": "Marathi", "gu": "Gujarati", "en": "English"}
    lang_name = lang_map.get(language_pref, "Hindi")
    
    prompt = f"""
    You are Munim, an AI assistant for a shopkeeper. 
    Write a very short, slightly informal WhatsApp notification in {lang_name} informing the shopkeeper that an invoice from '{supplier_name}' for ₹{total_amount} was just automatically received via Email and processed successfully. Let them know it was also forwarded to their CA.
    Do not use formal corporate language. Keep it brief and friendly. Use an emoji or two.
    """
    return await llm_router.generate_text(prompt, context={}, task=LLMTask.SUMMARY)

async def generate_formal_notification(trader_name: str, supplier_name: str, invoice_number: str, invoice_date: str, total_amount: float, itc_status: str) -> str:
    msg = f"""*Invoice Alert: {trader_name}*

Attached is the processed invoice via email webhook:

  • Client: {trader_name}
  • Supplier: {supplier_name}
  • Invoice No.: {invoice_number}
  • Date: {invoice_date}
  • Amount: ₹{total_amount}
  • ITC Status: {itc_status}

Please review and confirm receipt."""
    return msg

@router.post("")
async def receive_email_webhook(request: Request):
    """
    Webhook endpoint to receive SendGrid Inbound Parse.
    SendGrid sends multipart/form-data containing email fields and attachments.
    """
    try:
        # CloudMailin JSON Normalized format
        payload = await request.json()
        
        # CloudMailin puts headers in 'headers' and envelope data in 'envelope'
        headers = payload.get("headers", {})
        envelope = payload.get("envelope", {})
        
        to_email = envelope.get("to", "") or headers.get("to", "")
        from_email = envelope.get("from", "") or headers.get("from", "")
        subject = headers.get("subject", "")
        
        logger.info(f"Received email from {from_email} to {to_email} with subject: {subject}")
        
        # Clean the 'to' email (e.g., "Name <email@domain.com>")
        import re
        import base64
        email_match = re.search(r'<([^>]+)>', to_email)
        if email_match:
            to_email_clean = email_match.group(1).lower()
        else:
            to_email_clean = to_email.lower().strip()
            
        # Find trader by inbound_email
        trader = await get_trader_by_inbound_email(to_email_clean)
        if not trader:
            logger.warning(f"No trader found for inbound email: {to_email_clean}")
            return Response(status_code=200) # 2xx to stop retrying
            
        # Extract attachment (usually PDF)
        attachments = payload.get("attachments", [])
        if not attachments:
            logger.info("No attachments found in email.")
            return Response(status_code=200)
            
        # Get the first attachment
        file = attachments[0]
        file_content_b64 = file.get("content", "")
        
        if not file_content_b64:
            logger.info("No valid file content found in attachment.")
            return Response(status_code=200)
            
        file_bytes = base64.b64decode(file_content_b64)
        mime_type = file.get("content_type", "application/pdf")
        file_name = file.get("file_name", "invoice.pdf")
        
        # Upload to Supabase Storage
        file_ext = "pdf" if "pdf" in mime_type else "jpg"
        storage_path = f"invoices/{trader['id']}/{uuid.uuid4()}_email.{file_ext}"
        image_url = await upload_file("invoices", storage_path, file_bytes, mime_type)
        
        # Process invoice
        diagnosis = await process_invoice(
            trader_id=trader["id"],
            image_bytes=file_bytes,
            mime_type=mime_type,
        )
        
        if not diagnosis:
            logger.error("Invoice processing failed via email.")
            return Response(status_code=200)
            
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

        inv_json = diagnosis.invoice_json
        supplier_name = "Unknown Supplier"
        total_amount = 0.0
        
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
            
            supplier_name = inv_json.supplier_name or supplier_name
            total_amount = inv_json.total_amount or total_amount

            # Hash
            supplier_gstin = inv_json.gstin_supplier
            inv_number = inv_json.invoice_number
            if supplier_gstin:
                invoice_data["invoice_hash"] = GSTR2BReconciler.compute_hash(
                    supplier_gstin,
                    inv_number or str(uuid.uuid4())[:8],
                    str(diagnosis.total_amount or 0),
                )

        if diagnosis.fraud_result:
            invoice_data["fraud_score"] = diagnosis.fraud_result.total_score
            invoice_data["fraud_signals"] = {
                s.signal_name: {"triggered": s.triggered, "detail": s.detail}
                for s in diagnosis.fraud_result.signals
            }

        stored_invoice = await store_invoice(invoice_data)

        if stored_invoice and inv_json and inv_json.line_items:
            from app.services.supabase_client import store_invoice_line_items
            await store_invoice_line_items(
                stored_invoice["id"],
                inv_json.line_items,
                diagnosis.hsn_validations,
            )

        # Notify via WhatsApp (Dual Routing)
        # 1. Shopkeeper (Informal Document with Caption)
        if trader.get("whatsapp_number") and image_url:
            lang = trader.get("language_pref", "hi")
            msg = await generate_informal_notification(lang, supplier_name, total_amount)
            # Await the call so it doesn't get cancelled when request ends
            inv_no = invoice_data.get("invoice_number", "Unknown")
            await whatsapp.send_document(
                to=trader["whatsapp_number"],
                document_url=image_url,
                caption=msg,
                filename=f"Invoice_{inv_no}.pdf"
            )

        # 2. CA (Formal Document with Caption)
        if trader.get("ca_whatsapp_number") and image_url:
            trader_name = trader.get("business_name") or trader.get("name") or "Unknown Trader"
            inv_no = invoice_data.get("invoice_number", "Unknown")
            inv_date = invoice_data.get("invoice_date", "Unknown Date")
            itc_status = invoice_data.get("itc_status", "pending")
            
            ca_msg = await generate_formal_notification(
                trader_name, supplier_name, inv_no, str(inv_date), total_amount, itc_status
            )
            # Await the document send
            await whatsapp.send_document(
                to=trader["ca_whatsapp_number"],
                document_url=image_url,
                caption=ca_msg,
                filename=f"Invoice_{inv_no}.pdf"
            )

        return Response(status_code=200)

    except Exception as e:
        logger.error(f"Email webhook failed: {e}", exc_info=True)
        return Response(status_code=500)
