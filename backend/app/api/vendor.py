"""
Munim.ai — vendor self-service fix links.

When a supplier has not reported a sale, the trader's credit is stuck behind
somebody else's filing. Today the CA chases that supplier by phone, repeatedly,
and the outcome lives in the CA's memory.

This closes the loop without the CA in it. The supplier gets one link. It opens
without a login, on a phone, and shows exactly one thing: the invoice they
issued, what is missing, and by when. They tap what they intend to do. The
trader and their CA are told.

Security model, since these endpoints are deliberately unauthenticated
----------------------------------------------------------------------
*   The token is a **signed capability**, not a session. It names one invoice,
    expires, and grants nothing else. There is no account to take over.
*   It is signed with a key **derived from** `JWT_SECRET`, not `JWT_SECRET`
    itself, and carries no `sub` claim. Both are deliberate: a vendor token
    presented as a `Bearer` credential fails signature verification outright,
    and even if it did not, `deps.get_current_trader_id` would find no subject
    to impersonate. A capability URL that can be escalated into a login is the
    obvious way for this feature to become a breach, so it is closed twice.
*   The page returns **only data the vendor themselves issued** — their own
    invoice number, date and amount, and the buyer's business name. No other
    invoice, no trader phone number, no portfolio, nothing about the trader's
    other suppliers.
*   Both public routes are rate-limited per token, because the URL will be
    forwarded around WhatsApp and will end up in places nobody intended.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import HTTPException, get_current_trader_id, verify_trader_access
from app.config import get_settings
from app.services import event_store
from app.services.redis_cache import check_rate_limit
from app.services.supabase_client import get_supabase
from app.utils.errors import safe_http_error

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/v1/vendor", tags=["vendor"])

_AUDIENCE = "munim-vendor-fix"

# Long enough to survive a supplier's week, short enough that a forwarded link
# stops working well before the next filing cycle.
LINK_TTL_DAYS = 14

# The supplier's own GSTR-1 deadline.
_GSTR1_DAY = 11


def _signing_key() -> str:
    """A key derived from JWT_SECRET, never JWT_SECRET itself. See the module
    docstring — this is what makes a vendor link unusable as a login."""
    return hashlib.sha256(f"{settings.jwt_secret}|vendor-fix|v1".encode()).hexdigest()


def _mint(invoice_id: str, trader_id: str) -> tuple[str, datetime]:
    expires = datetime.now(timezone.utc) + timedelta(days=LINK_TTL_DAYS)
    token = jwt.encode(
        {
            "inv": invoice_id,
            "tid": trader_id,
            "aud": _AUDIENCE,
            "iat": datetime.now(timezone.utc),
            "exp": expires,
        },
        _signing_key(),
        algorithm="HS256",
    )
    return token, expires


def _read_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            _signing_key(),
            algorithms=["HS256"],
            audience=_AUDIENCE,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=410,
            detail="This link has expired. Ask your customer to send a fresh one.",
        )
    except jwt.PyJWTError:
        # Same message for a forged token and a truncated one. Telling the
        # difference is only useful to somebody probing.
        raise HTTPException(status_code=404, detail="This link is not valid.")


def _gstr1_due_for(invoice_date: Optional[date]) -> Optional[date]:
    if not invoice_date:
        return None
    if invoice_date.month == 12:
        return date(invoice_date.year + 1, 1, _GSTR1_DAY)
    return date(invoice_date.year, invoice_date.month + 1, _GSTR1_DAY)


def _parse_date(value) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _guard(token: str, bucket: str, max_requests: int, window: int) -> None:
    """Rate-limit a public route by token. `check_rate_limit` returns False
    when the caller is over budget."""
    key = f"vendorfix:{bucket}:{hashlib.sha256(token.encode()).hexdigest()[:24]}"
    if not check_rate_limit(key, max_requests=max_requests, window_seconds=window):
        raise HTTPException(status_code=429, detail="Too many requests. Try again shortly.")


# --------------------------------------------------------------------------
# Authenticated: minting a link. Lives here rather than in communications.py
# so that everything defining what a vendor can see sits in one file.
# --------------------------------------------------------------------------

@router.post("/link/{invoice_id}")
async def create_fix_link(invoice_id: str, current_trader_id: str = Depends(get_current_trader_id)):
    """Mint a fix link for one invoice. Returns the URL to send the supplier."""
    try:
        db = get_supabase()
        rows = (
            db.table("invoices")
            .select("id, trader_id, supplier_name, gstin_supplier, invoice_number, itc_status")
            .eq("id", invoice_id)
            .limit(1)
            .execute()
        ).data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Invoice not found")

        invoice = rows[0]
        owner = invoice.get("trader_id")
        if not owner:
            logger.warning("vendor link requested for ownerless invoice %s", invoice_id)
            raise HTTPException(status_code=403, detail="Not authorized for this invoice")
        await verify_trader_access(owner, current_trader_id)

        token, expires = _mint(invoice_id, owner)
        url = f"{settings.frontend_base_url}/fix/{token}"

        # Recorded so the CA can see a link was issued even if the supplier
        # never opens it. A returned None here means the write failed, and the
        # response says so rather than implying a clean audit trail.
        event_id = event_store.record(owner, event_store.VENDOR_FIX_LINK_ISSUED, {
            "invoice_id": invoice_id,
            "supplier_name": invoice.get("supplier_name"),
            "gstin_supplier": invoice.get("gstin_supplier"),
            "invoice_number": invoice.get("invoice_number"),
            "issued_by": current_trader_id,
            "expires_at": expires.isoformat(),
        })

        return {
            "url": url,
            "expires_at": expires.isoformat(),
            "expires_in_days": LINK_TTL_DAYS,
            "audited": event_id is not None,
            "supplier_name": invoice.get("supplier_name"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise safe_http_error(logger, "Failed to create a vendor fix link", e)


@router.get("/responses/{trader_id}")
async def list_vendor_responses(trader_id: str = Depends(verify_trader_access)):
    """What suppliers have said back, newest first — the CA's side of the loop."""
    try:
        responses = event_store.find(event_store.VENDOR_FIX_RESPONSE, trader_id, limit=100)
        issued = event_store.find(event_store.VENDOR_FIX_LINK_ISSUED, trader_id, limit=100)
        answered = {r.get("invoice_id") for r in responses}
        return {
            "responses": responses,
            "awaiting": [i for i in issued if i.get("invoice_id") not in answered],
        }
    except Exception as e:
        raise safe_http_error(logger, "Failed to list vendor responses", e)


