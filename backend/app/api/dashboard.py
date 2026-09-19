"""
Munim.ai — Dashboard REST API
Serves data to the Next.js frontend.
"""

import logging
import secrets
import string
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel
from app.api.deps import verify_trader_access, get_current_trader_id, HTTPException
from app.config import get_settings

from app.services.supabase_client import (
    get_supabase,
    get_itc_summary,
    get_invoices_for_trader,
    get_all_suppliers_for_trader,
    get_active_supplier_flags,
    update_trader,
)
from app.models.trader import DashboardSummary, ITCBucket, ActionItem
from app.utils.errors import safe_http_error

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
        raise safe_http_error(logger, "Failed to compute dashboard summary", e)


@router.get("/invoices/{trader_id}")
async def get_trader_invoices(trader_id: str = Depends(verify_trader_access), month: int = None, year: int = None):
    """Get all invoices for a trader."""
    try:
        invoices = await get_invoices_for_trader(trader_id, month, year)
        return {"invoices": invoices, "total": len(invoices)}
    except Exception as e:
        raise safe_http_error(logger, "Failed to fetch trader invoices", e)


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
        raise safe_http_error(logger, "Failed to fetch trader suppliers", e)


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

            # Timing is the product's first differentiator: a CA reconciles at
            # month end, by which point a supplier who hasn't filed can no
            # longer be chased in time. Surfacing the remaining window is what
            # makes "we check on arrival" mean something on screen rather than
            # only in the pitch. Only AT_RISK gets it — that is the one status
            # whose fix depends on somebody else filing.
            deadline = _supplier_filing_deadline(inv.get("invoice_date")) if status == "AT_RISK" else None

            actions.append(ActionItem(
                id=inv["id"],
                invoice_id=inv["id"],
                supplier_name=inv.get("supplier_name") or inv.get("gstin_supplier", "Unknown Supplier"),
                issue=inv.get("itc_block_reason") or _get_issue_label(status, lang),
                impact_amount=impact,
                fix_action=_get_fix_action(status, lang),
                deadline=deadline.isoformat() if deadline else None,
                days_to_fix=(deadline - date.today()).days if deadline else None,
                priority=0,
            ))

        # Sort by impact descending
        actions.sort(key=lambda a: a.impact_amount, reverse=True)

        # Assign priority ranks
        for i, action in enumerate(actions):
            action.priority = i + 1

        return {"actions": actions, "total": len(actions)}
    except Exception as e:
        raise safe_http_error(logger, "Failed to compute action items", e)


@router.patch("/actions/{invoice_id}/resolve")
async def resolve_action_item(invoice_id: str, current_trader_id: str = Depends(get_current_trader_id)):
    """Mark an action item (invoice issue) as manually resolved by CA."""
    try:
        db = get_supabase()

        # The path param here is an invoice, not a trader, so this endpoint
        # can't bind `Depends(verify_trader_access)` the way the rest of this
        # file does. Look the owning trader up first and then call the same
        # check by hand, so the CA-vs-client access rules stay defined in one
        # place (deps.py) rather than being re-implemented here.
        owner_res = db.table("invoices").select("trader_id").eq("id", invoice_id).execute()
        if not owner_res.data:
            raise HTTPException(status_code=404, detail="Invoice not found")

        owner_trader_id = owner_res.data[0].get("trader_id")
        if not owner_trader_id:
            # An invoice with no owner can't be authorised against anybody,
            # so refuse rather than fall through to an unscoped update.
            logger.warning(f"Invoice {invoice_id} has no trader_id — refusing resolve")
            raise HTTPException(status_code=403, detail="Not authorized to modify this invoice")

        await verify_trader_access(owner_trader_id, current_trader_id)

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
        raise safe_http_error(logger, f"Failed to resolve action item for invoice {invoice_id}", e)


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
        raise safe_http_error(logger, "Failed to build ITC timeline", e)


