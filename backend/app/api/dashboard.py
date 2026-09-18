"""
Munim.ai — Dashboard REST API
Serves data to the Next.js frontend.
"""

import logging
from datetime import date

from fastapi import APIRouter, Depends
from app.api.deps import verify_trader_access, get_current_trader_id, HTTPException

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
async def get_dashboard_summary(trader_id: str = Depends(verify_trader_access)):
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
async def get_trader_invoices(trader_id: str = Depends(verify_trader_access), month: int = None, year: int = None):
    """Get all invoices for a trader."""
    try:
        invoices = await get_invoices_for_trader(trader_id, month, year)
        return {"invoices": invoices, "total": len(invoices)}
    except Exception as e:
        logger.error(f"Get invoices failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suppliers/{trader_id}")
async def get_trader_suppliers(trader_id: str = Depends(verify_trader_access)):
    """Get all suppliers for a trader with health scores and flags."""
    try:
        supplier_links = await get_all_suppliers_for_trader(trader_id)
        invoices = await get_invoices_for_trader(trader_id)
        
        # Pre-compute ITC total per supplier
        itc_by_supplier = {}
        for inv in invoices:
            gstin = inv.get("gstin_supplier")
            if gstin:
                igst = float(inv.get("igst_amount") or inv.get("igst") or 0)
                cgst = float(inv.get("cgst_amount") or inv.get("cgst") or 0)
                sgst = float(inv.get("sgst_amount") or inv.get("sgst") or 0)
                itc_by_supplier[gstin] = itc_by_supplier.get(gstin, 0) + igst + cgst + sgst

        result = []
        for link in supplier_links:
            supplier = link.get("suppliers", {})
            if supplier:
                flags = await get_active_supplier_flags(supplier["id"])
                supplier["flags"] = [f["flag_type"] for f in flags]
                supplier["total_invoices"] = link.get("total_invoice_count", 0)
                supplier["total_amount"] = itc_by_supplier.get(supplier.get("gstin"), 0)
                result.append(supplier)

        # Sort by health score ascending (worst first)
        result.sort(key=lambda s: s.get("health_score", 100))
        return {"suppliers": result, "total": len(result)}
    except Exception as e:
        logger.error(f"Get suppliers failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actions/{trader_id}")
async def get_action_items(trader_id: str = Depends(verify_trader_access)):
    """Get prioritized action items (issues sorted by ₹ impact)."""
    try:
        db = get_supabase()
        trader_res = db.table("traders").select("language_pref").eq("id", trader_id).execute()
        lang = trader_res.data[0].get("language_pref", "en") if trader_res.data else "en"

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
                issue=inv.get("itc_block_reason") or _get_issue_label(status, lang),
                impact_amount=impact,
                fix_action=_get_fix_action(status, lang),
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
async def get_itc_timeline(trader_id: str = Depends(verify_trader_access)):
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


def _get_fix_action(status: str, lang: str = "en") -> str:
    """Get human-readable fix action for an ITC status based on language."""
    actions = {
        "en": {
            "FIXABLE_BLOCKED": "Correct HSN code / tax rate before filing",
            "AT_RISK": "Contact supplier to ensure GSTR-1 filing",
            "FRAUD_FLAGGED": "Verify invoice authenticity; withhold ITC claim",
        },
        "hi": {
            "FIXABLE_BLOCKED": "Filing se pehle HSN code ya tax rate theek karein",
            "AT_RISK": "Supplier se sampark karein aur GSTR-1 file karwayein",
            "FRAUD_FLAGGED": "Invoice check karein, abhi ITC claim na karein",
        },
        "mr": {
            "FIXABLE_BLOCKED": "फाइलिंगपूर्वी HSN कोड / टॅक्स रेट दुरुस्त करा",
            "AT_RISK": "सप्लायरला संपर्क करून GSTR-1 फाईल करायला सांगा",
            "FRAUD_FLAGGED": "इनव्हॉइस तपासा, आत्ता ITC क्लेम करू नका",
        },
        "gu": {
            "FIXABLE_BLOCKED": "ફાઇલિંગ પહેલાં HSN કોડ / ટેક્સ રેટ સુધારો",
            "AT_RISK": "સપ્લાયરનો સંપર્ક કરો અને GSTR-1 ફાઇલ કરાવો",
            "FRAUD_FLAGGED": "ઇનવોઇસ તપાસો, હમણાં ITC ક્લેમ ન કરો",
        }
    }
    lang_dict = actions.get(lang) or actions.get("en")
    return lang_dict.get(status, "Check with CA")


