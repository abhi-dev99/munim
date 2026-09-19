"""
Munim.ai — GSTR-2B Upload API
Allows traders (or CAs) to upload their GSTR-2B JSON export from the GST portal.
Parses and stores records for reconciliation against processed invoices.
"""

import json
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from app.api.deps import verify_trader_access, get_current_trader_id, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.services.supabase_client import get_supabase
from app.utils.errors import safe_http_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/gstr2b", tags=["gstr2b"])


class GSTR2BRecordInput(BaseModel):
    """Single GSTR-2B record from the GST portal JSON export."""
    supplier_gstin: str
    invoice_number: str
    invoice_date: str          # YYYY-MM-DD
    taxable_value: float
    igst: float = 0.0
    cgst: float = 0.0
    sgst: float = 0.0
    itc_eligible: bool = True
    record_type: str = "B2B"   # B2B | CDNR | CDNA | B2BA


class GSTR2BBulkUpload(BaseModel):
    """Bulk upload request body."""
    trader_id: str
    month: int
    year: int
    records: list[GSTR2BRecordInput]


@router.post("/upload")
async def upload_gstr2b_json(payload: GSTR2BBulkUpload, current_trader_id: str = Depends(get_current_trader_id)):
    """
    Upload GSTR-2B records parsed from GST portal JSON export.
    Use this when you have the JSON data already parsed client-side.
    """
    # trader_id arrives in the body, so verify_trader_access can't be wired in
    # as a FastAPI dependency (it reads trader_id from the path) -- call it
    # directly, the way webhook.py does. A raw equality check here rejected a
    # CA uploading GSTR-2B for their own client, which is the CA's core job.
    await verify_trader_access(payload.trader_id, current_trader_id)

    if not 1 <= payload.month <= 12:
        raise HTTPException(status_code=400, detail="month must be 1-12")
    if payload.year < 2020 or payload.year > date.today().year + 1:
        raise HTTPException(status_code=400, detail="Invalid year")
    if not payload.records:
        raise HTTPException(status_code=400, detail="No records provided")

    db = get_supabase()
    inserted = 0
    skipped = 0

    for rec in payload.records:
        try:
            row = {
                "trader_id": payload.trader_id,
                "month": payload.month,
                "year": payload.year,
                "supplier_gstin": rec.supplier_gstin.upper().strip(),
                "invoice_number": rec.invoice_number.strip(),
                "invoice_date": rec.invoice_date,
                "taxable_value": rec.taxable_value,
                "igst": rec.igst,
                "cgst": rec.cgst,
                "sgst": rec.sgst,
                "itc_eligible": rec.itc_eligible,
                "record_type": rec.record_type,
            }
            # B2BA amendments supersede the original — delete old B2B row first
            if rec.record_type == "B2BA":
                db.table("gstr2b_records").delete().eq(
                    "trader_id", payload.trader_id
                ).eq("supplier_gstin", rec.supplier_gstin.upper().strip()
                ).eq("invoice_number", rec.invoice_number.strip()
                ).eq("record_type", "B2B").execute()
            db.table("gstr2b_records").upsert(
                row, on_conflict="trader_id,month,year,supplier_gstin,invoice_number"
            ).execute()
            inserted += 1
        except Exception as e:
            logger.warning(f"Skipped GSTR-2B record {rec.invoice_number}: {e}")
            skipped += 1

    return {
        "status": "uploaded",
        "inserted": inserted,
        "skipped": skipped,
        "month": payload.month,
        "year": payload.year,
    }


