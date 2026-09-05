"""
Munim.ai — Supabase Database Service
Handles all database operations via Supabase client.
"""

import logging
from typing import Optional
from functools import lru_cache

from supabase import create_client, Client

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


@lru_cache()
def get_supabase() -> Client:
    """Create and cache Supabase client."""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


# --- Trader Operations ---

async def get_trader_by_phone(phone: str) -> Optional[dict]:
    """Find a trader by WhatsApp number."""
    try:
        db = get_supabase()
        response = db.table("traders").select("*").eq("whatsapp_number", phone).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to get trader by phone: {e}")
        return None

async def get_trader_by_inbound_email(email: str) -> Optional[dict]:
    """Find a trader by their inbound virtual email address."""
    try:
        db = get_supabase()
        response = db.table("traders").select("*").eq("inbound_email", email).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to get trader by inbound email: {e}")
        return None


async def create_trader(phone: str, gstin: str = None, name: str = None, business_name: str = None) -> Optional[dict]:
    """Register a new trader."""
    try:
        db = get_supabase()
        data = {"whatsapp_number": phone}
        if gstin:
            data["gstin"] = gstin
        if name:
            data["name"] = name
        if business_name:
            data["business_name"] = business_name
        response = db.table("traders").insert(data).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to create trader: {e}")
        return None


async def update_trader(trader_id: str, updates: dict) -> Optional[dict]:
    """Update trader fields."""
    try:
        db = get_supabase()
        response = db.table("traders").update(updates).eq("id", trader_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to update trader: {e}")
        return None


# --- Invoice Operations ---

async def store_invoice(invoice_data: dict) -> Optional[dict]:
    """Store a processed invoice."""
    try:
        db = get_supabase()
        response = db.table("invoices").insert(invoice_data).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to store invoice: {e}")
        return None


async def store_invoice_line_items(invoice_id: str, line_items: list, hsn_validations: list) -> None:
    """Store invoice line items with HSN validation results."""
    try:
        db = get_supabase()
        for i, item in enumerate(line_items):
            hsn_val = hsn_validations[i] if i < len(hsn_validations) else None
            row = {
                "invoice_id": invoice_id,
                "description": item.description,
                "hsn_code_extracted": item.hsn_code,
                "quantity": item.quantity,
                "unit": item.unit,
                "unit_price": item.unit_price,
                "taxable_value": item.taxable_value,
                "tax_rate_applied": (item.cgst_rate or 0) + (item.sgst_rate or 0) + (item.igst_rate or 0),
            }
            if hsn_val:
                row["hsn_code_validated"] = hsn_val.hsn_code_validated
                row["hsn_is_valid"] = hsn_val.is_valid
                row["hsn_suggestion"] = hsn_val.suggestion
                row["hsn_confidence"] = hsn_val.confidence
                row["tax_rate_correct"] = hsn_val.tax_rate_correct
                row["rate_mismatch"] = hsn_val.rate_mismatch
                row["itc_delta"] = hsn_val.itc_delta
            db.table("invoice_line_items").insert(row).execute()
    except Exception as e:
        logger.error(f"Failed to store line items: {e}")


async def get_invoices_for_trader(trader_id: str, month: int = None, year: int = None) -> list[dict]:
    """Get all invoices for a trader, optionally filtered by month/year."""
    try:
        db = get_supabase()
        query = db.table("invoices").select("*").eq("trader_id", trader_id)
        if month and year:
            start_date = f"{year}-{month:02d}-01"
            if month == 12:
                end_date = f"{year + 1}-01-01"
            else:
                end_date = f"{year}-{month + 1:02d}-01"
            query = query.gte("invoice_date", start_date).lt("invoice_date", end_date)
        response = query.order("created_at", desc=True).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get invoices: {e}")
        return []


async def check_duplicate_invoice(invoice_hash: str) -> bool:
    """Check if an invoice hash already exists."""
    try:
        db = get_supabase()
        response = db.table("invoices").select("id").eq("invoice_hash", invoice_hash).execute()
        return bool(response.data and len(response.data) > 0)
    except Exception as e:
        logger.error(f"Failed to check duplicate: {e}")
        return False


# --- Supplier Operations ---

async def get_or_create_supplier(gstin: str, legal_name: str = None) -> Optional[dict]:
    """Get existing supplier or create new one."""
    try:
        db = get_supabase()
        response = db.table("suppliers").select("*").eq("gstin", gstin).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]

        # Create new supplier
        data = {"gstin": gstin}
        if legal_name:
            data["legal_name"] = legal_name
        response = db.table("suppliers").insert(data).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to get/create supplier: {e}")
        return None


async def link_supplier_to_trader(trader_id: str, supplier_id: str) -> None:
    """Create supplier-trader link if not exists."""
    try:
        db = get_supabase()
        existing = db.table("supplier_trader_links").select("id").eq(
            "trader_id", trader_id
        ).eq("supplier_id", supplier_id).execute()

        if not existing.data:
            db.table("supplier_trader_links").insert({
                "trader_id": trader_id,
                "supplier_id": supplier_id,
                "total_invoice_count": 1,
            }).execute()
        else:
            # Increment invoice count
            link = existing.data[0]
            db.table("supplier_trader_links").update({
                "total_invoice_count": (link.get("total_invoice_count", 0) or 0) + 1,
            }).eq("id", link["id"]).execute()
    except Exception as e:
        logger.error(f"Failed to link supplier: {e}")


