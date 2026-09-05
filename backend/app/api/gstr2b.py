"""
Munim.ai — GSTR-2B Upload API
Allows traders (or CAs) to upload their GSTR-2B JSON export from the GST portal.
Parses and stores records for reconciliation against processed invoices.
"""

import json
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.services.supabase_client import get_supabase

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
async def upload_gstr2b_json(payload: GSTR2BBulkUpload):
    """
    Upload GSTR-2B records parsed from GST portal JSON export.
    Use this when you have the JSON data already parsed client-side.
    """
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
    trader_id: str,
    month: int = Form(...),
    year: int = Form(...),
    file: UploadFile = File(...),
):
    """
    Upload GSTR-2B as a raw JSON file or Excel file (downloaded from GST portal).
    Handles the standard GST portal GSTR-2B formats.
    """
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
async def get_gstr2b_records(trader_id: str, month: int = None, year: int = None):
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
        logger.error(f"Get GSTR-2B records failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/records/{trader_id}")
async def clear_gstr2b_records(trader_id: str, month: int, year: int):
    """Clear GSTR-2B records for a specific month (to re-upload)."""
    try:
        db = get_supabase()
        db.table("gstr2b_records").delete().eq(
            "trader_id", trader_id
        ).eq("month", month).eq("year", year).execute()
        return {"status": "cleared", "month": month, "year": year}
    except Exception as e:
        logger.error(f"Clear GSTR-2B records failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


@router.post("/reconcile/{trader_id}")
async def trigger_reconciliation(trader_id: str, month: int = None, year: int = None):
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

        # Get all GSTR-2B records for this period
        gstr2b_records = await get_gstr2b_records(trader_id, month, year)
        if not gstr2b_records:
            return {"status": "no_2b_data", "message": "No GSTR-2B records found for this period. Please upload first.", "matched": 0}

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

            records_obj.append(
                GSTR2BRecord(
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
            )

        matched_count = 0
        failed_invoices = []
        consumed_ids: set[str] = set()  # match-exclusivity: each 2B record consumed once
        from app.api.communications import email_vendor_warning, whatsapp_vendor_warning

        for inv in unmatched:
            match_result = reconciler.match_invoice(
                supplier_gstin=inv.get("gstin_supplier", ""),
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

        # Apply credit note netting
        cn_updates = reconciler.net_credit_notes(records_obj, unmatched)
        for upd in cn_updates:
            try:
                existing = db.table("invoices").select("itc_amount_eligible").eq("id", upd["invoice_id"]).execute()
                if existing.data:
                    current_itc = float(existing.data[0].get("itc_amount_eligible") or 0)
                    new_itc = max(0.0, current_itc + upd["itc_delta"])
                    db.table("invoices").update({
                        "itc_amount_eligible": new_itc,
                        "credit_note_applied": True,
                        "credit_note_reason": upd["reason"],
                    }).eq("id", upd["invoice_id"]).execute()
            except Exception as cn_err:
                logger.warning(f"Credit note update failed: {cn_err}")

        return {
            "status": "complete",
            "period": f"{month}/{year}",
            "invoices_checked": len(unmatched),
            "newly_matched": matched_count,
            "gstr2b_records": len(gstr2b_records),
            "credit_notes_applied": len(cn_updates),
            "failed_invoices": failed_invoices,
        }

    except Exception as e:
        logger.error(f"Reconciliation trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