@router.post("/upload-file/{trader_id}")
async def upload_gstr2b_file(
    month: int = Form(...),
    year: int = Form(...),
    file: UploadFile = File(...),
    trader_id: str = Depends(verify_trader_access),
):
    """
    Upload GSTR-2B as a raw JSON file or Excel file (downloaded from GST portal).
    Handles the standard GST portal GSTR-2B formats.
    """
    # trader_id comes from the path, so the same dependency the read/clear/
    # reconcile endpoints use applies here -- it allows the trader and any CA
    # whose phone matches the trader's ca_whatsapp_number.
    is_excel = file.filename.endswith(('.xlsx', '.xls')) or "spreadsheet" in file.content_type or "excel" in file.content_type
    if not is_excel and file.content_type not in ("application/json", "text/plain", "application/octet-stream"):
        raise HTTPException(
            status_code=400,
            detail="Only JSON or Excel files accepted. Download GSTR-2B from GST portal and upload here."
        )

    content = await file.read()
    
    if is_excel:
        records = _parse_gst_portal_excel(content)
        if not records:
            raise HTTPException(
                status_code=400,
                detail="Could not parse GSTR-2B records from this Excel file. "
                       "Ensure it is the standard GST portal GSTR-2B format."
            )
    else:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON file")

        records = _parse_gst_portal_json(data)
        if not records:
            raise HTTPException(
                status_code=400,
                detail="Could not parse GSTR-2B records from this JSON file. "
                       "Expected GST portal GSTR-2B JSON format."
            )

    db = get_supabase()
    inserted = 0
    skipped = 0

    for rec in records:
        try:
            row = {"trader_id": trader_id, "month": month, "year": year, **rec}
            # B2BA amendments supersede the original — delete old B2B row first
            if rec.get("record_type") == "B2BA":
                db.table("gstr2b_records").delete().eq(
                    "trader_id", trader_id
                ).eq("supplier_gstin", rec["supplier_gstin"]
                ).eq("invoice_number", rec["invoice_number"]
                ).eq("record_type", "B2B").execute()
            db.table("gstr2b_records").upsert(
                row, on_conflict="trader_id,month,year,supplier_gstin,invoice_number"
            ).execute()
            inserted += 1
        except Exception as e:
            logger.warning(f"Skipped record: {e}")
            skipped += 1

    return {
        "status": "uploaded",
        "inserted": inserted,
        "skipped": skipped,
        "month": month,
        "year": year,
        "filename": file.filename,
    }

def _parse_gst_portal_excel(content: bytes) -> list[dict]:
    import io
    import pandas as pd
    records = []
    
    try:
        xls = pd.ExcelFile(io.BytesIO(content))
        sheet_name = "B2B" if "B2B" in xls.sheet_names else xls.sheet_names[0]
        df = pd.read_excel(xls, sheet_name=sheet_name)
        
        # GST portal Excel often has headers at row 5. Let's find the header row by looking for "GSTIN"
        header_row_idx = -1
        for i, row in df.iterrows():
            if any(isinstance(val, str) and "GSTIN" in str(val).upper() for val in row.values):
                header_row_idx = i
                break
                
        if header_row_idx != -1:
            df.columns = df.iloc[header_row_idx]
            df = df.iloc[header_row_idx + 1:]
            
        # Clean column names
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # Expected columns (fuzzy match)
        gstin_col = next((c for c in df.columns if "gstin" in c and "supplier" in c), None) or next((c for c in df.columns if "gstin" in c), None)
        inv_col = next((c for c in df.columns if "invoice no" in c or "invoice number" in c), None)
        date_col = next((c for c in df.columns if "invoice date" in c), None)
        taxval_col = next((c for c in df.columns if "taxable value" in c), None)
        igst_col = next((c for c in df.columns if "integrated tax" in c or "igst" in c), None)
        cgst_col = next((c for c in df.columns if "central tax" in c or "cgst" in c), None)
        sgst_col = next((c for c in df.columns if "state" in c and "tax" in c or "sgst" in c), None)
        
        if gstin_col and inv_col and date_col:
            for _, row in df.iterrows():
                gstin = str(row[gstin_col]).strip()
                inv_no = str(row[inv_col]).strip()
                if not gstin or gstin.lower() == "nan" or not inv_no or inv_no.lower() == "nan":
                    continue
                    
                date_val = str(row[date_col]).strip()
                date_val = date_val.split(" ")[0] # in case of datetime
                # normalize date format
                if "-" in date_val:
                    parts = date_val.split("-")
                    if len(parts) == 3:
                        if len(parts[2]) == 4: # DD-MM-YYYY
                            date_val = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                        elif len(parts[0]) == 4: # YYYY-MM-DD
                            date_val = f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
                
                try:
                    tv = float(row[taxval_col]) if taxval_col and not pd.isna(row[taxval_col]) else 0.0
                except: tv = 0.0
                
                try:
                    ig = float(row[igst_col]) if igst_col and not pd.isna(row[igst_col]) else 0.0
                except: ig = 0.0
                
                try:
                    cg = float(row[cgst_col]) if cgst_col and not pd.isna(row[cgst_col]) else 0.0
                except: cg = 0.0
                
                try:
                    sg = float(row[sgst_col]) if sgst_col and not pd.isna(row[sgst_col]) else 0.0
                except: sg = 0.0
                
                records.append({
                    "supplier_gstin": gstin.upper(),
                    "invoice_number": inv_no,
                    "invoice_date": date_val,
                    "taxable_value": tv,
                    "igst": ig,
                    "cgst": cg,
                    "sgst": sg,
                    "itc_eligible": True
                })
    except Exception as e:
        logger.error(f"GSTR-2B Excel parse error: {e}")
        
    return records