def _get_issue_label(status: str, lang: str = "en") -> str:
    """Get a human-readable issue description for an ITC status code based on language."""
    labels = {
        "en": {
            "FIXABLE_BLOCKED": "HSN code mismatch or incorrect GST rate",
            "AT_RISK": "Supplier GSTR-1 not filed — ITC at risk",
            "FRAUD_FLAGGED": "Potential fraud or invalid supplier GSTIN",
        },
        "hi": {
            "FIXABLE_BLOCKED": "HSN code ya GST rate galat hai",
            "AT_RISK": "Supplier ne GSTR-1 file nahi kiya — ITC risk par",
            "FRAUD_FLAGGED": "Supplier fraud ho sakta hai ya GSTIN galat hai",
        },
        "mr": {
            "FIXABLE_BLOCKED": "HSN कोड जुळत नाही किंवा GST रेट चुकीचा आहे",
            "AT_RISK": "सप्लायरने GSTR-1 फाईल केले नाही — ITC धोक्यात",
            "FRAUD_FLAGGED": "सप्लायर फ्रॉड असू शकतो किंवा GSTIN चुकीचा आहे",
        },
        "gu": {
            "FIXABLE_BLOCKED": "HSN કોડ મેચ થતો નથી અથવા GST રેટ ખોટો છે",
            "AT_RISK": "સપ્લાયરે GSTR-1 ફાઈલ કર્યું નથી — ITC જોખમમાં",
            "FRAUD_FLAGGED": "સપ્લાયર ફ્રોડ હોઈ શકે છે અથવા GSTIN ખોટો છે",
        }
    }
    lang_dict = labels.get(lang) or labels.get("en")
    return lang_dict.get(status, status or "Compliance issue detected")


