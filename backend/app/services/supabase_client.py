"""
Munim-AI — Supabase Database Service
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


async def resolve_trader_rows(column: str, canonical: str, variants: list[str]) -> list[dict]:
    """
    Same wrong-identity guard auth.py originally had inline as
    _resolve_trader_rows, pulled out here so both backends (this one and
    dynamodb_client.py) expose it through the same db.py interface.
    Behaviour unchanged: an exact match on the canonical number always
    wins outright; only when there is no canonical match do we fall back
    to the looser variant list, and only if every row it returns belongs
    to the same trader -- a fallback that spans more than one distinct
    trader id is ambiguous, so this returns nothing rather than guess.
    """
    try:
        db = get_supabase()
        exact = db.table("traders").select("*").eq(column, canonical).execute()
        if exact.data:
            return exact.data

        fallback = db.table("traders").select("*").in_(column, variants).execute()
        if not fallback.data:
            return []
        ids = {row["id"] for row in fallback.data}
        if len(ids) > 1:
            logger.error(
                f"Ambiguous phone match on {column}: variants {variants} matched "
                f"{len(ids)} distinct traders {ids}. Refusing to guess."
            )
            return []
        return fallback.data
    except Exception as e:
        logger.error(f"Failed to resolve trader rows by {column}: {e}")
        return []


# --- Trader Operations ---

async def get_trader_by_phone(phone: str) -> Optional[dict]:
    """
    Find a trader by WhatsApp number, whatever spelling it is stored under.

    This used to be a bare `.eq("whatsapp_number", phone)`. Meta announces an
    inbound sender as `919136875481`, but rows reach this table from CAs,
    seed scripts and CSVs as ten bare digits or `+91 ...`, and an exact string
    match never bridges the two. One trader in the live database -- the one
    with 581 invoices -- was unreachable because of exactly that.

    Precedence is deliberate and is what keeps this deterministic when two
    rows hold the same number in different formats: the exact spelling
    WhatsApp used wins, then the normalised international form, then the bare
    local one. The row stored the way WhatsApp actually spells it owns the
    handset; the others are legacy spellings of it.
    """
    from app.services.phone import match_variants

    try:
        db = get_supabase()
        for candidate in match_variants(phone) or [phone]:
            response = db.table("traders").select("*").eq("whatsapp_number", candidate).execute()
            rows = response.data or []
            if rows:
                if len(rows) > 1:
                    # UNIQUE on whatsapp_number makes this unreachable today,
                    # but say so loudly rather than picking silently if the
                    # constraint is ever dropped.
                    logger.warning(
                        "Multiple traders stored under %s — using %s", candidate, rows[0].get("id")
                    )
                return rows[0]
        return None
    except Exception as e:
        logger.error(f"Failed to get trader by phone: {e}")
        return None

async def get_trader_by_short_code(short_code: str) -> Optional[dict]:
    """Find a trader by their QR-onboarding short_code (used as the CA
    identifier in JOIN-<code> deep links)."""
    try:
        db = get_supabase()
        response = db.table("traders").select("*").eq("short_code", short_code).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to get trader by short code: {e}")
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


async def get_trader_by_id(trader_id: str) -> Optional[dict]:
    """Find a trader by primary key id."""
    try:
        db = get_supabase()
        response = db.table("traders").select("*").eq("id", trader_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to get trader by id: {e}")
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


async def get_recent_invoice_locations(trader_id: str, limit: int = 20, exclude_invoice_id: str = None) -> list[dict]:
    """
    This trader's most recent invoices that have a GPS tag (backend/
    migrations/add_invoice_geolocation.sql — nullable, most invoices won't
    have one). Feeds webhook.py's scan-location anomaly check only; never
    used for anything ITC/compliance-related.
    """
    try:
        db = get_supabase()
        response = (
            db.table("invoices")
            .select("id, latitude, longitude")
            .eq("trader_id", trader_id)
            .not_.is_("latitude", "null")
            .not_.is_("longitude", "null")
            .order("created_at", desc=True)
            .limit(limit + 1)  # +1 headroom: the just-inserted row can itself be in this page
            .execute()
        )
        rows = response.data or []
        if exclude_invoice_id:
            rows = [r for r in rows if r.get("id") != exclude_invoice_id]
        return rows[:limit]
    except Exception as e:
        logger.error(f"Failed to get recent invoice locations: {e}")
        return []


async def get_invoices_by_gstin_suppliers(gstins: list[str]) -> list[dict]:
    """The one deliberately cross-tenant read in the codebase -- wraps the
    same chunked .in_() query domain/network_intel.py's _fetch_network_rows
    used to build inline, moved here so both backends expose it through
    db.py. Only the columns the aggregation needs: trader_id,
    gstin_supplier, gstr2b_match_status, itc_status -- no amounts, no
    invoice numbers, no supplier-side contact data."""
    if not gstins:
        return []
    rows: list[dict] = []
    CHUNK = 40  # PostgREST URL-length limit
    try:
        db = get_supabase()
        for i in range(0, len(gstins), CHUNK):
            batch = gstins[i:i + CHUNK]
            try:
                res = (
                    db.table("invoices")
                    .select("trader_id, gstin_supplier, gstr2b_match_status, itc_status")
                    .in_("gstin_supplier", batch)
                    .execute()
                )
                rows.extend(res.data or [])
            except Exception as e:
                logger.error(f"network_intel: batch fetch failed for {len(batch)} gstins: {e}")
    except Exception as e:
        logger.error(f"Failed to get invoices by gstin suppliers: {e}")
    return rows


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


async def upsert_gstr2b_record(
    trader_id: str, month: int, year: int, supplier_gstin: str, invoice_number: str, fields: dict
) -> None:
    """
    Upsert a single GSTR-2B record keyed on (trader_id, month, year,
    supplier_gstin, invoice_number).

    Deliberately does NOT catch exceptions, unlike almost everything else in
    this file: the upload endpoints' per-record try/except is what turns a
    raised error here into a counted `skipped` in the response. Swallowing
    it here would make `{"inserted": N}` lie about a totally failed import --
    exactly the landmine CLAUDE.md warns about for this upload loop.
    """
    db = get_supabase()
    row = {
        "trader_id": trader_id,
        "month": month,
        "year": year,
        "supplier_gstin": supplier_gstin,
        "invoice_number": invoice_number,
        **fields,
    }
    db.table("gstr2b_records").upsert(
        row, on_conflict="trader_id,month,year,supplier_gstin,invoice_number"
    ).execute()


async def delete_gstr2b_b2b_record(trader_id: str, supplier_gstin: str, invoice_number: str) -> None:
    """
    Delete the B2B row a B2BA amendment supersedes. No month/year filter --
    matches the original inline call, which deleted across any period this
    (trader, supplier, invoice_number) B2B row might live in.

    Does not catch exceptions -- same reasoning as upsert_gstr2b_record.
    """
    db = get_supabase()
    db.table("gstr2b_records").delete().eq(
        "trader_id", trader_id
    ).eq("supplier_gstin", supplier_gstin
    ).eq("invoice_number", invoice_number
    ).eq("record_type", "B2B").execute()


async def delete_gstr2b_records_for_period(trader_id: str, month: int, year: int) -> None:
    """Clear every GSTR-2B row for one trader+period (e.g. before a re-upload)."""
    try:
        db = get_supabase()
        db.table("gstr2b_records").delete().eq(
            "trader_id", trader_id
        ).eq("month", month).eq("year", year).execute()
    except Exception as e:
        logger.error(f"Failed to delete GSTR-2B records for period: {e}")


async def get_supplier_by_gstin(gstin: str) -> Optional[dict]:
    """
    Read-only point lookup by gstin. Unlike get_or_create_supplier, never
    creates a row -- for display-only paths (e.g. missed-ITC supplier names
    on the dashboard) that must stay pure reads.
    """
    try:
        db = get_supabase()
        response = db.table("suppliers").select("gstin, legal_name, trade_name").eq("gstin", gstin).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to get supplier by gstin: {e}")
        return None


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
                # itc_engine records an AT_RISK verdict as eligible=total_tax,
                # blocked=0 -- the credit is real, merely exposed. Rows written
                # by the seed scripts use the opposite convention and put the
                # figure in blocked. Reading only `eligible` reported this
                # bucket as roughly nil for 103 of the 104 AT_RISK invoices in
                # the database. Whichever column carries it is the number,
                # because each convention leaves the other at zero.
                buckets["at_risk"] += eligible or blocked
            elif status == "MISSED":
                buckets["missed"] += eligible
            elif status == "INELIGIBLE":
                buckets["ineligible"] += blocked

        # Compute Missed ITC from unmatched GSTR-2B records
        try:
            unmatched = await get_gstr2b_records(trader_id, unmatched_only=True)
            for rec in unmatched:
                if rec.get("record_type", "B2B") in ("B2B", "B2BA"):
                    tax_val = (rec.get("igst") or 0.0) + (rec.get("cgst") or 0.0) + (rec.get("sgst") or 0.0)
                    if tax_val == 0.0 and rec.get("total_tax"):
                        tax_val = rec.get("total_tax") or 0.0
                    buckets["missed"] += tax_val
        except Exception as e:
            logger.warning(f"Could not compute unmatched GSTR-2B missed ITC: {e}")

        return buckets
    except Exception as e:
        logger.error(f"Failed to compute ITC summary: {e}")
        return {}


# --- Report Operations ---

async def get_reports_for_trader(trader_id: str) -> list[dict]:
    """Get all generated Munim Reports for a trader, newest first."""
    try:
        db = get_supabase()
        response = db.table("munim_reports").select(
            "id, month, year, pdf_url, total_invoices_processed, total_itc_confirmed, total_issues_count"
        ).eq("trader_id", trader_id).order("year", desc=True).order("month", desc=True).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to list generated reports: {e}")
        return []


async def upsert_report(trader_id: str, month: int, year: int, fields: dict) -> None:
    """Create or update a trader's monthly report metadata row."""
    try:
        db = get_supabase()
        db.table("munim_reports").upsert({
            "trader_id": trader_id,
            "month": month,
            "year": year,
            **fields,
        }, on_conflict="trader_id,month,year").execute()
    except Exception as e:
        logger.error(f"Failed to store report metadata: {e}")


