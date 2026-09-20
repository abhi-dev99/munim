"""
Munim-AI — DynamoDB Database Service (AWS port)

Drop-in replacement for supabase_client.py: same function names, same
signatures, same return shapes (plain dicts/lists, same field names) --
every api/*.py caller works unchanged. Swapped in via app/services/db.py
based on settings.data_backend, so this and Supabase can coexist without
either touching the other's data.

Deliberately separate tables from the invoice pipeline's own munim-traders/
munim-invoices (aws/lambdas/): those are already live with real pipeline
data and keyed on a simpler model (trader_id = phone number directly, no
separate id, no date-sortable range key) -- the dashboard's richer model
(a trader with its own uuid id, a distinct ca_whatsapp_number role, short
codes, etc.) doesn't fit that schema, and this migration must not risk the
already-working pipeline's tables to make room for it.

Table design (see local-notes for the full access-pattern research this
was built from):
  munim-dashboard-traders     PK id
    GSI ca-index               PK ca_whatsapp_number (canonical form only)
    GSI whatsapp-index          PK whatsapp_number
    GSI short-code-index        PK short_code (sparse -- only onboarded-via-QR traders have one)
    GSI inbound-email-index     PK inbound_email (sparse)
  munim-dashboard-invoices    PK trader_id, SK invoice_date#invoice_id
    GSI invoice-id-index        PK id (the invoice's own id -- point lookup
                                 when only the invoice id is known, not trader_id)
    GSI gstin-supplier-index    PK gstin_supplier (lean projection: trader_id,
                                 gstin_supplier, gstr2b_match_status, itc_status --
                                 the one genuinely cross-tenant read, network_intel.py)
  munim-suppliers               PK gstin (global, not per-trader -- confirmed:
                                 the daily health check scans this system-wide)
  munim-supplier-trader-links   PK trader_id, SK supplier_id
    GSI supplier-index          PK supplier_id (alert fanout: which traders
                                 does this supplier affect)
  munim-supplier-flags          PK supplier_id, SK flag_id
  munim-gstr2b-records          PK trader_id, SK supplier_gstin#year#month#invoice_number
                                 (matches the reconciler's real candidate-fetch
                                 pattern: by supplier, not by period)

Every function below fails the same way the Supabase version did: log and
return None/[]/{} rather than raise, since callers throughout the app were
written against that contract.
"""

import logging
import uuid
from decimal import Decimal
from functools import lru_cache
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

AWS_REGION = "ap-south-1"


@lru_cache()
def _resource():
    return boto3.resource("dynamodb", region_name=AWS_REGION)


def _table(name: str):
    return _resource().Table(name)


def _to_decimal(value):
    """DynamoDB has no float type -- every numeric write goes through this."""
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: _to_decimal(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_decimal(v) for v in value]
    return value