@router.get("/records/{trader_id}")
async def get_gstr2b_records(trader_id: str = Depends(verify_trader_access), month: int = None, year: int = None):
    """Get all GSTR-2B records for a trader."""
    try:
        db = get_supabase()
        query = db.table("gstr2b_records").select("*").eq("trader_id", trader_id)
        if month:
            query = query.eq("month", month)
        if year:
            query = query.eq("year", year)
        response = query.order("invoice_date", desc=True).execute()
        return {
            "records": response.data or [],
            "total": len(response.data or []),
        }
    except Exception as e:
        raise safe_http_error(logger, "Failed to fetch GSTR-2B records", e)


async def get_missed_itc_snapshot(
    trader_id: str,
    month: Optional[int] = None,
    year: Optional[int] = None,
) -> dict:
    """
    Input tax credit the supplier has already reported but the trader never
    claimed — GSTR-2B rows with no invoice matched against them.

    This is deliberately a READ. The reconcile endpoint computes the same
    figure, but it also writes match results and can fire vendor warnings when
    auto_warn_vendors is on, so a dashboard panel must never call it just to
    display a number.

    Split out from the route so the recovery loop (`services/itc_recovery`)
    computes the figure the same way the panel displays it, rather than growing
    a second implementation that drifts. Authorisation stays on the route: this
    function trusts the trader_id it is given.
    """
    try:
        db = get_supabase()

        # Default to the newest period this trader actually has 2B data for,
        # not to today. GSTR-2B for a month is published after the 14th of the
        # next one, so "today" is routinely a period with nothing in it — and
        # opening on an empty month reads as "no unclaimed credit" when the
        # real answer is "we haven't looked at a month you have data for."
        if not month or not year:
            latest = (
                db.table("gstr2b_records")
                .select("month, year")
                .eq("trader_id", trader_id)
                .order("year", desc=True)
                .order("month", desc=True)
                .limit(1)
                .execute()
            ).data
            if latest:
                month = month or latest[0]["month"]
                year = year or latest[0]["year"]
            else:
                now = date.today()
                month = month or now.month
                year = year or now.year

        unmatched = (
            db.table("gstr2b_records")
            .select("*")
            .eq("trader_id", trader_id)
            .eq("month", month)
            .eq("year", year)
            .is_("matched_invoice_id", "null")
            .execute()
        ).data or []

        total_2b = (
            db.table("gstr2b_records")
            .select("id", count="exact")
            .eq("trader_id", trader_id)
            .eq("month", month)
            .eq("year", year)
            .limit(1)
            .execute()
        ).count or 0

        # An unmatched row only means "unclaimed" if matching has actually been
        # persisted. The test has to be the very column being filtered on:
        # invoices carry a gstr2b_match_status, but until the back-link fix
        # landed nothing ever wrote gstr2b_records.matched_invoice_id, so a
        # trader can have a fully reconciled invoice set and still show every
        # 2B row as unmatched. Checking the invoice side would report the whole
        # 2B value as unclaimed credit — confidently, and wrongly.
        linked_count = (
            db.table("gstr2b_records")
            .select("id", count="exact")
            .eq("trader_id", trader_id)
            .eq("month", month)
            .eq("year", year)
            .not_.is_("matched_invoice_id", "null")
            .limit(1)
            .execute()
        ).count or 0
        reconciled = linked_count > 0

        gstins = {r.get("supplier_gstin") for r in unmatched if r.get("supplier_gstin")}
        names: dict[str, str] = {}
        if gstins:
            sup = (
                db.table("suppliers")
                .select("gstin, legal_name, trade_name")
                .in_("gstin", list(gstins))
                .execute()
            ).data or []
            names = {
                s["gstin"]: (s.get("trade_name") or s.get("legal_name") or "")
                for s in sup
                if s.get("gstin")
            }

        records = []
        for r in unmatched:
            tax = float(r.get("igst") or 0) + float(r.get("cgst") or 0) + float(r.get("sgst") or 0)
            taxable = float(r.get("taxable_value") or 0)
            records.append({
                "record_id": r.get("id"),
                "supplier_gstin": r.get("supplier_gstin"),
                "supplier_name": names.get(r.get("supplier_gstin")) or "Unknown supplier",
                "invoice_number": r.get("invoice_number"),
                "invoice_date": r.get("invoice_date"),
                "taxable_value": round(taxable, 2),
                "tax": round(tax, 2),
                "total": round(taxable + tax, 2),
            })

        records.sort(key=lambda x: x["tax"], reverse=True)

        return {
            "period": f"{month}/{year}",
            "month": month,
            "year": year,
            "reconciled": reconciled,
            "note": None if reconciled else (
                "No GSTR-2B row in this period carries a match yet, so every "
                "row still counts as unmatched. Run reconciliation before "
                "treating this figure as unclaimed credit."
            ),
            "gstr2b_records": total_2b,
            "count": len(records),
            "unclaimed_tax": round(sum(r["tax"] for r in records), 2),
            "unclaimed_taxable": round(sum(r["taxable_value"] for r in records), 2),
            "records": records,
        }
    except Exception as e:
        raise safe_http_error(logger, "Failed to compute missed ITC", e)


