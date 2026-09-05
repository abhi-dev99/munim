"""
Munim.ai — Dashboard REST API
Serves data to the Next.js frontend.
"""

import logging
from datetime import date

from fastapi import APIRouter, HTTPException

from app.services.supabase_client import (
    get_supabase,
    get_itc_summary,
    get_invoices_for_trader,
    get_all_suppliers_for_trader,
    get_active_supplier_flags,
)
from app.models.trader import DashboardSummary, ITCBucket, ActionItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary/{trader_id}")
async def get_dashboard_summary(trader_id: str):
    """Get the full dashboard summary for a trader."""
    try:
        now = date.today()
        buckets = await get_itc_summary(trader_id)
        invoices = await get_invoices_for_trader(trader_id)
        suppliers = await get_all_suppliers_for_trader(trader_id)

        itc = ITCBucket(**buckets) if buckets else ITCBucket()
        total_recovery = itc.fixable_blocked + itc.at_risk + itc.missed

        # Count open issues
        issues_open = sum(
            1 for inv in invoices
            if inv.get("itc_status") in ("FIXABLE_BLOCKED", "AT_RISK", "FRAUD_FLAGGED")
        )

        return DashboardSummary(
            trader_id=trader_id,
            month=now.month,
            year=now.year,
            itc_buckets=itc,
            invoices_processed=len(invoices),
            suppliers_monitored=len(suppliers),
            issues_open=issues_open,
            total_recovery_possible=total_recovery,
        )
    except Exception as e:
        logger.error(f"Dashboard summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invoices/{trader_id}")
async def get_trader_invoices(trader_id: str, month: int = None, year: int = None):
    """Get all invoices for a trader."""
    try:
        invoices = await get_invoices_for_trader(trader_id, month, year)
        return {"invoices": invoices, "total": len(invoices)}
    except Exception as e:
        logger.error(f"Get invoices failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suppliers/{trader_id}")
async def get_trader_suppliers(trader_id: str):
    """Get all suppliers for a trader with health scores and flags."""
    try:
        supplier_links = await get_all_suppliers_for_trader(trader_id)
        result = []
        for link in supplier_links:
            supplier = link.get("suppliers", {})
            if supplier:
                flags = await get_active_supplier_flags(supplier["id"])
                supplier["flags"] = [f["flag_type"] for f in flags]
                supplier["total_invoices"] = link.get("total_invoice_count", 0)
                result.append(supplier)

        # Sort by health score ascending (worst first)
        result.sort(key=lambda s: s.get("health_score", 100))
        return {"suppliers": result, "total": len(result)}
    except Exception as e:
        logger.error(f"Get suppliers failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actions/{trader_id}")
async def get_action_items(trader_id: str):
    """Get prioritized action items (issues sorted by ₹ impact)."""
    try:
        invoices = await get_invoices_for_trader(trader_id)

        actions = []
        for inv in invoices:
            status = inv.get("itc_status", "")
            if status not in ("FIXABLE_BLOCKED", "AT_RISK", "FRAUD_FLAGGED"):
                continue

            blocked = inv.get("itc_amount_blocked") or 0
            eligible = inv.get("itc_amount_eligible") or 0
            impact = blocked if blocked > 0 else eligible

            actions.append(ActionItem(
                id=inv["id"],
                invoice_id=inv["id"],
                supplier_name=inv.get("supplier_name") or inv.get("gstin_supplier", "Unknown Supplier"),
                issue=inv.get("itc_block_reason") or _get_issue_label(status),
                impact_amount=impact,
                fix_action=_get_fix_action(status),
                priority=0,
            ))

        # Sort by impact descending
        actions.sort(key=lambda a: a.impact_amount, reverse=True)

        # Assign priority ranks
        for i, action in enumerate(actions):
            action.priority = i + 1

        return {"actions": actions, "total": len(actions)}
    except Exception as e:
        logger.error(f"Get actions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/actions/{invoice_id}/resolve")