# --- Communications Operations ---

async def update_invoice_by_id(invoice_id: str, updates: dict) -> None:
    """Update fields on a single invoice row, looked up by id alone."""
    try:
        db = get_supabase()
        db.table("invoices").update(updates).eq("id", invoice_id).execute()
    except Exception as e:
        logger.error(f"Failed to update invoice {invoice_id}: {e}")


async def get_invoice_by_id(invoice_id: str) -> Optional[dict]:
    """Plain point lookup by id, no tenant check -- for the one legitimate
    case that needs to know an invoice's owner BEFORE it can check access
    (dashboard.py's resolve_action_item does its own verify_trader_access
    right after). Anything that already knows the expected trader_id should
    use get_invoice_by_id_for_trader instead, which enforces the match."""
    try:
        db = get_supabase()
        response = db.table("invoices").select("*").eq("id", invoice_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to get invoice by id: {e}")
        return None


async def get_invoice_by_id_for_trader(invoice_id: str, trader_id: str) -> Optional[dict]:
    """Point-lookup an invoice by id, scoped to the caller's own trader_id --
    the double .eq() filter is the tenant-isolation guard so one trader can't
    pull another trader's invoice data by id alone."""
    try:
        db = get_supabase()
        response = db.table("invoices").select("*, traders(business_name)").eq(
            "id", invoice_id
        ).eq("trader_id", trader_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to get invoice by id for trader: {e}")
        return None


# --- Practice Operations ---

def _retry_once_on_disconnect(describe: str, call):
    """
    Run one Supabase read, retrying once on a transport-level failure.

    A pooled HTTP/2 connection that the server has already closed surfaces
    as `RemoteProtocolError: Server disconnected` on the next request that
    picks it up. The retry gets a fresh connection. Only transport errors
    are retried -- a 4xx would fail again identically, and retrying it
    would just double the latency before the same error. Same rationale
    (and formerly the same code) as practice.py's own `_with_retry`, which
    the practice view's bulk reads relied on before this port; pulled in
    here rather than imported from practice.py so services/ doesn't depend
    on api/.
    """
    try:
        return call()
    except Exception as first:
        if "disconnect" not in str(first).lower() and "protocol" not in str(first).lower():
            raise
        logger.warning("%s hit a stale connection, retrying once: %s", describe, first)
        return call()


async def get_traders_by_ids(trader_ids: list[str]) -> list[dict]:
    """
    The client roster for the CA's practice view -- every trader row named
    in trader_ids, in one shot. Was practice.py's own `_fetch_traders`,
    moved here so both backends expose it through db.py like everything
    else. The caller already caps this list to one CA's clients (rarely
    more than a few dozen), so unlike the two bulk reads below, this is a
    single un-chunked `.in_()` query.

    Deliberately does not catch exceptions: a failed roster read is not a
    partial practice view, it's an empty one, and swallowing the error here
    would have the endpoint tell a CA "you have no clients" instead of
    surfacing something they can retry.
    """
    try:
        db = get_supabase()
        return _retry_once_on_disconnect(
            "trader roster",
            lambda: (
                db.table("traders")
                .select("id, name, business_name, gstin, whatsapp_number, is_composition, language_pref")
                .in_("id", trader_ids)
                .execute()
            ).data or [],
        )
    except Exception as e:
        logger.error(f"Failed to get traders by ids: {e}")
        raise


def _fetch_paged_for_traders(table: str, columns: str, trader_ids: list[str]) -> list[dict]:
    """
    One table, every listed trader, batched and paged. Shared by
    get_invoices_for_traders and get_gstr2b_records_for_traders below --
    was practice.py's generic `_fetch_all`, moved here so both backends
    expose these reads through db.py.

    The paging is not optional. PostgREST caps an unbounded select at 1,000
    rows and returns them with no error and no indication of truncation --
    one trader in this database has 2,319 GSTR-2B rows, so an earlier
    version of this read silently returned less than half of one client's
    data and computed a confident, wrong unclaimed-credit figure from it.

    Failures are logged and the batch skipped rather than aborting the
    whole read -- a practice list missing one client's numbers is more
    useful than an error page, provided the caller can tell, which the
    `{"__partial__": True}` sentinel appended on failure lets it do.
    """
    PAGE = 1000
    CHUNK = 40  # PostgREST URL-length limit
    db = get_supabase()
    rows: list[dict] = []
    ok = True
    for i in range(0, len(trader_ids), CHUNK):
        batch = trader_ids[i:i + CHUNK]
        offset = 0
        while True:
            try:
                page = _retry_once_on_disconnect(
                    f"{table} offset {offset}",
                    lambda: (
                        db.table(table)
                        .select(columns)
                        .in_("trader_id", batch)
                        .range(offset, offset + PAGE - 1)
                        .execute()
                    ).data or [],
                )
            except Exception as e:
                ok = False
                logger.error(
                    "practice bulk fetch: %s failed for %d traders at offset %d: %s",
                    table, len(batch), offset, e,
                )
                break
            rows.extend(page)
            if len(page) < PAGE:
                break
            offset += PAGE
    if not ok:
        rows.append({"__partial__": True})
    return rows


async def get_invoices_for_traders(trader_ids: list[str]) -> list[dict]:
    """Every invoice for a list of traders -- the practice overview's bulk
    invoice read. See `_fetch_paged_for_traders` for the paging/partial-
    result rationale."""
    return _fetch_paged_for_traders(
        "invoices",
        "trader_id, itc_status, itc_amount_eligible, itc_amount_blocked, "
        "itc_block_reason, invoice_date, processed_at, gstr2b_match_status, "
        "supplier_name, gstin_supplier",
        trader_ids,
    )


async def get_gstr2b_records_for_traders(trader_ids: list[str]) -> list[dict]:
    """Every GSTR-2B record for a list of traders -- the practice overview's
    bulk 2B read. See `_fetch_paged_for_traders` for the paging/partial-
    result rationale."""
    return _fetch_paged_for_traders(
        "gstr2b_records",
        "trader_id, month, year, matched_invoice_id, igst, cgst, sgst",
        trader_ids,
    )


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
