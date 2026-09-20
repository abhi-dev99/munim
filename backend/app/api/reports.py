"""
Munim-AI — Reports API
Endpoints for triggering and downloading Munim Report PDFs.
"""

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from app.api.deps import verify_trader_access, get_current_trader_id, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.services import db
from app.utils.errors import safe_http_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.post("/generate/{trader_id}")
async def generate_report(
    background_tasks: BackgroundTasks,
    trader_id: str = Depends(verify_trader_access),
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
        raise safe_http_error(logger, f"Report generation failed for trader {trader_id}", e)


@router.get("/list/{trader_id}")
async def list_reports(trader_id: str = Depends(verify_trader_access)):
    """List all generated reports for a trader."""
    try:
        reports = await db.get_reports_for_trader(trader_id)
        return {"reports": reports}
    except Exception as e:
        raise safe_http_error(logger, "Failed to list generated reports", e)
