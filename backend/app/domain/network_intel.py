"""
Munim.ai — network supplier intelligence.

A single CA sees one trader's experience of a supplier. Munim sees every
trader's. "This GSTIN failed to report 4 of 11 invoices, across 3 other
businesses we monitor" is a judgement no one client's books can support, and
it is the one signal in this product that gets strictly better with scale.

Three rules govern this module, and they are not negotiable:

1. **Aggregate only.** Counts leave; identities never do. No trader id, name,
   phone, invoice number or amount belonging to another trader is returned by
   anything in here, ever.
2. **A minimum cohort.** Below `MIN_OTHER_TRADERS` other businesses, "1 other
   trader had a problem" is close enough to naming them. Under the threshold
   the answer is `available: False` — a stated absence, not a quiet zero.
3. **Unknown is not clean.** An invoice nobody has reconciled yet says nothing
   about the supplier. Those rows are excluded from the denominator rather
   than counted as compliant, because inflating the denominator understates
   the default rate — the direction of error that gets a trader hurt.

Deliberately *not* wired in as a seventh fraud signal: `FraudDetector.WEIGHTS`
must sum to 100, so adding one re-weights the other six and silently re-scores
every invoice already in the database. Supplier reputation is a property of
the supplier, not of one inbound invoice, so it belongs on the supplier
surfaces, where it is also far easier for a CA to interrogate.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Iterable, Optional

from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# How many *other* businesses must have dealt with a supplier before Munim will
# say anything about the network's experience of it.
MIN_OTHER_TRADERS = 2

# Two independent things can tell us whether a supplier reported a sale, and
# both count as an observation:
#
#   1. Batch reconciliation against an uploaded GSTR-2B, which writes
#      `gstr2b_match_status`. Strongest evidence, but it only exists for
#      periods where someone uploaded the 2B and ran the matcher.
#   2. The ITC engine's own verdict at the moment the invoice arrived.
#      AT_RISK is literally "not found in GSTR-2B, supplier may not have filed"
#      — which is the same observation, made earlier. Given that arriving-time
#      checking is this product's central claim, ignoring it would be odd.
#
# Reconciliation wins where both exist, since it is the later and better look.
# Anything else — UNRECONCILED, null, a verdict that never depended on the 2B —
# is "we have not looked", and is evidence in neither direction.
_OBSERVED = {"MATCHED", "PROBABLE_MATCH", "POSSIBLE_MATCH", "ITC_AT_RISK"}
_DEFAULTED = {"ITC_AT_RISK"}

# itc_status values that imply the engine did check the 2B position.
_OBSERVED_ITC = {"CONFIRMED", "AT_RISK"}
_DEFAULTED_ITC = {"AT_RISK"}

# Bands for the headline verdict. Chosen to be legible to a shopkeeper rather
# than statistically clever: below a tenth is noise, above a third is a pattern.
_CLEAN_BELOW = 0.10
_RISKY_ABOVE = 0.33


def _empty(reason: str) -> dict:
    return {
        "available": False,
        "reason": reason,
        "other_traders": 0,
        "verdict": "UNKNOWN",
    }


def _fetch_network_rows(gstins: list[str]) -> list[dict]:
    """
    Every invoice in the system from these suppliers, across all traders.

    This is the one deliberately cross-tenant read in the codebase. It is
    confined to this function so there is exactly one place to audit, and the
    only columns it selects are the ones the aggregation needs — no amounts,
    no invoice numbers, no supplier-side contact data.
    """
    if not gstins:
        return []
    rows: list[dict] = []
    # PostgREST puts the filter in the URL, so a practice with hundreds of
    # suppliers would blow the URL length limit in one call.
    CHUNK = 40
    db = get_supabase()
    for i in range(0, len(gstins), CHUNK):
        batch = gstins[i:i + CHUNK]
        try:
            res = (
                db.table("invoices")
                .select("trader_id, gstin_supplier, gstr2b_match_status, itc_status")
                .in_("gstin_supplier", batch)
                .execute()
            )
            rows.extend(res.data or [])
        except Exception as e:
            logger.error("network_intel: batch fetch failed for %d gstins: %s", len(batch), e)
    return rows


def bulk_network_signals(
    gstins: Iterable[str],
    requesting_trader_id: Optional[str] = None,
) -> dict[str, dict]:
    """
    Network reputation for many suppliers in one pass.

    Returns a dict keyed by GSTIN. Every requested GSTIN gets an entry, so a
    caller can render "not enough data" without a second lookup.
    """
    wanted = [g for g in {g for g in gstins if g}]
    if not wanted:
        return {}

    rows = _fetch_network_rows(wanted)

    traders_by_gstin: dict[str, set] = defaultdict(set)
    affected_by_gstin: dict[str, set] = defaultdict(set)
    observed: dict[str, int] = defaultdict(int)
    defaulted: dict[str, int] = defaultdict(int)

    for r in rows:
        g = r.get("gstin_supplier")
        t = r.get("trader_id")
        if not g or not t:
            continue
        traders_by_gstin[g].add(t)

        status = r.get("gstr2b_match_status")
        itc = r.get("itc_status")
        if status in _OBSERVED:
            saw, missed = True, status in _DEFAULTED
        elif itc in _OBSERVED_ITC:
            saw, missed = True, itc in _DEFAULTED_ITC
        else:
            saw, missed = False, False

        if saw:
            observed[g] += 1
            if missed:
                defaulted[g] += 1
                affected_by_gstin[g].add(t)

    out: dict[str, dict] = {}
    for g in wanted:
        others = traders_by_gstin[g] - ({requesting_trader_id} if requesting_trader_id else set())
        if len(others) < MIN_OTHER_TRADERS:
            out[g] = _empty(
                f"Munim monitors this supplier for fewer than {MIN_OTHER_TRADERS + 1} "
                "businesses, which is too few to report a network pattern without "
                "effectively identifying one of them."
            )
            continue

        seen = observed[g]
        missed = defaulted[g]
        if not seen:
            out[g] = _empty(
                "No invoice from this supplier has been reconciled against a "
                "GSTR-2B yet, so the network has not actually observed their "
                "filing behaviour."
            )
            continue

        rate = missed / seen
        verdict = "CLEAN" if rate < _CLEAN_BELOW else ("RISKY" if rate > _RISKY_ABOVE else "MIXED")
        affected_others = affected_by_gstin[g] - ({requesting_trader_id} if requesting_trader_id else set())

        out[g] = {
            "available": True,
            "reason": None,
            "other_traders": len(others),
            "observed_invoices": seen,
            "unreported_invoices": missed,
            "default_rate": round(rate, 3),
            "other_traders_affected": len(affected_others),
            "verdict": verdict,
            "summary": _summarise(len(others), seen, missed, len(affected_others), verdict),
        }
    return out


def _summarise(others: int, seen: int, missed: int, affected: int, verdict: str) -> str:
    """One sentence a CA can read out to their client without translating it."""
    if verdict == "CLEAN":
        return (
            f"Across {others} other businesses Munim monitors, this supplier "
            f"reported {seen - missed} of {seen} checked invoices on time."
        )
    if affected:
        return (
            f"This supplier failed to report {missed} of {seen} invoices Munim "
            f"has checked, affecting {affected} other business"
            f"{'es' if affected != 1 else ''} besides this one."
        )
    return (
        f"This supplier failed to report {missed} of {seen} invoices Munim has "
        f"checked across {others} other businesses."
    )


def supplier_network_signal(
    gstin: str,
    requesting_trader_id: Optional[str] = None,
) -> dict:
    """Network reputation for one supplier. Thin wrapper over the bulk path."""
    if not gstin:
        return _empty("No GSTIN supplied.")
    return bulk_network_signals([gstin], requesting_trader_id).get(
        gstin, _empty("No network data for this GSTIN.")
    )