def _supplier_filing_deadline(invoice_date_str: Optional[str]) -> Optional[date]:
    """
    The date by which this invoice's supplier must file GSTR-1 for the credit
    to land in the expected period: the 11th of the month after the invoice.

    Chasing a supplier is only useful before that date, which is exactly why
    Munim checks an invoice when it arrives instead of at month end. Returns
    None for an unparseable date rather than guessing a deadline — a wrong
    countdown is worse than none, because a CA would act on it.
    """
    if not invoice_date_str:
        return None
    try:
        d = date.fromisoformat(str(invoice_date_str)[:10])
    except (ValueError, TypeError):
        return None
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return date(year, month, 11)


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
        user_res = db.table("traders").select("whatsapp_number").eq("id", current_trader_id).execute()
        if not user_res.data:
            return {"traders": []}
            
        phone = user_res.data[0].get("whatsapp_number", "")
        phone_full = phone if phone.startswith("91") else f"91{phone}"
        phone_10 = phone[-10:] if len(phone) >= 10 else phone
        
        response = db.table("traders").select(
            "id, name, business_name, gstin, whatsapp_number, is_composition, language_pref"
        ).or_(f"id.eq.{current_trader_id},ca_whatsapp_number.eq.{phone_full},ca_whatsapp_number.eq.{phone_10}").execute()

        return {"traders": response.data or []}
    except Exception as e:
        raise safe_http_error(logger, "Failed to list traders", e)


class TraderCompositionModel(BaseModel):
    is_composition: bool


@router.patch("/traders/{trader_id}/composition")
async def set_trader_composition(payload: TraderCompositionModel, trader_id: str = Depends(verify_trader_access)):
    """Toggle whether a client is registered under the GST Composition Scheme.

    Composition dealers cannot claim ITC at all, so this gates MoneyMeter's
    display for that client. Set from the CA's profile/client-list page.
    """
    try:
        db = get_supabase()
        db.table("traders").update({"is_composition": payload.is_composition}).eq("id", trader_id).execute()
        return {"trader_id": trader_id, "is_composition": payload.is_composition}
    except Exception as e:
        raise safe_http_error(logger, "Failed to update composition status", e)


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
        raise safe_http_error(logger, "Failed to compute GSTR-2B reconciliation status", e)


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
        raise safe_http_error(logger, "Report generation failed", e)


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
        raise safe_http_error(logger, "Failed to fetch generated reports", e)


# The POST /check-deadlines route was removed: it was unauthenticated, it
# sent WhatsApp messages (real per-message cost on an open endpoint), and its
# body was hardcoded demo text ("Tomorrow is the 11th") regardless of the
# actual date. The real job is main.py's `deadline_alerts` APScheduler entry,
# which runs on the 5th/10th/18th off live invoice data. Nothing in the
# frontend or mobile app ever called the HTTP trigger.


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
        raise safe_http_error(logger, "Failed to compute GSTR-3B draft", e)


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
        raise safe_http_error(logger, "Failed to build IMS invoice feed", e)



import json
import os
from pydantic import BaseModel

class PreferencesModel(BaseModel):
    dashboard: list[str]
    sidebar: list[str]
    money_meter_top: list[str] | None = None
    money_meter_bottom: list[str] | None = None

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


_SHORT_CODE_ALPHABET = string.ascii_uppercase + string.digits


def _generate_short_code(db, length: int = 6) -> str:
    """Random short_code, retried against the DB on collision. There's no
    separate CAs table -- any trader row can be the CA side of a QR link
    (see deps.py:verify_trader_access), so short_code lives on traders."""
    for _ in range(5):
        candidate = "".join(secrets.choice(_SHORT_CODE_ALPHABET) for _ in range(length))
        existing = db.table("traders").select("id").eq("short_code", candidate).execute()
        if not existing.data:
            return candidate
    raise RuntimeError("Could not generate a unique short_code after 5 attempts")


class AskQuestionModel(BaseModel):
    question: str