@router.get("/missed-itc/{trader_id}")
async def get_missed_itc(
    trader_id: str = Depends(verify_trader_access),
    month: int = None,
    year: int = None,
):
    """Unclaimed credit for a period. See `get_missed_itc_snapshot`."""
    return await get_missed_itc_snapshot(trader_id, month, year)


class AskTraderRequest(BaseModel):
    month: Optional[int] = None
    year: Optional[int] = None
    limit: int = 3


@router.post("/missed-itc/{trader_id}/ask")
async def ask_trader_for_missing_bills(
    payload: AskTraderRequest,
    trader_id: str = Depends(verify_trader_access),
):
    """
    Ask the trader, over WhatsApp, whether they have the bills behind their
    largest unclaimed credit.

    This sends a real message to a real person, so it is a POST, it is never
    called on render, and it refuses in every case where the question would be
    wrong: nothing unclaimed, nothing reconciled yet, no number on file, or
    already asked. The result says which, in words a CA can act on.
    """
    from app.services.itc_recovery import ask_trader

    try:
        result = await ask_trader(trader_id, payload.month, payload.year, payload.limit)
        # Only "sent" means a message went out. Everything else is a reason
        # nothing was sent, and the UI shows it as such rather than as success.
        return {"trader_id": trader_id, **result}
    except HTTPException:
        raise
    except Exception as e:
        raise safe_http_error(logger, "Failed to ask the trader about unclaimed bills", e)


@router.get("/missed-itc/{trader_id}/requests")
async def list_recovery_requests(trader_id: str = Depends(verify_trader_access)):
    """Every bill we have asked this trader about, and what they said."""
    from app.services.itc_recovery import summary_for

    try:
        return {"trader_id": trader_id, **summary_for(trader_id)}
    except Exception as e:
        raise safe_http_error(logger, "Failed to list recovery requests", e)


