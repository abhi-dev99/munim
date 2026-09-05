"""
Munim.ai — Reports API
Endpoints for triggering and downloading Munim Report PDFs.
"""

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.post("/generate/{trader_id}")
async def generate_report(
    trader_id: str,
    background_tasks: BackgroundTasks,
    month: Optional[int] = None,
    year: Optional[int] = None,
    send_whatsapp: bool = False,
):
    """
    Generate a Munim Report PDF for a trader.
    Returns the PDF URL immediately (runs synchronously).
    Optionally sends it via WhatsApp if send_whatsapp=true.
    """
    from app.agents.report_agent import generate_munim_report, send_report_to_trader

    now = date.today()
    month = month or now.month
    year = year or now.year

    if not 1 <= month <= 12:
        raise HTTPException(status_code=400, detail="month must be 1–12")
    if year < 2020 or year > now.year + 1:
        raise HTTPException(status_code=400, detail="Invalid year")

    try:
        pdf_url = await generate_munim_report(trader_id, month, year)
        if not pdf_url:
            raise HTTPException(status_code=500, detail="PDF generation failed")

        if send_whatsapp:
            background_tasks.add_task(send_report_to_trader, trader_id, pdf_url)

        return {
            "status": "generated",
            "trader_id": trader_id,
            "month": month,
            "year": year,
            "pdf_url": pdf_url,
            "whatsapp_queued": send_whatsapp,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report generation failed for {trader_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list/{trader_id}")
async def list_reports(trader_id: str):
    """List all generated reports for a trader."""
    db = get_supabase()
    try:
        resp = db.table("munim_reports").select(
            "id, month, year, pdf_url, total_invoices_processed, total_itc_confirmed, total_issues_count"
        ).eq("trader_id", trader_id).order("year", desc=True).order("month", desc=True).execute()

        return {"reports": resp.data or []}
    except Exception as e:
        logger.error(f"Failed to list reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))
