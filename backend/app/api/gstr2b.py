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
            db.table("gstr2b_records").upsert({
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
            }, on_conflict="trader_id,month,year,supplier_gstin,invoice_number").execute()
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
    Upload GSTR-2B as a raw JSON file (downloaded from GST portal).
    Handles the standard GST portal GSTR-2B JSON format.
    """
    if file.content_type not in ("application/json", "text/plain", "application/octet-stream"):
        raise HTTPException(
            status_code=400,
            detail="Only JSON files accepted. Download GSTR-2B from GST portal and upload here."
        )

    content = await file.read()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    records = _parse_gst_portal_json(data)
    if not records:
        raise HTTPException(
            status_code=400,
            detail="Could not parse GSTR-2B records from this file. "
                   "Expected GST portal GSTR-2B JSON format."
        )

    db = get_supabase()
    inserted = 0
    skipped = 0

    for rec in records:
        try:
            db.table("gstr2b_records").upsert({
                "trader_id": trader_id,
                "month": month,
                "year": year,
                **rec,
            }, on_conflict="trader_id,month,year,supplier_gstin,invoice_number").execute()
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
    The GST portal exports a nested structure under data.docdata.b2b / b2ba / cdnr etc.
    """
    records = []

    try:
        # Standard GST portal format: data > docdata > b2b (B2B invoices)
        doc_data = data.get("data", data)  # handle both wrapped and raw

        # B2B invoices (regular supplier invoices)
        b2b_entries = (
            doc_data.get("docdata", {}).get("b2b", [])
            or doc_data.get("b2b", [])
        )

        for supplier_entry in b2b_entries:
            supplier_gstin = supplier_entry.get("ctin", "")
            invoices = supplier_entry.get("inv", [])

            for inv in invoices:
                inv_number = inv.get("inum", "")
                inv_date = _normalize_date(inv.get("dt", ""))
                taxable_value = float(inv.get("val", 0))

                # Tax components
                igst = 0.0
                cgst = 0.0
                sgst = 0.0

                for item in inv.get("itms", []):
                    det = item.get("itm_det", {})
                    igst += float(det.get("iamt", 0))
                    cgst += float(det.get("camt", 0))
                    sgst += float(det.get("samt", 0))

                    # Taxable value from line items if top-level missing
                    if not taxable_value:
                        taxable_value += float(det.get("txval", 0))

                if supplier_gstin and inv_number and inv_date:
                    records.append({
                        "supplier_gstin": supplier_gstin.upper().strip(),
                        "invoice_number": inv_number.strip(),
                        "invoice_date": inv_date,
                        "taxable_value": taxable_value,
                        "igst": igst,
                        "cgst": cgst,
                        "sgst": sgst,
                        "itc_eligible": True,
                    })

    except Exception as e:
        logger.error(f"GSTR-2B JSON parse error: {e}")

    return records


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
        from app.domain.reconciler import GSTR2BReconciler
        from app.services.supabase_client import get_gstr2b_records, get_invoices_for_trader

        now = date.today()
        month = month or now.month
        year = year or now.year

        db = get_supabase()
        reconciler = GSTR2BReconciler()

        # Get all GSTR-2B records for this period
        gstr2b_records = await get_gstr2b_records(trader_id, month, year)
        if not gstr2b_records:
            return {"status": "no_2b_data", "message": "No GSTR-2B records found for this period. Please upload first.", "matched": 0}

        # Get unmatched invoices for this month
        invoices = await get_invoices_for_trader(trader_id, month, year)
        unmatched = [inv for inv in invoices if inv.get("gstr2b_match_status") in (None, "UNRECONCILED", "ITC_AT_RISK")]

        matched_count = 0
        for inv in unmatched:
            match_result = reconciler.reconcile(
                invoice_number=inv.get("invoice_number", ""),
                supplier_gstin=inv.get("gstin_supplier", ""),
                invoice_amount=inv.get("total_amount", 0),
                invoice_date=inv.get("invoice_date", ""),
                gstr2b_records=gstr2b_records,
            )

            # Update the invoice with match result
            new_status = "MATCHED" if match_result.is_matched else "UNRECONCILED"
            db.table("invoices").update({
                "gstr2b_match_status": new_status,
                "gstr2b_match_type": match_result.match_type if match_result.is_matched else None,
                "gstr2b_match_score": match_result.score,
            }).eq("id", inv["id"]).execute()

            if match_result.is_matched:
                matched_count += 1

        return {
            "status": "complete",
            "period": f"{month}/{year}",
            "invoices_checked": len(unmatched),
            "newly_matched": matched_count,
            "gstr2b_records": len(gstr2b_records),
        }

    except Exception as e:
        logger.error(f"Reconciliation trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