@router.delete("/records/{trader_id}")
async def clear_gstr2b_records(month: int, year: int, trader_id: str = Depends(verify_trader_access)):
    """Clear GSTR-2B records for a specific month (to re-upload)."""
    try:
        db = get_supabase()
        db.table("gstr2b_records").delete().eq(
            "trader_id", trader_id
        ).eq("month", month).eq("year", year).execute()
        return {"status": "cleared", "month": month, "year": year}
    except Exception as e:
        raise safe_http_error(logger, "Failed to clear GSTR-2B records", e)


def _parse_gst_portal_json(data: dict) -> list[dict]:
    """
    Parse the standard GST portal GSTR-2B JSON format.
    Handles b2b (regular invoices), b2ba (amendments), cdnr (credit/debit notes).
    """
    records = []

    try:
        doc_data = data.get("data", data)  # handle both wrapped and raw
        inner = doc_data.get("docdata", doc_data)

        # ── B2B: Regular supplier invoices ────────────────────────────────────
        for supplier_entry in inner.get("b2b", []):
            supplier_gstin = supplier_entry.get("ctin", "")
            for inv in supplier_entry.get("inv", []):
                rec = _extract_invoice_record(supplier_gstin, inv, "B2B")
                if rec:
                    records.append(rec)

        # ── B2BA: Amended invoices (supersede their originals) ────────────────
        for supplier_entry in inner.get("b2ba", []):
            supplier_gstin = supplier_entry.get("ctin", "")
            for inv in supplier_entry.get("inv", []):
                rec = _extract_invoice_record(supplier_gstin, inv, "B2BA")
                if rec:
                    records.append(rec)

        # ── CDNR: Credit/Debit notes from suppliers ───────────────────────────
        for supplier_entry in inner.get("cdnr", []):
            supplier_gstin = supplier_entry.get("ctin", "")
            for note in supplier_entry.get("nt", []):
                rec = _extract_invoice_record(supplier_gstin, note, "CDNR")
                if rec:
                    # Credit notes have negative taxable value convention
                    rec["itc_eligible"] = False  # CN reduces ITC, never adds it
                    records.append(rec)

    except Exception as e:
        logger.error(f"GSTR-2B JSON parse error: {e}")

    return records


def _extract_invoice_record(supplier_gstin: str, inv: dict, record_type: str) -> Optional[dict]:
    """Extract a normalised record dict from a GST portal invoice/note object."""
    inv_number = inv.get("inum", "") or inv.get("ntnum", "")  # nt = note number for CDNR
    inv_date = _normalize_date(inv.get("dt", ""))
    taxable_value = float(inv.get("val", 0))

    igst = cgst = sgst = 0.0
    for item in inv.get("itms", []):
        det = item.get("itm_det", {})
        igst += float(det.get("iamt", 0))
        cgst += float(det.get("camt", 0))
        sgst += float(det.get("samt", 0))
        if not taxable_value:
            taxable_value += float(det.get("txval", 0))

    if not (supplier_gstin and inv_number and inv_date):
        return None

    return {
        "supplier_gstin": supplier_gstin.upper().strip(),
        "invoice_number": inv_number.strip(),
        "invoice_date": inv_date,
        "taxable_value": taxable_value,
        "igst": igst,
        "cgst": cgst,
        "sgst": sgst,
        "itc_eligible": True,
        "record_type": record_type,
    }


def _normalize_date(date_str: str) -> Optional[str]:
    """Convert DD-MM-YYYY (GST portal format) to YYYY-MM-DD (ISO)."""
    if not date_str:
        return None
    try:
        if "-" in date_str and len(date_str) == 10:
            parts = date_str.split("-")
            if len(parts[0]) == 2:  # DD-MM-YYYY
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
            return date_str  # Already YYYY-MM-DD
        return None
    except Exception:
        return None


def _adjacent_periods(month: int, year: int) -> list[tuple[int, int]]:
    """
    Return (month, year) for M-1, M and M+1, rolling the year over in January
    and December. Suppliers file late — a January invoice routinely turns up in
    February's or March's GSTR-2B — so reconciling period M against period M's
    2B alone can never match those.
    """
    previous = (12, year - 1) if month == 1 else (month - 1, year)
    following = (1, year + 1) if month == 12 else (month + 1, year)
    return [previous, (month, year), following]