def _from_decimal(value):
    """Mirror conversion on read. boto3 always deserializes a DynamoDB Number
    as Decimal regardless of whether it was written as an int or a float --
    Decimal itself carries no such distinction. Values with no fractional
    part become int (matches what Supabase's Postgres client already hands
    callers for integer columns like month/year); anything with a
    fractional part becomes float. Blindly converting everything to float
    was the original version of this function -- caught rendering
    month/year as "5.0/2026" instead of "5/2026" downstream (practice.py's
    _unclaimed_for), the same bug already latent in gstr2b.py's month/year
    handling. Fixed here, once, rather than at every display site."""
    if isinstance(value, Decimal):
        as_int = int(value)
        return as_int if value == as_int else float(value)
    if isinstance(value, dict):
        return {k: _from_decimal(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_from_decimal(v) for v in value]
    return value


def _clean_item(item: dict) -> dict:
    return _from_decimal(item) if item else item


def _query_all(table, **query_kwargs) -> list[dict]:
    """Page a query to exhaustion via LastEvaluatedKey. A bare single
    table.query() truncates at DynamoDB's 1MB-per-call response limit with
    no error -- not a hypothetical for this data set: Raju's Kirana Store
    alone has 581 invoices and 2,319 GSTR-2B rows (see CLAUDE.md), either
    of which can plausibly cross 1MB unprojected. Every trader-scoped
    Query in this file that isn't already known-small should go through
    this rather than a bare table.query()."""
    items = []
    while True:
        resp = table.query(**query_kwargs)
        items.extend(resp.get("Items") or [])
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            return items
        query_kwargs["ExclusiveStartKey"] = last_key


def _invoice_sk(invoice_date: Optional[str], invoice_id: str) -> str:
    # Invoices without a recognised date sort first under "0000-00-00" rather
    # than crashing a range query -- matches how the real extractor already
    # treats a missing date (an honest gap, not a fabricated one).
    date_part = invoice_date if invoice_date else "0000-00-00"
    return f"{date_part}#{invoice_id}"


# --- Trader Operations ---

async def get_trader_by_phone(phone: str) -> Optional[dict]:
    """Find a trader by WhatsApp number, whatever spelling it is stored under."""
    from app.services.phone import match_variants

    try:
        table = _table("munim-dashboard-traders")
        for candidate in match_variants(phone) or [phone]:
            resp = table.query(
                IndexName="whatsapp-index",
                KeyConditionExpression=Key("whatsapp_number").eq(candidate),
            )
            items = resp.get("Items") or []
            if items:
                if len(items) > 1:
                    logger.warning(
                        "Multiple traders stored under %s — using %s", candidate, items[0].get("id")
                    )
                return _clean_item(items[0])
        return None
    except ClientError as e:
        logger.error(f"Failed to get trader by phone: {e}")
        return None


async def get_trader_by_short_code(short_code: str) -> Optional[dict]:
    try:
        table = _table("munim-dashboard-traders")
        resp = table.query(
            IndexName="short-code-index",
            KeyConditionExpression=Key("short_code").eq(short_code),
        )
        items = resp.get("Items") or []
        return _clean_item(items[0]) if items else None
    except ClientError as e:
        logger.error(f"Failed to get trader by short code: {e}")
        return None


async def get_trader_by_inbound_email(email: str) -> Optional[dict]:
    try:
        table = _table("munim-dashboard-traders")
        resp = table.query(
            IndexName="inbound-email-index",
            KeyConditionExpression=Key("inbound_email").eq(email),
        )
        items = resp.get("Items") or []
        return _clean_item(items[0]) if items else None
    except ClientError as e:
        logger.error(f"Failed to get trader by inbound email: {e}")
        return None


async def get_trader_by_id(trader_id: str) -> Optional[dict]:
    """Simple primary-key point lookup on munim-dashboard-traders."""
    try:
        table = _table("munim-dashboard-traders")
        resp = table.get_item(Key={"id": trader_id})
        return _clean_item(resp.get("Item"))
    except ClientError as e:
        logger.error(f"Failed to get trader by id: {e}")
        return None


async def create_trader(phone: str, gstin: str = None, name: str = None, business_name: str = None) -> Optional[dict]:
    try:
        table = _table("munim-dashboard-traders")
        item = {"id": str(uuid.uuid4()), "whatsapp_number": phone}
        if gstin:
            item["gstin"] = gstin
        if name:
            item["name"] = name
        if business_name:
            item["business_name"] = business_name
        table.put_item(Item=item, ConditionExpression=Attr("id").not_exists())
        return item
    except ClientError as e:
        logger.error(f"Failed to create trader: {e}")
        return None


async def update_trader(trader_id: str, updates: dict) -> Optional[dict]:
    try:
        table = _table("munim-dashboard-traders")
        expr_names = {f"#k{i}": k for i, k in enumerate(updates)}
        expr_values = {f":v{i}": _to_decimal(v) for i, v in enumerate(updates.values())}
        update_expr = "SET " + ", ".join(f"{n} = {v}" for n, v in zip(expr_names, expr_values))
        resp = table.update_item(
            Key={"id": trader_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ReturnValues="ALL_NEW",
        )
        return _clean_item(resp.get("Attributes"))
    except ClientError as e:
        logger.error(f"Failed to update trader: {e}")
        return None


async def resolve_trader_rows(column: str, canonical: str, variants: list[str]) -> list[dict]:
    """
    DynamoDB equivalent of auth.py's _resolve_trader_rows -- same
    wrong-identity guard, same precedence (exact canonical match wins
    outright; the looser variant fallback only applies, and only counts,
    when every row it returns belongs to the same trader). column is
    "whatsapp_number" or "ca_whatsapp_number", both of which have their
    own GSI on munim-dashboard-traders (see module docstring).

    The one real difference from the Supabase version: there's no native
    `.in_(column, variants)` on a DynamoDB GSI, so the variant fallback
    runs one Query per variant and merges results -- functionally
    identical, just N round trips instead of one.
    """
    index_name = "whatsapp-index" if column == "whatsapp_number" else "ca-index"
    table = _table("munim-dashboard-traders")

    try:
        exact_resp = table.query(
            IndexName=index_name,
            KeyConditionExpression=Key(column).eq(canonical),
        )
        exact_items = [_clean_item(i) for i in (exact_resp.get("Items") or [])]
        if exact_items:
            return exact_items

        fallback_items = []
        seen_ids = set()
        for variant in variants:
            resp = table.query(
                IndexName=index_name,
                KeyConditionExpression=Key(column).eq(variant),
            )
            for item in resp.get("Items") or []:
                if item["id"] not in seen_ids:
                    seen_ids.add(item["id"])
                    fallback_items.append(_clean_item(item))

        if not fallback_items:
            return []
        distinct_trader_ids = {row["id"] for row in fallback_items}
        if len(distinct_trader_ids) > 1:
            logger.error(
                f"Ambiguous phone match on {column}: variants {variants} matched "
                f"{len(distinct_trader_ids)} distinct traders {distinct_trader_ids}. Refusing to guess."
            )
            return []
        return fallback_items
    except ClientError as e:
        logger.error(f"Failed to resolve trader rows by {column}: {e}")
        return []


# --- Invoice Operations ---

async def store_invoice(invoice_data: dict) -> Optional[dict]:
    try:
        table = _table("munim-dashboard-invoices")
        item = dict(invoice_data)
        item.setdefault("id", str(uuid.uuid4()))
        item["sk"] = _invoice_sk(item.get("invoice_date"), item["id"])
        table.put_item(Item=_to_decimal(item))
        return _clean_item(item)
    except ClientError as e:
        logger.error(f"Failed to store invoice: {e}")
        return None


async def store_invoice_line_items(invoice_id: str, line_items: list, hsn_validations: list) -> None:
    try:
        table = _table("munim-invoice-line-items")
        with table.batch_writer() as batch:
            for i, item in enumerate(line_items):
                hsn_val = hsn_validations[i] if i < len(hsn_validations) else None
                row = {
                    "invoice_id": invoice_id,
                    "id": str(uuid.uuid4()),
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
                batch.put_item(Item=_to_decimal(row))
    except ClientError as e:
        logger.error(f"Failed to store line items: {e}")


async def get_invoices_for_trader(trader_id: str, month: int = None, year: int = None) -> list[dict]:
    try:
        table = _table("munim-dashboard-invoices")
        if month and year:
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
            raw_items = _query_all(
                table,
                KeyConditionExpression=(
                    Key("trader_id").eq(trader_id) & Key("sk").between(start_date, end_date)
                ),
            )
        else:
            raw_items = _query_all(table, KeyConditionExpression=Key("trader_id").eq(trader_id))
        items = [_clean_item(i) for i in raw_items]
        items.sort(key=lambda i: i.get("created_at") or "", reverse=True)
        return items
    except ClientError as e:
        logger.error(f"Failed to get invoices: {e}")
        return []


async def get_recent_invoice_locations(trader_id: str, limit: int = 20, exclude_invoice_id: str = None) -> list[dict]:
    try:
        table = _table("munim-dashboard-invoices")
        raw_items = _query_all(table, KeyConditionExpression=Key("trader_id").eq(trader_id))
        items = [_clean_item(i) for i in raw_items]
        items = [i for i in items if i.get("latitude") is not None and i.get("longitude") is not None]
        items.sort(key=lambda i: i.get("created_at") or "", reverse=True)
        if exclude_invoice_id:
            items = [i for i in items if i.get("id") != exclude_invoice_id]
        return [{"id": i["id"], "latitude": i["latitude"], "longitude": i["longitude"]} for i in items[:limit]]
    except ClientError as e:
        logger.error(f"Failed to get recent invoice locations: {e}")
        return []


async def get_invoices_by_gstin_suppliers(gstins: list[str]) -> list[dict]:
    """The one deliberately cross-tenant read in the codebase (see
    domain/network_intel.py's own docstring on _fetch_network_rows, which
    this replaces). Every invoice in the system from these supplier GSTINs,
    across ALL traders -- confined to this function, same as the Supabase
    version, so there's exactly one place to audit. Uses the
    gstin-supplier-index GSI (lean projection: trader_id, gstin_supplier,
    gstr2b_match_status, itc_status -- no amounts, no invoice numbers, no
    supplier-side contact data, enforced by the GSI's own projection, not
    just convention). DynamoDB has no IN-list scan on a GSI partition key,
    so this is one Query per GSTIN rather than Supabase's single
    chunked-IN call -- same total data, just N round trips instead of
    ceil(N/40)."""
    if not gstins:
        return []
    table = _table("munim-dashboard-invoices")
    rows = []
    for gstin in gstins:
        try:
            resp = table.query(
                IndexName="gstin-supplier-index",
                KeyConditionExpression=Key("gstin_supplier").eq(gstin),
            )
            rows.extend(_clean_item(i) for i in (resp.get("Items") or []))
        except ClientError as e:
            logger.error(f"network_intel: query failed for gstin {gstin}: {e}")
    return rows


async def check_duplicate_invoice(invoice_hash: str) -> bool:
    try:
        table = _table("munim-dashboard-invoices")
        resp = table.scan(
            FilterExpression=Attr("invoice_hash").eq(invoice_hash),
            ProjectionExpression="id",
        )
        return bool(resp.get("Items"))
    except ClientError as e:
        logger.error(f"Failed to check duplicate: {e}")
        return False


# --- Supplier Operations ---

async def get_or_create_supplier(gstin: str, legal_name: str = None) -> Optional[dict]:
    try:
        table = _table("munim-suppliers")
        resp = table.get_item(Key={"gstin": gstin})
        if "Item" in resp:
            return _clean_item(resp["Item"])
        item = {"gstin": gstin, "id": str(uuid.uuid4())}
        if legal_name:
            item["legal_name"] = legal_name
        table.put_item(Item=item, ConditionExpression=Attr("gstin").not_exists())
        return item
    except ClientError as e:
        logger.error(f"Failed to get/create supplier: {e}")
        return None


async def link_supplier_to_trader(trader_id: str, supplier_id: str) -> None:
    try:
        table = _table("munim-supplier-trader-links")
        resp = table.get_item(Key={"trader_id": trader_id, "supplier_id": supplier_id})
        if "Item" not in resp:
            table.put_item(Item={"trader_id": trader_id, "supplier_id": supplier_id, "total_invoice_count": 1})
        else:
            count = (resp["Item"].get("total_invoice_count") or 0) + 1
            table.update_item(
                Key={"trader_id": trader_id, "supplier_id": supplier_id},
                UpdateExpression="SET total_invoice_count = :c",
                ExpressionAttributeValues={":c": count},
            )
    except ClientError as e:
        logger.error(f"Failed to link supplier: {e}")


async def get_all_suppliers_for_trader(trader_id: str) -> list[dict]:
    """Denormalized: the link item carries a copy of the supplier's own
    fields (kept in sync by supplier_monitor's update_supplier), so this is
    one Query, no join/second read -- see update_supplier below."""
    try:
        table = _table("munim-supplier-trader-links")
        resp = table.query(KeyConditionExpression=Key("trader_id").eq(trader_id))
        links = [_clean_item(i) for i in (resp.get("Items") or [])]
        # Shape each link as {**link, "suppliers": {...}} to match the
        # Supabase embedded-select shape callers already expect.
        out = []
        for link in links:
            supplier_fields = {
                k: v for k, v in link.items()
                if k in (
                    "gstin", "legal_name", "trade_name", "taxpayer_type", "registration_date",
                    "business_category", "is_einvoice_mandated", "health_score", "last_verified_at",
                )
            }
            out.append({**link, "suppliers": supplier_fields})
        return out
    except ClientError as e:
        logger.error(f"Failed to get suppliers: {e}")
        return []


async def get_all_supplier_gstins() -> list[str]:
    try:
        table = _table("munim-suppliers")
        resp = table.scan(ProjectionExpression="gstin")
        return [r["gstin"] for r in (resp.get("Items") or [])]
    except ClientError as e:
        logger.error(f"Failed to get supplier GSTINs: {e}")
        return []


async def update_supplier(supplier_id: str, updates: dict) -> None:
    """Updates munim-suppliers by gstin (supplier_id IS the gstin here --
    every caller in this codebase already passes a gstin-shaped value in,
    confirmed against supplier_monitor.py/gstr2b.py call sites), and fans
    the same field changes out to every trader's link item so
    get_all_suppliers_for_trader's denormalized copy never goes stale."""
    try:
        suppliers_table = _table("munim-suppliers")
        expr_names = {f"#k{i}": k for i, k in enumerate(updates)}
        expr_values = {f":v{i}": _to_decimal(v) for i, v in enumerate(updates.values())}
        update_expr = "SET " + ", ".join(f"{n} = {v}" for n, v in zip(expr_names, expr_values))
        suppliers_table.update_item(
            Key={"gstin": supplier_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )

        links_table = _table("munim-supplier-trader-links")
        resp = links_table.query(
            IndexName="supplier-index",
            KeyConditionExpression=Key("supplier_id").eq(supplier_id),
        )
        for link in resp.get("Items") or []:
            links_table.update_item(
                Key={"trader_id": link["trader_id"], "supplier_id": supplier_id},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
            )
    except ClientError as e:
        logger.error(f"Failed to update supplier: {e}")


async def add_supplier_flag(supplier_id: str, flag_type: str, metadata: dict = None) -> None:
    try:
        table = _table("munim-supplier-flags")
        table.put_item(Item=_to_decimal({
            "supplier_id": supplier_id,
            "id": str(uuid.uuid4()),
            "flag_type": flag_type,
            "metadata": metadata or {},
            "is_active": True,
        }))
    except ClientError as e:
        logger.error(f"Failed to add supplier flag: {e}")


async def get_active_supplier_flags(supplier_id: str) -> list[dict]:
    try:
        table = _table("munim-supplier-flags")
        resp = table.query(
            KeyConditionExpression=Key("supplier_id").eq(supplier_id),
            FilterExpression=Attr("is_active").eq(True),
        )
        return [_clean_item(i) for i in (resp.get("Items") or [])]
    except ClientError as e:
        logger.error(f"Failed to get supplier flags: {e}")
        return []


# --- GSTR-2B Operations ---

async def get_gstr2b_records(trader_id: str, month: int = None, year: int = None, unmatched_only: bool = False) -> list[dict]:
    try:
        table = _table("munim-gstr2b-records")
        raw_items = _query_all(table, KeyConditionExpression=Key("trader_id").eq(trader_id))
        items = [_clean_item(i) for i in raw_items]
        if month:
            items = [i for i in items if i.get("month") == month]
        if year:
            items = [i for i in items if i.get("year") == year]
        if unmatched_only:
            items = [i for i in items if not i.get("matched_invoice_id")]
        return items
    except ClientError as e:
        logger.error(f"Failed to get GSTR-2B records: {e}")
        return []


async def mark_gstr2b_record_matched(record_id: str, invoice_id: str) -> None:
    """Every gstr2b-records item carries its own `id` (set at upsert time,
    same as every other table here) plus an `id-index` GSI -- record_id is
    that plain id, exactly like the Supabase version, no composite-key
    encoding needed."""
    try:
        table = _table("munim-gstr2b-records")
        resp = table.query(IndexName="id-index", KeyConditionExpression=Key("id").eq(record_id))
        items = resp.get("Items") or []
        if not items:
            logger.error(f"mark_gstr2b_record_matched: no record found for id {record_id}")
            return
        table.update_item(
            Key={"trader_id": items[0]["trader_id"], "sk": items[0]["sk"]},
            UpdateExpression="SET matched_invoice_id = :i",
            ExpressionAttributeValues={":i": invoice_id},
        )
    except ClientError as e:
        logger.error(f"Failed to mark GSTR-2B record as matched: {e}")


async def upsert_gstr2b_record(
    trader_id: str, month: int, year: int, supplier_gstin: str, invoice_number: str, fields: dict
) -> None:
    """
    Upsert via put_item on the fixed key (trader_id, sk) -- sk is
    f"{supplier_gstin}#{year:04d}#{month:02d}#{invoice_number}", matching the
    Supabase side's (trader_id,month,year,supplier_gstin,invoice_number)
    unique key.

    A bare put_item would replace the whole item, silently destroying `id`
    (the id-index GSI mark_gstr2b_record_matched relies on) and
    `matched_invoice_id` (what get_missed_itc_snapshot's `reconciled` flag is
    derived from) on every re-upload of a period. Read the existing item
    first and carry both forward -- Supabase's `.upsert(..., on_conflict=...)`
    does this for free by only touching the listed columns; this is the
    DynamoDB equivalent of that guarantee.

    Does NOT catch ClientError -- see the Supabase twin's docstring for why
    the upload endpoints' inserted/skipped counters depend on this raising.
    """
    table = _table("munim-gstr2b-records")
    sk = f"{supplier_gstin}#{year:04d}#{month:02d}#{invoice_number}"
    existing = table.get_item(Key={"trader_id": trader_id, "sk": sk}).get("Item") or {}
    item = {
        "id": existing.get("id") or str(uuid.uuid4()),
        "trader_id": trader_id,
        "sk": sk,
        "month": month,
        "year": year,
        "supplier_gstin": supplier_gstin,
        "invoice_number": invoice_number,
        **fields,
    }
    if existing.get("matched_invoice_id"):
        item["matched_invoice_id"] = existing["matched_invoice_id"]
    table.put_item(Item=_to_decimal(item))


async def delete_gstr2b_b2b_record(trader_id: str, supplier_gstin: str, invoice_number: str) -> None:
    """
    Delete the B2B row a B2BA amendment supersedes. sk is period-specific
    (see upsert_gstr2b_record), so this can't be an exact-key delete -- query
    the supplier's slice of the trader's partition via begins_with and filter
    on record_type/invoice_number in Python, matching the Supabase side's
    unfiltered-by-period delete.

    Does NOT catch ClientError -- same reasoning as upsert_gstr2b_record.
    """
    table = _table("munim-gstr2b-records")
    resp = table.query(
        KeyConditionExpression=Key("trader_id").eq(trader_id) & Key("sk").begins_with(f"{supplier_gstin}#"),
    )
    for item in resp.get("Items") or []:
        if item.get("record_type") == "B2B" and item.get("invoice_number") == invoice_number:
            table.delete_item(Key={"trader_id": trader_id, "sk": item["sk"]})


async def delete_gstr2b_records_for_period(trader_id: str, month: int, year: int) -> None:
    """Clear every GSTR-2B row for one trader+period (e.g. before a re-upload)."""
    try:
        table = _table("munim-gstr2b-records")
        resp = table.query(KeyConditionExpression=Key("trader_id").eq(trader_id))
        items = [
            i for i in (resp.get("Items") or [])
            if i.get("month") == month and i.get("year") == year
        ]
        with table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={"trader_id": trader_id, "sk": item["sk"]})
    except ClientError as e:
        logger.error(f"Failed to delete GSTR-2B records for period: {e}")


async def get_supplier_by_gstin(gstin: str) -> Optional[dict]:
    """
    Read-only point lookup by gstin. Unlike get_or_create_supplier, never
    creates a row -- for display-only paths (e.g. missed-ITC supplier names
    on the dashboard) that must stay pure reads.
    """
    try:
        table = _table("munim-suppliers")
        resp = table.get_item(Key={"gstin": gstin})
        return _clean_item(resp.get("Item"))
    except ClientError as e:
        logger.error(f"Failed to get supplier by gstin: {e}")
        return None


# --- Dashboard Operations ---

async def get_recent_invoices(trader_id: str, limit: int = 5) -> list[dict]:
    try:
        table = _table("munim-dashboard-invoices")
        resp = table.query(
            KeyConditionExpression=Key("trader_id").eq(trader_id),
            ScanIndexForward=False,  # sk is date-prefixed, so this is newest-first
            Limit=limit,
            ProjectionExpression="supplier_name, total_amount, itc_status, invoice_date",
        )
        return [_clean_item(i) for i in (resp.get("Items") or [])]
    except ClientError as e:
        logger.error(f"Failed to get recent invoices: {e}")
        return []


async def get_itc_summary(trader_id: str) -> dict:
    try:
        table = _table("munim-dashboard-invoices")
        resp = table.query(
            KeyConditionExpression=Key("trader_id").eq(trader_id),
            ProjectionExpression="itc_status, itc_amount_eligible, itc_amount_blocked",
        )
        buckets = {"confirmed": 0.0, "fixable_blocked": 0.0, "at_risk": 0.0, "missed": 0.0, "ineligible": 0.0}
        for inv in (resp.get("Items") or []):
            status = inv.get("itc_status", "")
            eligible = float(inv.get("itc_amount_eligible") or 0)
            blocked = float(inv.get("itc_amount_blocked") or 0)
            if status == "CONFIRMED":
                buckets["confirmed"] += eligible
            elif status in ("FIXABLE_BLOCKED", "FRAUD_FLAGGED", "DUPLICATE"):
                buckets["fixable_blocked"] += blocked
            elif status == "AT_RISK":
                buckets["at_risk"] += eligible or blocked
            elif status == "MISSED":
                buckets["missed"] += eligible
            elif status == "INELIGIBLE":
                buckets["ineligible"] += blocked

        try:
            unmatched = await get_gstr2b_records(trader_id, unmatched_only=True)
            for rec in unmatched:
                if rec.get("record_type", "B2B") in ("B2B", "B2BA"):
                    tax_val = float(rec.get("igst") or 0) + float(rec.get("cgst") or 0) + float(rec.get("sgst") or 0)
                    if tax_val == 0.0 and rec.get("total_tax"):
                        tax_val = float(rec.get("total_tax") or 0)
                    buckets["missed"] += tax_val
        except Exception as e:
            logger.warning(f"Could not compute unmatched GSTR-2B missed ITC: {e}")

        return buckets
    except ClientError as e:
        logger.error(f"Failed to compute ITC summary: {e}")
        return {}


# --- Report Operations ---

async def get_reports_for_trader(trader_id: str) -> list[dict]:
    """Munim Reports for a trader, newest first -- sk is REPORT#year#month
    (zero-padded), so DynamoDB's own descending sort order on the range key
    already gives us newest-first, no Python-side sort needed (unlike the
    Supabase version's two-column order-by)."""
    try:
        table = _table("munim-reports")
        resp = table.query(
            KeyConditionExpression=Key("trader_id").eq(trader_id),
            ScanIndexForward=False,
        )
        return [_clean_item(i) for i in (resp.get("Items") or [])]
    except ClientError as e:
        logger.error(f"Failed to list generated reports: {e}")
        return []


async def upsert_report(trader_id: str, month: int, year: int, fields: dict) -> None:
    """Create or replace a trader's monthly report metadata item -- a
    put_item of the full item, matching Supabase's upsert-on-conflict
    semantics (full row replace, not a partial field merge)."""
    try:
        table = _table("munim-reports")
        item = {
            "trader_id": trader_id,
            "month": month,
            "year": year,
            "sk": f"REPORT#{year:04d}#{month:02d}",
            **fields,
        }
        table.put_item(Item=_to_decimal(item))
    except ClientError as e:
        logger.error(f"Failed to store report metadata: {e}")


# --- Communications Operations ---

async def update_invoice_by_id(invoice_id: str, updates: dict) -> None:
    """invoices are keyed (trader_id, sk), not just id -- point-lookup the
    real key via the invoice-id-index GSI first, then update_item on it."""
    try:
        table = _table("munim-dashboard-invoices")
        resp = table.query(IndexName="invoice-id-index", KeyConditionExpression=Key("id").eq(invoice_id))
        items = resp.get("Items") or []
        if not items:
            logger.error(f"update_invoice_by_id: no invoice found for id {invoice_id}")
            return
        expr_names = {f"#k{i}": k for i, k in enumerate(updates)}
        expr_values = {f":v{i}": _to_decimal(v) for i, v in enumerate(updates.values())}
        update_expr = "SET " + ", ".join(f"{n} = {v}" for n, v in zip(expr_names, expr_values))
        table.update_item(
            Key={"trader_id": items[0]["trader_id"], "sk": items[0]["sk"]},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )
    except ClientError as e:
        logger.error(f"Failed to update invoice {invoice_id}: {e}")


async def get_invoice_by_id(invoice_id: str) -> Optional[dict]:
    """Plain point lookup by id, no tenant check -- for the one legitimate
    case that needs to know an invoice's owner BEFORE it can check access
    (dashboard.py's resolve_action_item does its own verify_trader_access
    right after). Anything that already knows the expected trader_id should
    use get_invoice_by_id_for_trader instead, which enforces the match."""
    try:
        table = _table("munim-dashboard-invoices")
        resp = table.query(IndexName="invoice-id-index", KeyConditionExpression=Key("id").eq(invoice_id))
        items = resp.get("Items") or []
        return _clean_item(items[0]) if items else None
    except ClientError as e:
        logger.error(f"Failed to get invoice by id: {e}")
        return None


async def get_invoice_by_id_for_trader(invoice_id: str, trader_id: str) -> Optional[dict]:
    """invoice-id-index GSI point lookup, then a tenant check standing in for
    Supabase's double .eq() filter (returns None on a mismatch rather than
    leaking another trader's invoice), then a separate trader read to merge
    business_name in under a "traders" key -- matches the embedded-select
    shape callers already expect."""
    try:
        table = _table("munim-dashboard-invoices")
        resp = table.query(IndexName="invoice-id-index", KeyConditionExpression=Key("id").eq(invoice_id))
        items = resp.get("Items") or []
        if not items:
            return None
        invoice = _clean_item(items[0])
        if invoice.get("trader_id") != trader_id:
            return None
        trader = await get_trader_by_id(trader_id)
        invoice["traders"] = {"business_name": trader.get("business_name") if trader else None}
        return invoice
    except ClientError as e:
        logger.error(f"Failed to get invoice by id for trader: {e}")
        return None


# --- Practice Operations ---

async def get_traders_by_ids(trader_ids: list[str]) -> list[dict]:
    """
    The client roster for the CA's practice view -- munim-dashboard-traders
    is keyed on `id` alone (simple PK, no sort key), so this is a
    `batch_get_item` rather than N point lookups. boto3 caps a single
    `batch_get_item` call at 100 keys; the caller already scopes this to one
    CA's clients (rarely more than a few dozen), but the batching loop below
    chunks into groups of 100 anyway so this stays correct if that ever
    changes.

    Deliberately does not catch ClientError: a failed roster read is not a
    partial practice view, it's an empty one, and swallowing the error here
    would have the endpoint tell a CA "you have no clients" instead of
    surfacing something they can retry -- matches the Supabase twin.
    """
    if not trader_ids:
        return []
    table_name = "munim-dashboard-traders"
    client = _resource().meta.client
    rows: list[dict] = []
    for i in range(0, len(trader_ids), 100):
        batch = trader_ids[i:i + 100]
        keys = [{"id": tid} for tid in batch]
        request = {table_name: {"Keys": keys}}
        while request:
            resp = client.batch_get_item(RequestItems=request)
            rows.extend(_clean_item(item) for item in resp.get("Responses", {}).get(table_name, []))
            unprocessed = resp.get("UnprocessedKeys") or {}
            request = unprocessed if unprocessed else None
    return rows


def _query_all_for_trader(table, trader_id: str) -> list[dict]:
    """A single trader's full partition, paged to exhaustion.

    boto3's `Table.query()` caps a single call at 1MB and does not
    auto-paginate -- it returns a `LastEvaluatedKey` instead of raising when
    there's more. A trader with 2,319 GSTR-2B rows (see practice.py's module
    docstring) sits right around that line, so a bare single `query()` here
    would silently drop the tail the same way an un-paged PostgREST select
    silently caps at 1,000 rows -- the exact failure mode the Supabase side
    of this file is written to avoid.
    """
    items: list[dict] = []
    kwargs = {"KeyConditionExpression": Key("trader_id").eq(trader_id)}
    while True:
        resp = table.query(**kwargs)
        items.extend(_clean_item(i) for i in (resp.get("Items") or []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key
    return items


async def get_invoices_for_traders(trader_ids: list[str]) -> list[dict]:
    """
    Every invoice for a list of traders -- the practice overview's bulk
    invoice read. DynamoDB has no cross-partition-key IN query, so this is
    one `get_invoices_for_trader`-style Query per trader_id, concatenated
    (each one itself paged to exhaustion -- see `_query_all_for_trader`).

    On a trader's query failing, a `{"__partial__": True}` sentinel is
    appended and the loop continues with the next trader_id -- a practice
    list missing one client's numbers is more useful than an error page,
    provided the caller can tell, which the sentinel lets it do (matches
    the Supabase twin's per-batch behaviour).
    """
    table = _table("munim-dashboard-invoices")
    rows: list[dict] = []
    for trader_id in trader_ids:
        try:
            rows.extend(_query_all_for_trader(table, trader_id))
        except ClientError as e:
            logger.error(f"practice bulk fetch: invoices query failed for trader {trader_id}: {e}")
            rows.append({"__partial__": True})
    return rows


async def get_gstr2b_records_for_traders(trader_ids: list[str]) -> list[dict]:
    """Every GSTR-2B record for a list of traders -- the practice overview's
    bulk 2B read. See get_invoices_for_traders above for the per-trader-Query,
    paging and partial-result rationale."""
    table = _table("munim-gstr2b-records")
    rows: list[dict] = []
    for trader_id in trader_ids:
        try:
            rows.extend(_query_all_for_trader(table, trader_id))
        except ClientError as e:
            logger.error(f"practice bulk fetch: gstr2b_records query failed for trader {trader_id}: {e}")
            rows.append({"__partial__": True})
    return rows


# --- File Storage ---

async def upload_file(bucket: str, path: str, file_bytes: bytes, content_type: str = "image/jpeg") -> Optional[str]:
    """S3 equivalent of Supabase Storage's upload+get_public_url pair --
    except the bucket here is NOT public (matches this build's security
    posture: every other bucket in the AWS pipeline is private, accessed
    through a gated Lambda or a signed URL, never a raw public one). A
    flat https://bucket.s3.../key URL would silently 403 for anyone who
    tries it -- WhatsApp's document send included -- so this returns a
    presigned URL instead: same "here's a working link" contract callers
    already expect, just time-limited (7 days, S3's own presign max)
    rather than permanently public."""
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        bucket_name = f"munim-{bucket}-753654068031-{AWS_REGION}"
        s3.put_object(Bucket=bucket_name, Key=path, Body=file_bytes, ContentType=content_type)
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": path},
            ExpiresIn=7 * 24 * 3600,
        )
    except ClientError as e:
        logger.error(f"Failed to upload file: {e}")
        return None