# --------------------------------------------------------------------------
# Public: what the supplier actually opens.
# --------------------------------------------------------------------------

@router.get("/fix/{token}")
async def open_fix_link(token: str):
    """
    The supplier's view of one invoice. No login, no account, one invoice.

    Everything returned here is data the supplier issued in the first place,
    plus the buyer's business name so they know who is asking.
    """
    _guard(token, "open", max_requests=30, window=300)
    claims = _read_token(token)
    invoice_id, trader_id = claims.get("inv"), claims.get("tid")

    try:
        db = get_supabase()
        rows = (
            db.table("invoices")
            .select(
                "id, trader_id, supplier_name, gstin_supplier, invoice_number, "
                "invoice_date, total_amount, taxable_amount, igst_amount, cgst_amount, "
                "sgst_amount, itc_status, itc_block_reason"
            )
            .eq("id", invoice_id)
            .limit(1)
            .execute()
        ).data or []
        if not rows or rows[0].get("trader_id") != trader_id:
            # Token/row mismatch means the invoice moved or was deleted. Not
            # something to explain in detail to an unauthenticated caller.
            raise HTTPException(status_code=404, detail="This link is not valid.")

        inv = rows[0]
        buyer = (
            db.table("traders")
            .select("business_name, name, gstin")
            .eq("id", trader_id)
            .limit(1)
            .execute()
        ).data or [{}]
        buyer_name = buyer[0].get("business_name") or buyer[0].get("name") or "your customer"

        inv_date = _parse_date(inv.get("invoice_date"))
        due = _gstr1_due_for(inv_date)
        tax = sum(float(inv.get(k) or 0) for k in ("igst_amount", "cgst_amount", "sgst_amount"))

        # Has this vendor already answered on this invoice? Showing them the
        # form again after they said "already filed" is how a genuine supplier
        # decides the sender is a bot and stops reading.
        prior = event_store.find(
            event_store.VENDOR_FIX_RESPONSE, trader_id, limit=100,
            where={"invoice_id": invoice_id},
        )

        return {
            "buyer_name": buyer_name,
            "buyer_gstin": buyer[0].get("gstin"),
            # Many invoices carry no extracted supplier name. Showing "null"
            # to the supplier reading their own bill is worse than showing the
            # GSTIN, which they will recognise as theirs.
            "supplier_name": inv.get("supplier_name") or inv.get("gstin_supplier") or "your business",
            "supplier_gstin": inv.get("gstin_supplier"),
            "invoice_number": inv.get("invoice_number"),
            "invoice_date": inv.get("invoice_date"),
            "taxable_amount": round(float(inv.get("taxable_amount") or 0), 2),
            "tax_amount": round(tax, 2),
            "total_amount": round(float(inv.get("total_amount") or 0), 2),
            "problem": (
                "This invoice has not appeared in your customer's GSTR-2B, "
                "which means it has not yet been reported in your GSTR-1."
            ),
            "reason": inv.get("itc_block_reason"),
            "gstr1_due": due.isoformat() if due else None,
            "days_left": (due - date.today()).days if due else None,
            "already_answered": prior[0] if prior else None,
            "expires_at": datetime.fromtimestamp(claims["exp"], tz=timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise safe_http_error(logger, "Failed to open the vendor fix link", e)


class VendorResponse(BaseModel):
    action: str = Field(..., description="filed | will_file | disputed | not_mine")
    expected_date: Optional[str] = None
    note: Optional[str] = Field(None, max_length=500)


_ACTIONS = {
    "filed": "says this invoice is already reported in their GSTR-1",
    "will_file": "will report this invoice in their next GSTR-1",
    "disputed": "disputes this invoice",
    "not_mine": "says this invoice is not theirs",
}


@router.post("/fix/{token}/respond")
async def respond_to_fix_link(token: str, payload: VendorResponse):
    """The supplier answers. Recorded, and pushed to the trader over WhatsApp."""
    _guard(token, "respond", max_requests=10, window=3600)
    claims = _read_token(token)
    invoice_id, trader_id = claims.get("inv"), claims.get("tid")

    action = (payload.action or "").strip().lower()
    if action not in _ACTIONS:
        raise HTTPException(status_code=400, detail=f"action must be one of {sorted(_ACTIONS)}")

    try:
        db = get_supabase()
        rows = (
            db.table("invoices")
            .select("id, trader_id, supplier_name, invoice_number, invoice_date")
            .eq("id", invoice_id)
            .limit(1)
            .execute()
        ).data or []
        if not rows or rows[0].get("trader_id") != trader_id:
            raise HTTPException(status_code=404, detail="This link is not valid.")
        inv = rows[0]

        event_id = event_store.record(trader_id, event_store.VENDOR_FIX_RESPONSE, {
            "invoice_id": invoice_id,
            "invoice_number": inv.get("invoice_number"),
            "supplier_name": inv.get("supplier_name"),
            "action": action,
            "expected_date": payload.expected_date,
            "note": (payload.note or "").strip() or None,
            "channel": "vendor_fix_link",
        })
        if not event_id:
            # The supplier did their part; if we cannot store it we must not
            # tell them it is handled.
            raise HTTPException(
                status_code=503,
                detail="We could not record your answer. Please try again in a moment.",
            )

        await _notify_trader(db, trader_id, inv, action, payload)

        return {
            "recorded": True,
            "action": action,
            "message": {
                "filed": "Thank you. Your customer has been told it is already filed.",
                "will_file": "Thank you. Your customer has been told you will file it.",
                "disputed": "Thank you. Your customer has been told you dispute this invoice.",
                "not_mine": "Thank you. Your customer has been told this is not your invoice.",
            }[action],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise safe_http_error(logger, "Failed to record the vendor response", e)


async def _notify_trader(db, trader_id: str, invoice: dict, action: str, payload: VendorResponse) -> None:
    """Tell the trader their supplier answered. Best-effort: the response is
    already durably recorded, so a failed WhatsApp send must not fail the
    supplier's submission."""
    try:
        from app.services.whatsapp import send_text_message

        rows = (
            db.table("traders")
            .select("whatsapp_number")
            .eq("id", trader_id)
            .limit(1)
            .execute()
        ).data or []
        phone = rows[0].get("whatsapp_number") if rows else None
        if not phone:
            return

        supplier = invoice.get("supplier_name") or "Your supplier"
        number = invoice.get("invoice_number") or "an invoice"
        line = f"{supplier} {_ACTIONS[action]} ({number})."
        if action == "will_file" and payload.expected_date:
            line += f" They expect to file by {payload.expected_date}."
        if payload.note:
            line += f"\n\nTheir note: {payload.note.strip()[:300]}"

        await send_text_message(phone, f"Supplier update from Munim\n\n{line}")
    except Exception as e:
        logger.warning("vendor fix: could not notify trader %s: %s", trader_id, e)