@router.post("/reconcile/{trader_id}")
async def trigger_reconciliation(trader_id: str = Depends(verify_trader_access), month: int = None, year: int = None):
    """
    Re-run GSTR-2B reconciliation against all unmatched invoices for a trader.
    Useful after uploading new GSTR-2B data.
    """
    try:
        from app.domain.reconciler import GSTR2BReconciler, GSTR2BRecord
        from app.services.supabase_client import get_gstr2b_records, get_invoices_for_trader

        now = date.today()
        month = month or now.month
        year = year or now.year

        db = get_supabase()
        reconciler = GSTR2BReconciler()

        # Get trader preferences gracefully (in case migration not run yet)
        auto_warn_vendors = False
        try:
            trader_resp = db.table("traders").select("auto_warn_vendors").eq("id", trader_id).execute()
            if trader_resp.data:
                auto_warn_vendors = trader_resp.data[0].get("auto_warn_vendors", False)
        except Exception as e:
            logger.warning(f"Could not fetch auto_warn_vendors (migration missing?): {e}")

        # Get GSTR-2B records for this period AND its neighbours. The matcher's
        # 15/30-day date windows can only narrow the candidate list it is given,
        # so late-filed rows have to be fetched here or they can never match.
        # get_gstr2b_records() filters on one period, hence one call per period.
        gstr2b_records = []
        seen_record_ids: set[str] = set()
        for period_month, period_year in _adjacent_periods(month, year):
            for rec in await get_gstr2b_records(trader_id, period_month, period_year):
                record_id = str(rec.get("id"))
                if record_id in seen_record_ids:
                    continue  # same row can't be fed to the matcher twice
                seen_record_ids.add(record_id)
                gstr2b_records.append(rec)

        if not gstr2b_records:
            return {"status": "no_2b_data", "message": "No GSTR-2B records found for this period or the months either side of it. Please upload first.", "matched": 0}

        # Get all invoices for this month — re-run reconciles everything
        invoices = await get_invoices_for_trader(trader_id, month, year)
        unmatched = invoices  # re-run checks all invoices regardless of prior status

        from datetime import datetime
        
        # Convert dicts to GSTR2BRecord objects
        records_obj = []
        for r in gstr2b_records:
            date_obj = None
            if r.get("invoice_date"):
                try:
                    date_obj = datetime.strptime(r["invoice_date"], "%Y-%m-%d").date()
                except ValueError:
                    pass

            record = GSTR2BRecord(
                record_id=str(r.get("id")),
                supplier_gstin=r.get("supplier_gstin", ""),
                invoice_number=r.get("invoice_number", ""),
                invoice_date=date_obj,
                taxable_value=float(r.get("taxable_value") or 0),
                igst=float(r.get("igst") or 0),
                cgst=float(r.get("cgst") or 0),
                sgst=float(r.get("sgst") or 0),
                record_type=r.get("record_type", "B2B"),
            )
            # find_missed_itc() reads matched_invoice_id as "already claimed",
            # and the constructor defaults it to None. Carry the stored value
            # across or a row an adjacent month's run already matched would be
            # reported back to the CA as unclaimed ITC.
            record.matched_invoice_id = r.get("matched_invoice_id")
            records_obj.append(record)

        matched_count = 0
        failed_invoices = []
        # Match-exclusivity: each 2B record consumed once. Pre-consume rows
        # already matched to an invoice outside this run — now that adjacent
        # periods are fetched, reconciling January would otherwise re-point a
        # 2B row February's run had legitimately matched, leaving two invoices
        # claiming it. Rows matched to invoices inside this run stay free, since
        # a re-run recomputes those from scratch.
        invoice_ids_in_run = {str(i["id"]) for i in unmatched}
        consumed_ids: set[str] = {
            r.record_id for r in records_obj
            if r.matched_invoice_id and str(r.matched_invoice_id) not in invoice_ids_in_run
        }
        from app.api.communications import email_vendor_warning, whatsapp_vendor_warning
        from app.services.supabase_client import mark_gstr2b_record_matched

        for inv in unmatched:
            match_result = reconciler.match_invoice(
                supplier_gstin=(inv.get("gstin_supplier") or "").upper().strip(),
                invoice_number=inv.get("invoice_number", ""),
                invoice_date_str=inv.get("invoice_date", ""),
                total_amount=inv.get("total_amount", 0),
                gstr2b_records=records_obj,
                consumed_ids=consumed_ids,
            )

            # Update the invoice with match result
            is_matched = match_result.status in ("MATCHED", "PROBABLE_MATCH", "POSSIBLE_MATCH")
            db.table("invoices").update({
                "gstr2b_match_status": match_result.status,
                "gstr2b_match_confidence": match_result.confidence,
            }).eq("id", inv["id"]).execute()

            if is_matched:
                matched_count += 1
                if match_result.matched_record_id:
                    await mark_gstr2b_record_matched(match_result.matched_record_id, inv["id"])
            else:
                failed_invoices.append({
                    "supplier_name": inv.get("supplier_name") or "Unknown Vendor",
                    "invoice_number": inv.get("invoice_number", "N/A"),
                })
                if auto_warn_vendors:
                    inv_id = inv["id"]
                    try:
                        if inv.get("supplier_email"):
                            await email_vendor_warning(inv_id)
                        elif inv.get("supplier_phone"):
                            await whatsapp_vendor_warning(inv_id)
                    except Exception as warn_err:
                        logger.error(f"Auto-warning failed for {inv_id}: {warn_err}")

        # Apply credit note netting. Count what actually landed, not what was
        # attempted: credit_note_applied/credit_note_reason only exist if
        # migrations/add_invoice_credit_note_and_notify.sql has been run, and
        # reporting attempts told the CA that N notes were netted when the
        # update had raised and been swallowed below.
        cn_updates = reconciler.net_credit_notes(records_obj, unmatched)
        cn_applied = 0
        cn_failed = 0
        for upd in cn_updates:
            try:
                existing = db.table("invoices").select("itc_amount_eligible").eq("id", upd["invoice_id"]).execute()
                if not existing.data:
                    cn_failed += 1
                    logger.warning(f"Credit note target invoice {upd['invoice_id']} not found")
                    continue
                current_itc = float(existing.data[0].get("itc_amount_eligible") or 0)
                new_itc = max(0.0, current_itc + upd["itc_delta"])
                db.table("invoices").update({
                    "itc_amount_eligible": new_itc,
                    "credit_note_applied": True,
                    "credit_note_reason": upd["reason"],
                }).eq("id", upd["invoice_id"]).execute()
                cn_applied += 1
            except Exception as cn_err:
                cn_failed += 1
                logger.warning(f"Credit note update failed: {cn_err}")

        # B2B/B2BA rows nobody claimed: the supplier filed it, the trader paid
        # the tax, and no invoice was ever matched against it. Scoped to the
        # requested period — the neighbouring months were pulled in only to let
        # late filings match, and their orphans belong to their own runs.
        period_record_ids = {
            str(r.get("id")) for r in gstr2b_records
            if r.get("month") == month and r.get("year") == year
        }
        missed = [
            r for r in reconciler.find_missed_itc(gstr2b_records=records_obj, consumed_ids=consumed_ids)
            if r.record_id in period_record_ids
        ]
        missed_itc_value = sum(r.total_tax for r in missed)

        return {
            "status": "complete",
            "period": f"{month}/{year}",
            "invoices_checked": len(unmatched),
            "newly_matched": matched_count,
            "gstr2b_records": len(gstr2b_records),
            "credit_notes_applied": cn_applied,
            "credit_notes_failed": cn_failed,
            "missed_itc_records": len(missed),
            "missed_itc_value": round(missed_itc_value, 2),
            "failed_invoices": failed_invoices,
        }

    except Exception as e:
        raise safe_http_error(logger, "GSTR-2B reconciliation run failed", e)