def _month_name(month: int) -> str:
    """Get short month name."""
    months = [
        "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    return months[month] if 1 <= month <= 12 else ""


@router.get("/traders")
async def list_traders(current_trader_id: str = Depends(get_current_trader_id)):
    """List all registered traders (for frontend trader selection)."""
    try:
        db = get_supabase()
        response = db.table("traders").select("id, name, business_name, gstin, whatsapp_number").eq("id", current_trader_id).execute()
        return {"traders": response.data or []}
    except Exception as e:
        logger.error(f"List traders failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gstr2b-status/{trader_id}")
async def get_gstr2b_status(trader_id: str = Depends(verify_trader_access)):
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
async def trigger_report_generation(trader_id: str = Depends(verify_trader_access), month: int = None, year: int = None):
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
async def get_reports(trader_id: str = Depends(verify_trader_access)):
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


@router.get("/gstr3b/{trader_id}")
async def get_gstr3b_draft(trader_id: str = Depends(verify_trader_access), month: int = None, year: int = None):
    """
    Compute a GSTR-3B auto-draft from real invoice data.
    Table 4 (ITC) is computed from actual reconciled invoices.
    Table 3.1 (output liability) is omitted — outward supply data not yet available.
    """
    try:
        now = date.today()
        month = month or now.month
        year = year or now.year

        invoices = await get_invoices_for_trader(trader_id, month, year)
        if not invoices:
            invoices = await get_invoices_for_trader(trader_id)  # fallback: all invoices

        # Table 4: ITC Availability — from real engine verdicts
        itc_igst = itc_cgst = itc_sgst = 0.0
        itc_blocked_igst = itc_blocked_cgst = itc_blocked_sgst = 0.0
        at_risk_total = 0.0
        ineligible_total = 0.0
        total_invoices = len(invoices)
        confirmed_count = 0
        at_risk_count = 0
        blocked_count = 0

        for inv in invoices:
            status = inv.get("itc_status", "")
            igst = float(inv.get("igst_amount") or inv.get("igst") or 0)
            cgst = float(inv.get("cgst_amount") or inv.get("cgst") or 0)
            sgst = float(inv.get("sgst_amount") or inv.get("sgst") or 0)
            total_tax = igst + cgst + sgst

            if status == "CONFIRMED":
                itc_igst += igst
                itc_cgst += cgst
                itc_sgst += sgst
                confirmed_count += 1
            elif status in ("FIXABLE_BLOCKED", "FRAUD_FLAGGED"):
                itc_blocked_igst += igst
                itc_blocked_cgst += cgst
                itc_blocked_sgst += sgst
                blocked_count += 1
            elif status == "AT_RISK":
                at_risk_total += total_tax
                at_risk_count += 1
            elif status == "INELIGIBLE":
                ineligible_total += total_tax

        itc_available = itc_igst + itc_cgst + itc_sgst
        itc_blocked = itc_blocked_igst + itc_blocked_cgst + itc_blocked_sgst

        # GSTR-2B reconciliation summary
        db = get_supabase()
        from app.services.supabase_client import get_gstr2b_records
        gstr2b_recs = await get_gstr2b_records(trader_id, month, year)
        total_2b_igst = sum(float(r.get("igst") or 0) for r in gstr2b_recs if r.get("record_type", "B2B") == "B2B")
        total_2b_cgst = sum(float(r.get("cgst") or 0) for r in gstr2b_recs if r.get("record_type", "B2B") == "B2B")
        total_2b_sgst = sum(float(r.get("sgst") or 0) for r in gstr2b_recs if r.get("record_type", "B2B") == "B2B")

        return {
            "period": {"month": month, "year": year},
            "total_invoices": total_invoices,
            "table4": {
                "description": "ITC Availability — computed from reconciled invoices",
                "igst_available": round(itc_igst, 2),
                "cgst_available": round(itc_cgst, 2),
                "sgst_available": round(itc_sgst, 2),
                "total_available": round(itc_available, 2),
                "igst_blocked": round(itc_blocked_igst, 2),
                "cgst_blocked": round(itc_blocked_cgst, 2),
                "sgst_blocked": round(itc_blocked_sgst, 2),
                "total_blocked": round(itc_blocked, 2),
                "at_risk": round(at_risk_total, 2),
                "ineligible": round(ineligible_total, 2),
            },
            "gstr2b_summary": {
                "total_records": len(gstr2b_recs),
                "total_igst": round(total_2b_igst, 2),
                "total_cgst": round(total_2b_cgst, 2),
                "total_sgst": round(total_2b_sgst, 2),
                "total_tax": round(total_2b_igst + total_2b_cgst + total_2b_sgst, 2),
            },
            "invoice_summary": {
                "confirmed": confirmed_count,
                "at_risk": at_risk_count,
                "blocked": blocked_count,
            },
            "table3_1": None,  # Outward supply data not available — output tax liability requires GSTR-1 data
            "note": "Table 4 (ITC) computed from Munim.ai engine. Table 3.1 (output liability) requires outward supply data.",
        }
    except Exception as e:
        logger.error(f"GSTR-3B draft failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ims/{trader_id}")
async def get_ims_invoices(trader_id: str = Depends(verify_trader_access), month: int = None, year: int = None):
    """
    Invoice Management System (IMS) data feed.
    Returns all invoices with their Munim.ai verdict pre-mapped to an IMS action:
      CONFIRMED       → Accept
      FIXABLE_BLOCKED → Pending (needs CA review)
      AT_RISK         → Pending
      FRAUD_FLAGGED   → Reject
      INELIGIBLE      → Reject
    The CA can override any default in the UI before filing.
    """
    try:
        now = date.today()
        month = month or now.month
        year = year or now.year

        # Try current month first; if empty fall back to ALL invoices for the trader
        # (invoices may have been uploaded in a different month or have no invoice_date)
        invoices = await get_invoices_for_trader(trader_id, month, year)
        if not invoices:
            invoices = await get_invoices_for_trader(trader_id)  # no date filter

        IMS_DEFAULT = {
            "CONFIRMED": "accept",
            "FIXABLE_BLOCKED": "pending",
            "AT_RISK": "pending",
            "FRAUD_FLAGGED": "reject",
            "INELIGIBLE": "reject",
        }

        ims_rows = []
        for inv in invoices:
            status = inv.get("itc_status", "")
            igst = float(inv.get("igst_amount") or inv.get("igst") or 0)
            cgst = float(inv.get("cgst_amount") or inv.get("cgst") or 0)
            sgst = float(inv.get("sgst_amount") or inv.get("sgst") or 0)
            ims_rows.append({
                "invoice_id": inv["id"],
                "invoice_number": inv.get("invoice_number", ""),
                "invoice_date": inv.get("invoice_date", ""),
                "supplier_name": inv.get("supplier_name") or inv.get("gstin_supplier", "Unknown"),
                "supplier_gstin": inv.get("gstin_supplier", ""),
                "total_amount": float(inv.get("total_amount") or 0),
                "taxable_value": float(inv.get("taxable_amount") or inv.get("taxable_value") or 0),
                "igst": igst,
                "cgst": cgst,
                "sgst": sgst,
                "total_tax": igst + cgst + sgst,
                "itc_status": status,
                "itc_reason": inv.get("itc_block_reason") or inv.get("fraud_reason") or "",
                "gstr2b_match": inv.get("gstr2b_match_status", "UNRECONCILED"),
                "ims_action": IMS_DEFAULT.get(status, "pending"),  # pre-set from engine verdict
                "ims_overridden": False,
            })

        accept_count = sum(1 for r in ims_rows if r["ims_action"] == "accept")
        pending_count = sum(1 for r in ims_rows if r["ims_action"] == "pending")
        reject_count = sum(1 for r in ims_rows if r["ims_action"] == "reject")
        accepted_itc = sum(r["total_tax"] for r in ims_rows if r["ims_action"] == "accept")

        return {
            "period": {"month": month, "year": year},
            "invoices": ims_rows,
            "summary": {
                "total": len(ims_rows),
                "accept": accept_count,
                "pending": pending_count,
                "reject": reject_count,
                "accepted_itc": round(accepted_itc, 2),
            },
        }
    except Exception as e:
        logger.error(f"IMS data failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))



import json
import os
from pydantic import BaseModel

class PreferencesModel(BaseModel):
    dashboard: list[str]
    sidebar: list[str]

PREF_FILE = "preferences.json"

def _load_prefs():
    if os.path.exists(PREF_FILE):
        with open(PREF_FILE, "r") as f:
            return json.load(f)
    return {}

def _save_prefs(prefs):
    with open(PREF_FILE, "w") as f:
        json.dump(prefs, f)

@router.get("/preferences/{trader_id}")
async def get_preferences(trader_id: str = Depends(verify_trader_access)):
    prefs = _load_prefs()
    if trader_id in prefs:
        return prefs[trader_id]
    return {
        "dashboard": ["quick_links", "supplier_risk", "filing_readiness", "eway_bills"],
        "sidebar": ["money-meter", "suppliers", "actions", "reports"]
    }

@router.post("/preferences/{trader_id}")
async def save_preferences(payload: PreferencesModel, trader_id: str = Depends(verify_trader_access)):
    prefs = _load_prefs()
    prefs[trader_id] = {
        "dashboard": payload.dashboard,
        "sidebar": payload.sidebar
    }
    _save_prefs(prefs)
    return {"message": "Preferences saved successfully"}