@router.post("/ask/{trader_id}")
async def ask_trader_question(
    payload: AskQuestionModel,
    trader_id: str = Depends(verify_trader_access),
):
    """
    Real-answer backend for the trader PWA's voice-query button (and usable
    for a future typed-question box too) -- reuses the exact same
    LLM-backed answer function WhatsApp's text/voice query handling already
    calls (webhook.py's _answer_general_query -> gemini.py's
    answer_trader_question), rather than the PWA's own separate
    VoiceQueryButton.js / utils/voiceIntent.js, which only recognizes three
    fixed question shapes by design (see that file's own header comment) --
    fine for "no network call" but the reason it felt broken against
    anything else, next to WhatsApp's much more flexible answer.

    Deadline-math duplicated from webhook.py's _answer_general_query rather
    than shared, matching that function's own stated reasoning: keeping
    this endpoint from ever risking a change to the live WhatsApp handler.
    """
    from datetime import date
    from app.services.supabase_client import get_itc_summary, get_recent_invoices
    from app.services.gemini import answer_trader_question

    language_pref = "hi"  # safe default -- overwritten below once the real
                          # trader row is fetched, but the except block
                          # needs something to fall back on even if that
                          # fetch itself is what fails.
    try:
        db = get_supabase()
        trader_res = db.table("traders").select("business_name, language_pref").eq("id", trader_id).execute()
        trader_row = trader_res.data[0] if trader_res.data else {}
        language_pref = trader_row.get("language_pref", "hi")

        buckets = await get_itc_summary(trader_id)
        recent = await get_recent_invoices(trader_id, limit=3)

        today = date.today()
        if today.day <= 11:
            next_filing_type, deadline_day = "GSTR-1", 11
        else:
            next_filing_type, deadline_day = "GSTR-3B", 20
        days_remaining = deadline_day - today.day

        context_data = {
            "business_name": trader_row.get("business_name"),
            "itc_summary_totals": buckets,
            "recent_invoices": recent,
            "next_filing_deadline": {
                "filing_type": next_filing_type,
                "deadline_day_of_month": deadline_day,
                "days_remaining": days_remaining,
            },
        }
        answer = await answer_trader_question(payload.question, context_data, language_pref)
        if not answer or not answer.strip():
            raise ValueError("answer_trader_question returned an empty answer")
        return {"answer": answer}
    except Exception as e:
        logger.error(f"ask_trader_question failed for {trader_id}: {e}")
        fallback = {
            "hi": "Kuch dikkat aa gayi, kripya dubara try karein.",
            "en": "Something went wrong, please try again.",
            "mr": "काहीतरी चूक झाली, कृपया पुन्हा प्रयत्न करा.",
            "gu": "કંઈક ખોટું થયું, કૃપા કરી ફરી પ્રયાસ કરો.",
        }
        return {"answer": fallback.get(language_pref, fallback["hi"])}


class PushTokenModel(BaseModel):
    token: str


@router.post("/register-push-token")
async def register_push_token(payload: PushTokenModel, current_trader_id: str = Depends(get_current_trader_id)):
    """
    Stores an Expo push token against the logged-in trader, so scheduled
    alerts (backend/app/main.py's deadline_alerts job today) can reach this
    device directly instead of only via WhatsApp. Called from
    frontend/src/app/trader/page.js's MUNIM_PUSH_TOKEN listener, which
    receives the token from mobile/App.tsx's own push-registration
    useEffect -- that native code has existed since the CA-dashboard commit,
    but nothing on the web side was ever listening for what it sent until
    now, so no token had ever actually reached the database.
    """
    try:
        await update_trader(current_trader_id, {"push_token": payload.token})
        return {"status": "success"}
    except Exception as e:
        raise safe_http_error(logger, "Failed to register push token", e)


@router.post("/transcribe-audio")
async def transcribe_audio(
    audio: UploadFile = File(...),
    current_trader_id: str = Depends(get_current_trader_id),
):
    """
    Speech-to-text for the trader PWA's voice-query button, over a plain
    authenticated HTTP call rather than the browser's Web Speech API --
    that API is unsupported inside the React Native WebView the mobile app
    embeds this page in (a long-standing Android System WebView limitation;
    Firefox lacks it too), which is why VoiceQueryButton.js's mic button
    silently doesn't even render there. Same transcription path
    webhook.py's handle_voice_message() already uses for WhatsApp voice
    notes -- Groq's hosted Whisper, not a second implementation of speech-to-
    text. Only the input transport differs: WhatsApp hands us an already-
    downloaded media_id, this endpoint takes a browser-recorded audio blob
    directly. Everything downstream (voiceIntent.js's local intent
    matching) is unchanged.
    """
    from groq import AsyncGroq

    settings = get_settings()
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio upload")

    try:
        client = AsyncGroq(api_key=settings.groq_api_key)
        transcription = await client.audio.transcriptions.create(
            file=(audio.filename or "audio.webm", audio_bytes),
            model="whisper-large-v3",
        )
        return {"text": transcription.text.strip()}
    except Exception as e:
        raise safe_http_error(logger, "Audio transcription failed", e)