async def get_all_suppliers_for_trader(trader_id: str) -> list[dict]:
    """Get all suppliers linked to a trader."""
    try:
        db = get_supabase()
        response = db.table("supplier_trader_links").select(
            "*, suppliers(*)"
        ).eq("trader_id", trader_id).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get suppliers: {e}")
        return []


async def get_all_supplier_gstins() -> list[str]:
    """Get all unique supplier GSTINs."""
    try:
        db = get_supabase()
        response = db.table("suppliers").select("gstin").execute()
        return [r["gstin"] for r in (response.data or [])]
    except Exception as e:
        logger.error(f"Failed to get supplier GSTINs: {e}")
        return []


async def update_supplier(supplier_id: str, updates: dict) -> None:
    """Update supplier fields."""
    try:
        db = get_supabase()
        db.table("suppliers").update(updates).eq("id", supplier_id).execute()
    except Exception as e:
        logger.error(f"Failed to update supplier: {e}")


async def add_supplier_flag(supplier_id: str, flag_type: str, metadata: dict = None) -> None:
    """Add a behavioral flag to a supplier."""
    try:
        db = get_supabase()
        db.table("supplier_flags").insert({
            "supplier_id": supplier_id,
            "flag_type": flag_type,
            "metadata": metadata or {},
            "is_active": True,
        }).execute()
    except Exception as e:
        logger.error(f"Failed to add supplier flag: {e}")


async def get_active_supplier_flags(supplier_id: str) -> list[dict]:
    """Get all active flags for a supplier."""
    try:
        db = get_supabase()
        response = db.table("supplier_flags").select("*").eq(
            "supplier_id", supplier_id
        ).eq("is_active", True).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get supplier flags: {e}")
        return []


# --- GSTR-2B Operations ---

async def get_gstr2b_records(trader_id: str, month: int = None, year: int = None, unmatched_only: bool = False) -> list[dict]:
    """Get GSTR-2B records for a trader."""
    try:
        db = get_supabase()
        query = db.table("gstr2b_records").select("*").eq("trader_id", trader_id)
        if month:
            query = query.eq("month", month)
        if year:
            query = query.eq("year", year)
        if unmatched_only:
            query = query.is_("matched_invoice_id", "null")
        response = query.execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get GSTR-2B records: {e}")
        return []

async def mark_gstr2b_record_matched(record_id: str, invoice_id: str) -> None:
    """Mark a GSTR-2B record as matched with an invoice."""
    try:
        db = get_supabase()
        db.table("gstr2b_records").update({
            "matched_invoice_id": invoice_id
        }).eq("id", record_id).execute()
    except Exception as e:
        logger.error(f"Failed to mark GSTR-2B record as matched: {e}")


# --- Dashboard Operations ---

async def get_recent_invoices(trader_id: str, limit: int = 5) -> list[dict]:
    """Get recent invoices for a trader."""
    try:
        db = get_supabase()
        response = db.table("invoices").select(
            "supplier_name, total_amount, itc_status, invoice_date"
        ).eq("trader_id", trader_id).order("created_at", desc=True).limit(limit).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get recent invoices: {e}")
        return []

async def get_itc_summary(trader_id: str) -> dict:
    """Compute ITC summary buckets for a trader."""
    try:
        db = get_supabase()
        response = db.table("invoices").select(
            "itc_status, itc_amount_eligible, itc_amount_blocked"
        ).eq("trader_id", trader_id).execute()

        buckets = {
            "confirmed": 0.0,
            "fixable_blocked": 0.0,
            "at_risk": 0.0,
            "missed": 0.0,
            "ineligible": 0.0,
        }

        for inv in (response.data or []):
            status = inv.get("itc_status", "")
            eligible = inv.get("itc_amount_eligible") or 0
            blocked = inv.get("itc_amount_blocked") or 0

            if status == "CONFIRMED":
                buckets["confirmed"] += eligible
            elif status in ["FIXABLE_BLOCKED", "FRAUD_FLAGGED", "DUPLICATE"]:
                buckets["fixable_blocked"] += blocked
            elif status == "AT_RISK":
                buckets["at_risk"] += eligible
            elif status == "MISSED":
                buckets["missed"] += eligible
            elif status == "INELIGIBLE":
                buckets["ineligible"] += blocked

        return buckets
    except Exception as e:
        logger.error(f"Failed to compute ITC summary: {e}")
        return {}


# --- File Storage ---

async def upload_file(bucket: str, path: str, file_bytes: bytes, content_type: str = "image/jpeg") -> Optional[str]:
    """Upload a file to Supabase Storage and return the public URL."""
    try:
        db = get_supabase()
        db.storage.from_(bucket).upload(
            path, file_bytes, {"content-type": content_type, "upsert": "true"}
        )
        url = db.storage.from_(bucket).get_public_url(path)
        return url
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        return None
