"""
Munim.ai — Supplier Monitoring Service
Daily health check, state-change detection, and proactive alerts.
"""

import logging
from datetime import date, timedelta
from typing import Optional

from app.services.supabase_client import (
    get_all_supplier_gstins,
    get_supabase,
    update_supplier,
    add_supplier_flag,
)
from app.services.gstin import verify_gstin
from app.services.redis_cache import (
    get_cached_gstin,
    cache_gstin,
    invalidate_gstin_cache,
)
from app.services import whatsapp

logger = logging.getLogger(__name__)


# High-fraud sector keywords
HIGH_FRAUD_SECTORS = [
    "iron", "steel", "scrap", "textile", "chemical",
    "construction", "real estate", "pan masala",
]


async def run_daily_supplier_check():
    """
    Daily supplier monitoring job.
    Checks all supplier GSTINs, detects state changes, updates health scores.
    """
    logger.info("[SupplierMonitor] Starting daily supplier check...")

    db = get_supabase()
    suppliers_response = db.table("suppliers").select("*").execute()
    suppliers = suppliers_response.data or []

    alerts_generated = 0

    for supplier in suppliers:
        gstin = supplier["gstin"]
        supplier_id = supplier["id"]

        try:
            # Get previous cached state
            previous_state = get_cached_gstin(gstin)

            # Verify current state (force API call, bypass cache)
            current = await verify_gstin(gstin, use_cache=False)

            if not current.is_valid:
                continue

            # --- Detect State Transitions ---
            flags_to_add = []

            # 1. GSTIN Cancelled
            if previous_state and previous_state.get("is_active") and not current.is_active:
                flags_to_add.append(("GSTIN_CANCELLED", "GSTIN has been cancelled"))

            # 2. Scheme Switch (Regular → Composition)
            if previous_state:
                old_type = previous_state.get("taxpayer_type", "")
                if old_type == "Regular" and current.taxpayer_type == "Composition":
                    flags_to_add.append(("SCHEME_SWITCH", "Switched to Composition — ITC blocked"))

            # 3. New GSTIN Risk
            if current.registration_date:
                try:
                    reg_date = date.fromisoformat(current.registration_date)
                    age_days = (date.today() - reg_date).days
                    if age_days < 180:
                        flags_to_add.append(("NEW_GSTIN_RISK", f"GSTIN is only {age_days} days old"))
                except (ValueError, TypeError):
                    pass

            # 4. Sector Risk
            if current.business_category:
                cat_lower = current.business_category.lower()
                if any(sector in cat_lower for sector in HIGH_FRAUD_SECTORS):
                    flags_to_add.append(("SECTOR_RISK", f"High-fraud sector: {current.business_category}"))

            # Apply flags
            for flag_type, detail in flags_to_add:
                await add_supplier_flag(supplier_id, flag_type, {"detail": detail})
                alerts_generated += 1

            # Compute health score
            health_score = await _compute_health_score(supplier_id, current)
            await update_supplier(supplier_id, {
                "health_score": health_score,
                "last_verified_at": date.today().isoformat(),
                "legal_name": current.legal_name,
                "taxpayer_type": current.taxpayer_type,
            })

            # Update cache with new state
            cache_gstin(gstin, {
                "gstin": current.gstin,
                "is_valid": current.is_valid,
                "is_active": current.is_active,
                "taxpayer_type": current.taxpayer_type,
                "registration_date": current.registration_date,
                "legal_name": current.legal_name,
                "business_category": current.business_category,
                "filing_status": current.filing_status,
            })

            # Send WhatsApp alerts for critical flags
            if flags_to_add:
                await _send_supplier_alerts(supplier_id, gstin, flags_to_add)

        except Exception as e:
            logger.error(f"Supplier check failed for {gstin}: {e}")

    logger.info(f"[SupplierMonitor] Completed. Checked {len(suppliers)} suppliers, generated {alerts_generated} alerts.")


async def _compute_health_score(supplier_id: str, gstin_data) -> int:
    """
    Compute supplier health score 0-100.
    Weighted: filing consistency (40%), GSTIN age (15%), flag count (30%), sector risk (15%).
    """
    db = get_supabase()
    score = 100

    # Filing consistency (40% weight) — based on filing_status
    if gstin_data.filing_status:
        status_lower = gstin_data.filing_status.lower()
        if "not filed" in status_lower or "cancelled" in status_lower:
            score -= 40
        elif "late" in status_lower:
            score -= 20

    # GSTIN age (15% weight)
    if gstin_data.registration_date:
        try:
            reg_date = date.fromisoformat(gstin_data.registration_date)
            age_days = (date.today() - reg_date).days
            if age_days < 180:
                score -= 15
            elif age_days < 365:
                score -= 7
        except (ValueError, TypeError):
            pass

    # Active flags (30% weight)
    flags_response = db.table("supplier_flags").select("flag_type").eq(
        "supplier_id", supplier_id
    ).eq("is_active", True).execute()
    flag_count = len(flags_response.data or [])
    score -= min(flag_count * 10, 30)

    # Sector risk (15% weight)
    if gstin_data.business_category:
        cat_lower = gstin_data.business_category.lower()
        if any(sector in cat_lower for sector in HIGH_FRAUD_SECTORS):
            score -= 15

    return max(0, min(100, score))


async def _send_supplier_alerts(supplier_id: str, gstin: str, flags: list[tuple[str, str]]):
    """Send WhatsApp alerts to all traders linked to this supplier."""
    db = get_supabase()

    # Find all traders linked to this supplier
    links = db.table("supplier_trader_links").select(
        "trader_id, traders(whatsapp_number, name)"
    ).eq("supplier_id", supplier_id).execute()

    if not links.data:
        return

    for link in links.data:
        trader = link.get("traders", {})
        phone = trader.get("whatsapp_number")
        if not phone:
            continue

        flag_descriptions = "\n".join(f"• {desc}" for _, desc in flags)
        msg = (
            f"🚨 Supplier Alert!\n\n"
            f"Supplier GSTIN: {gstin}\n"
            f"Issues detected:\n{flag_descriptions}\n\n"
            f"Aapke ITC par asar pad sakta hai. "
            f"Is supplier se payment karne se pehle yeh issues check karo."
        )

        await whatsapp.send_text_message(phone, msg)