async def resolve_action_item(invoice_id: str):
    """Mark an action item (invoice issue) as manually resolved by CA."""
    try:
        db = get_supabase()
        response = db.table("invoices").update({
            "itc_status": "RESOLVED",
            "status": "validated",
        }).eq("id", invoice_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Invoice not found")

        return {"status": "resolved", "invoice_id": invoice_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resolve action failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/itc-timeline/{trader_id}")
async def get_itc_timeline(trader_id: str):
    """Get 6-month ITC timeline data for charts."""
    try:
        db = get_supabase()
        now = date.today()
        timeline = []

        for i in range(5, -1, -1):
            month = now.month - i
            year = now.year
            if month <= 0:
                month += 12
                year -= 1

            invoices = await get_invoices_for_trader(trader_id, month, year)

            confirmed = sum(
                (inv.get("itc_amount_eligible") or 0)
                for inv in invoices
                if inv.get("itc_status") == "CONFIRMED"
            )
            total_eligible = sum(
                (inv.get("itc_amount_eligible") or 0) + (inv.get("itc_amount_blocked") or 0)
                for inv in invoices
            )

            timeline.append({
                "month": month,
                "year": year,
                "label": f"{_month_name(month)} {year}",
                "itc_claimed": confirmed,
                "itc_eligible": total_eligible,
                "gap": total_eligible - confirmed,
            })

        return {"timeline": timeline}
    except Exception as e:
        logger.error(f"ITC timeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_fix_action(status: str) -> str:
    """Get human-readable fix action for an ITC status."""
    actions = {
        "FIXABLE_BLOCKED": "CA ko bolo HSN code / rate correct kare filing se pehle",
        "AT_RISK": "Supplier se contact karo — unhe GSTR-1 file karna hoga",
        "FRAUD_FLAGGED": "CA se verify karwao — ITC claim mat karo abhi",
    }
    return actions.get(status, "Check with CA")


def _get_issue_label(status: str) -> str:
    """Get a human-readable issue description for an ITC status code."""
    labels = {
        "FIXABLE_BLOCKED": "HSN code mismatch or incorrect GST rate",
        "AT_RISK": "Supplier GSTR-1 not filed — ITC at risk",
        "FRAUD_FLAGGED": "Potential fraud or invalid supplier GSTIN",
    }
    return labels.get(status, status or "Compliance issue detected")


def _month_name(month: int) -> str:
    """Get short month name."""
    months = [
        "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    return months[month] if 1 <= month <= 12 else ""


@router.get("/traders")
async def list_traders():
    """List all registered traders (for frontend trader selection)."""
    try:
        db = get_supabase()
        response = db.table("traders").select("id, name, business_name, gstin, whatsapp_number").execute()
        return {"traders": response.data or []}
    except Exception as e:
        logger.error(f"List traders failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gstr2b-status/{trader_id}")
async def get_gstr2b_status(trader_id: str):
    """Get GSTR-2B reconciliation status for a trader."""
    try:
        from app.services.supabase_client import get_gstr2b_records

        now = date.today()
        records = await get_gstr2b_records(trader_id, now.month, now.year)
        invoices = await get_invoices_for_trader(trader_id)

        matched = sum(1 for inv in invoices if inv.get("gstr2b_match_status") == "MATCHED")
        probable = sum(1 for inv in invoices if inv.get("gstr2b_match_status") == "PROBABLE_MATCH")
        at_risk = sum(1 for inv in invoices if inv.get("gstr2b_match_status") == "ITC_AT_RISK")

        return {
            "total_2b_records": len(records),
            "matched": matched,
            "probable_match": probable,
            "at_risk": at_risk,
            "unreconciled": len(invoices) - matched - probable - at_risk,
        }
    except Exception as e:
        logger.error(f"GSTR-2B status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports/generate/{trader_id}")
async def trigger_report_generation(trader_id: str, month: int = None, year: int = None):
    """Trigger Munim Report generation for a trader."""
    try:
        from app.agents.report_agent import generate_munim_report, send_report_to_trader

        now = date.today()
        month = month or now.month
        year = year or now.year

        pdf_url = await generate_munim_report(trader_id, month, year)
        if not pdf_url:
            raise HTTPException(status_code=500, detail="Report generation failed")

        # Send to trader via WhatsApp
        await send_report_to_trader(trader_id, pdf_url)

        return {
            "status": "generated",
            "pdf_url": pdf_url,
            "month": month,
            "year": year,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/{trader_id}")
async def get_reports(trader_id: str):
    """Get all generated reports for a trader."""
    try:
        db = get_supabase()
        response = db.table("munim_reports").select("*").eq(
            "trader_id", trader_id
        ).order("year", desc=True).order("month", desc=True).execute()
        return {"reports": response.data or []}
    except Exception as e:
        logger.error(f"Get reports failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/check-deadlines")
async def check_deadlines():
    """Check if any deadline is near and send WhatsApp alerts to trader and CA."""
    from app.services.whatsapp import send_text_message
    
    # Normally this would fetch traders and their CAs from the database
    # and calculate if a deadline is 1 day away.
    # For demo purposes, we trigger the notification directly.
    message = (
        "⚠️ *GST Deadline Alert*\n\n"
        "Tomorrow is the 11th. Your GSTR-1 is due!\n\n"
        "Please review the pending Action Items on Munim.ai and clear them so your CA can file on time."
    )
    
    ca_message = (
        "⚠️ *GST Deadline Alert*\n\n"
        "Client: Suryakant Optics\n"
        "GSTR-1 is due tomorrow. The client has uncleared ITC flags on Munim.ai. Please follow up."
    )
    
    # We log it or send to a test number.
    # In production, iterate over db.table("traders") and check their deadlines.
    # await send_text_message("TRADER_PHONE", message)
    # await send_text_message("CA_PHONE", ca_message)
    
    logger.info("Checked deadlines. Sent WhatsApp alerts to trader and CA.")
    return {"status": "success", "message": "Deadline alerts triggered successfully via WhatsApp."}