@router.get("/onboard-link")
async def get_onboard_link(current_trader_id: str = Depends(get_current_trader_id)):
    """Return the caller's WhatsApp QR-onboarding deep link, generating and
    persisting their short_code on first request."""
    try:
        db = get_supabase()
        res = db.table("traders").select("id, short_code").eq("id", current_trader_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Trader not found")

        short_code = res.data[0].get("short_code")
        if not short_code:
            short_code = _generate_short_code(db)
            await update_trader(current_trader_id, {"short_code": short_code})

        business_number = get_settings().whatsapp_business_number
        deep_link = f"https://wa.me/{business_number}?text=JOIN-{short_code}"
        return {"short_code": short_code, "deep_link": deep_link}
    except HTTPException:
        raise
    except Exception as e:
        raise safe_http_error(logger, "Failed to build onboarding link", e)



@router.get("/explain/{invoice_id}")
async def explain_invoice_verdict(invoice_id: str, current_trader_id: str = Depends(get_current_trader_id)):
    """
    "Says who?" — the clause of the CGST Act behind one invoice's verdict.

    The section number and its quoted words come from `domain/statute.py`, not
    from a model. That is the whole point: a plausible-sounding section that
    does not exist is worse on a compliance screen than no citation at all, so
    a verdict this module cannot map returns `citation: null` and the UI says
    so honestly.
    """
    from app.domain import statute

    try:
        db = get_supabase()
        rows = db.table("invoices").select(
            "id, trader_id, supplier_name, gstin_supplier, invoice_number, invoice_date, "
            "itc_status, itc_block_reason, itc_amount_eligible, itc_amount_blocked, "
            "gstr2b_match_status, fraud_score"
        ).eq("id", invoice_id).limit(1).execute().data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Invoice not found")

        invoice = rows[0]
        owner = invoice.get("trader_id")
        if not owner:
            logger.warning(f"Invoice {invoice_id} has no trader_id — refusing explain")
            raise HTTPException(status_code=403, detail="Not authorized to view this invoice")
        await verify_trader_access(owner, current_trader_id)

        reason = invoice.get("itc_block_reason")
        status = invoice.get("itc_status")
        citation = statute.cite_for_reason(reason)
        # `derived` tells the UI how confident to be: a citation resolved from
        # the engine's own reason string is traceable to the rule that fired;
        # one inferred from the status alone is a reasonable guess about an
        # older row, and should not be presented with the same certainty.
        derived = "reason" if citation else None
        if not citation:
            citation = statute.cite_for_status(status)
            derived = "status" if citation else None

        return {
            "invoice_id": invoice_id,
            "status": status,
            "reason": reason,
            "supplier_name": invoice.get("supplier_name"),
            "invoice_number": invoice.get("invoice_number"),
            "invoice_date": invoice.get("invoice_date"),
            "amount_eligible": invoice.get("itc_amount_eligible"),
            "amount_blocked": invoice.get("itc_amount_blocked"),
            "citation": citation.to_dict() if citation else None,
            "citation_derived_from": derived,
            "note": None if citation else (
                "Munim cannot trace this verdict to a specific clause, so it is "
                "not quoting one. The reason above is what the engine recorded."
            ),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise safe_http_error(logger, f"Failed to explain invoice {invoice_id}", e)


@router.get("/supplier-network/{trader_id}")
async def get_supplier_network(trader_id: str = Depends(verify_trader_access)):
    """
    What every other business Munim monitors has experienced of this trader's
    suppliers.

    Strictly aggregate — see `domain/network_intel` for the three rules that
    govern it. A supplier below the minimum cohort returns `available: false`
    with the reason, because a stated absence is honest and a silent zero is
    not.
    """
    from app.domain.network_intel import MIN_OTHER_TRADERS, bulk_network_signals

    try:
        db = get_supabase()
        rows = db.table("invoices").select("gstin_supplier, supplier_name").eq(
            "trader_id", trader_id
        ).execute().data or []

        names: dict[str, str] = {}
        for r in rows:
            g = r.get("gstin_supplier")
            if g and g not in names:
                names[g] = r.get("supplier_name") or ""

        signals = bulk_network_signals(list(names), trader_id)
        suppliers = [
            {"gstin": g, "supplier_name": names.get(g) or "Unknown supplier", **sig}
            for g, sig in signals.items()
        ]
        # Riskiest first; unavailable ones last. A CA scanning this wants the
        # supplier the network is warning about at the top, not alphabetical order.
        rank = {"RISKY": 0, "MIXED": 1, "CLEAN": 2, "UNKNOWN": 3}
        suppliers.sort(key=lambda s: (rank.get(s.get("verdict"), 9), -(s.get("default_rate") or 0)))

        return {
            "trader_id": trader_id,
            "min_other_traders": MIN_OTHER_TRADERS,
            "suppliers": suppliers,
            "reportable": sum(1 for s in suppliers if s.get("available")),
            "flagged": sum(1 for s in suppliers if s.get("verdict") == "RISKY"),
        }
    except Exception as e:
        raise safe_http_error(logger, "Failed to compute supplier network intelligence", e)
