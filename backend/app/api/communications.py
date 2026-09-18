from fastapi import APIRouter, Depends
from app.api.deps import verify_trader_access, get_current_trader_id, HTTPException
import logging
from datetime import datetime, timedelta, timezone
from app.services.supabase_client import get_supabase
import resend
from app.config import get_settings
from app.services.whatsapp import send_text_message

logger = logging.getLogger(__name__)
settings = get_settings()
resend.api_key = settings.resend_api_key

ROUTE_PREFIX = "/api/v1/communicate"
VENDOR_ALERT_COOLDOWN_DAYS = 7  # Don't re-alert same vendor on same invoice within this window

router = APIRouter(prefix=ROUTE_PREFIX, tags=["communications"])


def _check_rate_limit(invoice: dict) -> None:
    """Raise 429 if this invoice was already notified within the cooldown window."""
    last_notified = invoice.get("last_vendor_notified_at")
    if last_notified:
        try:
            sent_at = datetime.fromisoformat(last_notified.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - sent_at < timedelta(days=VENDOR_ALERT_COOLDOWN_DAYS):
                days_left = VENDOR_ALERT_COOLDOWN_DAYS - (datetime.now(timezone.utc) - sent_at).days
                raise HTTPException(
                    status_code=429,
                    detail=f"Vendor was already notified {(datetime.now(timezone.utc) - sent_at).days} day(s) ago. "
                           f"Wait {days_left} more day(s) before sending another alert to avoid harassing this supplier."
                )
        except HTTPException:
            raise
        except Exception:
            pass  # If timestamp parsing fails, allow the send


def _stamp_notified(db, invoice_id: str) -> None:
    """Record the notification timestamp on the invoice row."""
    try:
        db.table("invoices").update(
            {"last_vendor_notified_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", invoice_id).execute()
    except Exception as e:
        logger.warning(f"Could not stamp last_vendor_notified_at on invoice {invoice_id}: {e}")

@router.post("/email-vendor/{invoice_id}")
async def email_vendor_warning(invoice_id: str, current_trader_id: str = Depends(get_current_trader_id)):
    """Send an automated warning email to the vendor regarding missed GSTR-1 filing."""
    db = get_supabase()
    # Fetch invoice
    inv_resp = db.table("invoices").select("*, traders(business_name)").eq("id", invoice_id).execute()
    if not inv_resp.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice = inv_resp.data[0]

    # Rate-limit guard: don't spam the same supplier
    _check_rate_limit(invoice)

    supplier_email = invoice.get("supplier_email")
    if not supplier_email:
        raise HTTPException(status_code=400, detail="No supplier email available for this invoice")

    trader_name = invoice.get("traders", {}).get("business_name", "your client")
    inv_number = invoice.get("invoice_number", "Unknown")
    inv_date = invoice.get("invoice_date", "Unknown")
    image_url = invoice.get("image_url", "#")

    subject = f"ITC Alert: Invoice {inv_number} Requires Your Attention"
    
    html_content = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2>Invoice Status Check</h2>
        <p>Dear {invoice.get('supplier_name', 'Vendor')},</p>
        <p>This is a system test notification regarding an invoice issued to <strong>{trader_name}</strong>.</p>
        <p>We are verifying the GSTR-2B reconciliation status for the following document:</p>
        <div style="background: #f8fafc; padding: 15px; border-radius: 8px; margin: 15px 0;">
            <p><strong>Invoice Number:</strong> {inv_number}</p>
            <p><strong>Invoice Date:</strong> {inv_date}</p>
            <p><strong>Taxable Amount:</strong> Rs. {invoice.get('taxable_amount', 0)}</p>
            <p><strong>Total Amount:</strong> Rs. {invoice.get('total_amount', 0)}</p>
        </div>
        <p>Please review your upcoming filings.</p>
        <p>Original Document Link: <a href="{image_url}">{image_url}</a></p>
        <p>Regards,<br>Munim AI System</p>
    </div>
    """

    try:
        # If in debug mode, override the destination to a verified address
        # so Resend doesn't block the email
        if settings.debug:
            supplier_email = "shahaditya0710@gmail.com"
            logger.info(f"Debug mode: Routing warning email to {supplier_email}")
            
            # Save the email locally so the user can preview it instantly without waiting for Resend
            try:
                import os
                preview_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "frontend", "public", "latest_email.html")
                with open(preview_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.info(f"Saved email preview to {preview_path}")
            except Exception as e:
                logger.error(f"Failed to save email preview: {e}")

        params = {
            "from": "Munim AI <onboarding@resend.dev>",
            "to": [supplier_email],
            "subject": subject,
            "html": html_content
        }
        resend.Emails.send(params)
        logger.info(f"Warning email sent to vendor {supplier_email} for invoice {invoice_id}")
        _stamp_notified(db, invoice_id)
        return {"status": "success", "message": "Email sent to vendor"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send vendor warning email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/whatsapp-vendor/{invoice_id}")
async def whatsapp_vendor_warning(invoice_id: str, lang: str = "en", current_trader_id: str = Depends(get_current_trader_id)):
    """Send an automated WhatsApp warning to the vendor regarding missed GSTR-1 filing."""
    db = get_supabase()
    inv_resp = db.table("invoices").select("*, traders(business_name)").eq("id", invoice_id).execute()
    if not inv_resp.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice = inv_resp.data[0]

    # Rate-limit guard: don't spam the same supplier
    _check_rate_limit(invoice)

    supplier_phone = invoice.get("supplier_phone")
    if not supplier_phone:
        raise HTTPException(status_code=400, detail="No supplier phone available for this invoice")

    # Format phone to ensure standard format (assume India +91 if length is 10)
    phone = "".join(filter(str.isdigit, supplier_phone))
    if len(phone) == 10:
        phone = "91" + phone

    trader_name = invoice.get("traders", {}).get("business_name", "your client")
    inv_number = invoice.get("invoice_number", "Unknown")
    total_amount = invoice.get("total_amount", 0)

    if lang == "hi":
        message = (
            f"📋 *कार्रवाई आवश्यक: GSTR-1 फाइलिंग*\n\n"
            f"प्रिय {invoice.get('supplier_name', 'Vendor')},\n\n"
            f"आपके द्वारा *{trader_name}* को जारी किया गया एक चालान अभी तक उनके GSTR-2B में नहीं दिखा है, जिसके कारण इनपुट टैक्स क्रेडिट (ITC) रुका हुआ है।\n\n"
            f"📄 *चालान संख्या:* {inv_number}\n"
            f"💰 *राशि:* ₹{total_amount}\n\n"
            f"कृपया जांचें कि क्या यह चालान आपकी GSTR-1 फाइलिंग में शामिल था। यदि नहीं, तो कृपया इसे जल्द से जल्द फाइल करें ताकि ITC जारी किया जा सके।\n"
            f"🔗 चालान की प्रति: {invoice.get('image_url', '#')}\n\n"
            f"धन्यवाद,\nMunim AI ({trader_name} की ओर से)"
        )
    else:
        message = (
            f"📋 *Action Needed: GSTR-1 Filing*\n\n"
            f"Dear {invoice.get('supplier_name', 'Vendor')},\n\n"
            f"An invoice you issued to *{trader_name}* has not yet reflected in their GSTR-2B, which has put the Input Tax Credit on hold.\n\n"
            f"📄 *Invoice No:* {inv_number}\n"
            f"💰 *Amount:* ₹{total_amount}\n\n"
            f"Kindly verify if this invoice was included in your GSTR-1 filing. If not, please file at your earliest convenience so the ITC can be released.\n"
            f"🔗 Invoice copy: {invoice.get('image_url', '#')}\n\n"
            f"Thank you,\nMunim AI (on behalf of {trader_name})"
        )

    try:
        await send_text_message(to=phone, message=message)
        logger.info(f"WhatsApp warning sent to vendor {phone} for invoice {invoice_id}")
        return {"status": "success", "message": "WhatsApp sent to vendor"}
    except Exception as e:
        logger.error(f"Failed to send vendor WhatsApp: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-alert/{trader_id}")
async def send_test_alert(trader_id: str = Depends(verify_trader_access), lang: str = "en"):
    """Send a test WhatsApp alert to the trader (CA self-test)."""
    db = get_supabase()
    trader_resp = db.table("traders").select("whatsapp_number, business_name, name").eq("id", trader_id).execute()
    if not trader_resp.data:
        raise HTTPException(status_code=404, detail="Trader not found")

    trader = trader_resp.data[0]
    phone_raw = trader.get("whatsapp_number") or ""
    if not phone_raw:
        raise HTTPException(status_code=400, detail="No WhatsApp number on file for this trader")

    phone = "".join(filter(str.isdigit, phone_raw))
    if len(phone) == 10:
        phone = "91" + phone

    biz = trader.get("business_name") or trader.get("name") or "your business"
    if lang == "hi":
        message = (
            f"✅ *Munim.ai अलर्ट टेस्ट*\n\n"
            f"यह *{biz}* के लिए एक परीक्षण अधिसूचना है।\n\n"
            f"आपके WhatsApp अलर्ट अब सक्रिय हैं। आपको यहाँ सूचनाएं मिलेंगी:\n"
            f"• 🗓️ आगामी GST फाइलिंग समय-सीमाएं\n"
            f"• ⚠️ ITC बेमेल या अवरुद्ध चालान\n"
            f"• ✅ नया पुष्ट ITC\n\n"
            f"अनसब्सक्राइब करने के लिए किसी भी समय STOP का उत्तर दें।\n"
            f"— Munim AI"
        )
    else:
        message = (
            f"✅ *Munim.ai Alert Test*\n\n"
            f"This is a test notification for *{biz}*.\n\n"
            f"Your WhatsApp alerts are now active. You'll receive notifications here for:\n"
            f"• 🗓️ Upcoming GST filing deadlines\n"
            f"• ⚠️ ITC mismatches or blocked invoices\n"
            f"• ✅ Newly confirmed ITC\n\n"
            f"Reply STOP to unsubscribe at any time.\n"
            f"— Munim AI"
        )

    try:
        await send_text_message(to=phone, message=message)
        logger.info(f"Test alert sent to trader {trader_id} at {phone}")
        return {"status": "success", "message": f"Test alert sent to {phone}"}
    except Exception as e:
        logger.error(f"Failed to send test alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))
