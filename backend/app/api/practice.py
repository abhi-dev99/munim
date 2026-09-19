"""
Munim.ai — the CA's practice view.

Every other surface in this product answers "how is this client doing?". A CA
carrying twenty to sixty clients has the opposite question on a Monday
morning: **which of them needs me this week, and in what order?**

That inversion is the whole feature. The output is one row per client, ranked
by rupees genuinely at risk, each carrying the single reason that put it
there and the date by which somebody has to act.

Two engineering constraints shaped this file:

*   **No N+1.** Sixty clients must not mean sixty round trips. Every table is
    read once, in chunks, filtered by `in_(trader_ids)`, and aggregated in
    Python. A practice view that takes eleven seconds does not get opened on a
    Monday morning.
*   **Ranking has to be defensible.** "Rupees at risk" is credit that is
    recoverable and running out of time — the AT_RISK and FIXABLE_BLOCKED
    buckets. Credit that is blocked under Section 17(5) is not at risk; it is
    gone, and padding the number with it would send a CA chasing a supplier
    about a car they cannot claim either way.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends

from app.api.deps import get_current_trader_id, get_practice_client_ids
from app.domain import statute
from app.services.supabase_client import get_supabase
from app.utils.errors import safe_http_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/practice", tags=["practice"])

# PostgREST puts `in.(...)` filters in the URL, so batch the client list.
_CHUNK = 40

# Statutory dates the whole practice shares. GSTR-1 is the supplier's deadline
# and therefore the last useful day to chase one; GSTR-3B is the trader's own.
_GSTR1_DAY = 11
_GSTR2B_DAY = 14
_GSTR3B_DAY = 20

# Buckets that represent money still recoverable. See the module docstring.
_AT_RISK_STATUSES = {"AT_RISK"}
_FIXABLE_STATUSES = {"FIXABLE_BLOCKED", "FRAUD_FLAGGED", "DUPLICATE"}
_OPEN_STATUSES = _AT_RISK_STATUSES | _FIXABLE_STATUSES

# A supplier deadline missed longer ago than this is history, not this week's
# work. See `_attention`.
_STALE_AFTER_DAYS = 30


def _chunked(items: list, size: int = _CHUNK):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _with_retry(describe: str, call):
    """
    Run one Supabase read, retrying once on a transport-level failure.

    A pooled HTTP/2 connection that the server has already closed surfaces as
    `RemoteProtocolError: Server disconnected` on the next request that picks
    it up. The retry gets a fresh connection. Only transport errors are
    retried -- a 4xx would fail again identically, and retrying it would just
    double the latency before the same error.
    """
    try:
        return call()
    except Exception as first:
        if "disconnect" not in str(first).lower() and "protocol" not in str(first).lower():
            raise
        logger.warning("practice: %s hit a stale connection, retrying once: %s", describe, first)
        return call()


def _fetch_all(table: str, columns: str, trader_ids: list[str]) -> list[dict]:
    """
    One table, every listed trader, batched and paged.

    The paging is not optional. PostgREST caps an unbounded select at 1,000
    rows and returns them with no error and no indication of truncation —
    this trader has 2,319 GSTR-2B rows, so the first version of this function
    silently read less than half of one client's data and computed a
    confident, wrong unclaimed-credit figure from it. Truncation that looks
    like an answer is the exact failure mode this codebase already has too
    much of, so every read here is explicitly paged to exhaustion.

    Failures are logged and the batch skipped rather than aborting the whole
    view — a practice list missing one client's numbers is more useful than an
    error page, provided the caller can tell, which `partial` in the response
    does.
    """
    PAGE = 1000
    db = get_supabase()
    rows: list[dict] = []
    ok = True
    for batch in _chunked(trader_ids):
        offset = 0
        while True:
            try:
                page = _with_retry(
                    f"{table} offset {offset}",
                    lambda: (
                        db.table(table)
                        .select(columns)
                        .in_("trader_id", batch)
                        .range(offset, offset + PAGE - 1)
                        .execute()
                    ).data or [],
                )
            except Exception as e:
                ok = False
                logger.error("practice: %s fetch failed for %d traders at offset %d: %s",
                             table, len(batch), offset, e)
                break
            rows.extend(page)
            if len(page) < PAGE:
                break
            offset += PAGE
    if not ok:
        rows.append({"__partial__": True})
    return rows


def _fetch_traders(client_ids: list[str]) -> list[dict]:
    """The client roster itself. Separate so it can run alongside the two
    large reads rather than in front of them."""
    try:
        return _with_retry(
            "trader roster",
            lambda: (
                get_supabase()
                .table("traders")
                .select("id, name, business_name, gstin, whatsapp_number, is_composition, language_pref")
                .in_("id", client_ids)
                .execute()
            ).data or [],
        )
    except Exception as e:
        # Unlike the two big reads, this one failing is not a partial view --
        # it is an empty one. Re-raised so the endpoint returns an error the
        # CA can retry instead of "you have no clients".
        logger.error("practice: trader roster fetch failed: %s", e)
        raise


def _days_until(day_of_month: int, today: date) -> int:
    """Days until the next occurrence of a statutory day-of-month."""
    if today.day <= day_of_month:
        return day_of_month - today.day
    # Roll into next month.
    if today.month == 12:
        nxt = date(today.year + 1, 1, day_of_month)
    else:
        nxt = date(today.year, today.month + 1, day_of_month)
    return (nxt - today).days


def _money_at_stake(invoice: dict, status: str) -> float:
    """
    What this invoice actually puts at risk, whichever column it landed in.

    `itc_engine` writes an AT_RISK verdict as `itc_amount = total_tax` with
    `itc_blocked = 0` — the credit is real and merely exposed, not disallowed.
    Rows loaded by the seed scripts use the opposite convention and put the
    figure in `itc_amount_blocked`, leaving `itc_amount_eligible` at zero.

    103 of this database's 104 AT_RISK invoices are the second kind, so
    reading only `itc_amount_eligible` reports a client's at-risk exposure as
    roughly nil and ranks them last on a screen built to say who needs help
    first. Taking whichever column carries the number is correct under both
    conventions, because each one leaves the other at zero.
    """
    eligible = float(invoice.get("itc_amount_eligible") or 0)
    blocked = float(invoice.get("itc_amount_blocked") or 0)
    if status in _AT_RISK_STATUSES:
        return eligible or blocked
    return blocked or eligible


def _parse_date(value) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None


@router.get("/overview")
async def practice_overview(current_trader_id: str = Depends(get_current_trader_id)):
    """
    Every client this CA acts for, ranked by rupees at risk.

    Returns the practice totals alongside the rows, because the first thing a
    CA wants is the number they are carrying across the whole book — not a
    sum they have to do in their head from a table.
    """
    try:
        today = date.today()
        client_ids = await get_practice_client_ids(current_trader_id)
        if not client_ids:
            return {
                "generated_at": today.isoformat(),
                "clients": [],
                "totals": _empty_totals(),
                "partial": False,
                "deadlines": _deadlines(today),
            }

        # Sequential, deliberately, and it cost a round of debugging to learn
        # why. Supabase round trips dominate this endpoint, so an earlier
        # version ran these three reads concurrently via asyncio.to_thread.
        # They all share one process-wide `supabase-py` client, whose
        # underlying httpx connection pool is synchronous and multiplexes over
        # HTTP/2 -- driving it from three threads at once produced
        # `RemoteProtocolError: Server disconnected` on all three reads
        # simultaneously, intermittently. Intermittently is the worst kind:
        # it passed twice before it failed.
        #
        # Giving each thread its own client would fix the sharing but pay a
        # fresh TLS handshake for roughly the latency it saves. A few seconds
        # on a screen a CA opens once a morning is the right thing to trade,
        # so this runs one read at a time and each one retries once.
        traders = _fetch_traders(client_ids)
        invoices = _fetch_all(
            "invoices",
            "trader_id, itc_status, itc_amount_eligible, itc_amount_blocked, "
            "itc_block_reason, invoice_date, processed_at, gstr2b_match_status, "
            "supplier_name, gstin_supplier",
            client_ids,
        )
        gstr2b = _fetch_all(
            "gstr2b_records",
            "trader_id, month, year, matched_invoice_id, igst, cgst, sgst",
            client_ids,
        )

        partial = any(r.get("__partial__") for r in invoices + gstr2b)
        invoices = [r for r in invoices if not r.get("__partial__")]
        gstr2b = [r for r in gstr2b if not r.get("__partial__")]

        inv_by_trader = defaultdict(list)
        for inv in invoices:
            inv_by_trader[inv.get("trader_id")].append(inv)

        rows = [
            _build_client_row(t, inv_by_trader.get(t["id"], []), gstr2b, today)
            for t in traders
        ]

        # A composition dealer cannot claim credit at all, so ranking them by
        # rupees at risk is meaningless; they sort to the bottom and carry an
        # explicit note instead of a misleading zero.
        rows.sort(key=lambda r: (not r["is_composition"], r["rupees_at_risk"]), reverse=True)
        for i, r in enumerate(rows):
            r["rank"] = i + 1

        return {
            "generated_at": today.isoformat(),
            "clients": rows,
            "totals": _totals(rows),
            "partial": partial,
            "deadlines": _deadlines(today),
        }
    except Exception as e:
        raise safe_http_error(logger, "Failed to build the practice overview", e)


def _empty_totals() -> dict:
    return {
        "clients": 0,
        "needs_attention": 0,
        "rupees_at_risk": 0.0,
        "unclaimed_credit": 0.0,
        "open_items": 0,
        "unreconciled_clients": 0,
    }


def _totals(rows: list[dict]) -> dict:
    return {
        "clients": len(rows),
        "needs_attention": sum(1 for r in rows if r["needs_attention"]),
        "rupees_at_risk": round(sum(r["rupees_at_risk"] for r in rows), 2),
        "unclaimed_credit": round(sum(r["unclaimed_credit"] for r in rows), 2),
        "open_items": sum(r["open_items"] for r in rows),
        "unreconciled_clients": sum(1 for r in rows if not r["reconciled"]),
    }


def _deadlines(today: date) -> list[dict]:
    return [
        {
            "label": "GSTR-1",
            "day": _GSTR1_DAY,
            "days_left": _days_until(_GSTR1_DAY, today),
            "whose": "supplier",
            "note": "Last useful day to chase a supplier for this period.",
        },
        {
            "label": "GSTR-2B",
            "day": _GSTR2B_DAY,
            "days_left": _days_until(_GSTR2B_DAY, today),
            "whose": "portal",
            "note": "The portal publishes; reconcile after this.",
        },
        {
            "label": "GSTR-3B",
            "day": _GSTR3B_DAY,
            "days_left": _days_until(_GSTR3B_DAY, today),
            "whose": "trader",
            "note": "Filing and payment.",
        },
    ]


def _build_client_row(trader: dict, invoices: list[dict], gstr2b_rows: list[dict], today: date) -> dict:
    tid = trader["id"]
    is_composition = bool(trader.get("is_composition"))

    at_risk = 0.0
    fixable = 0.0
    open_items = 0
    reasons: Counter = Counter()
    soonest: Optional[date] = None
    last_seen: Optional[date] = None

    for inv in invoices:
        processed = _parse_date(inv.get("processed_at"))
        if processed and (last_seen is None or processed > last_seen):
            last_seen = processed

        status = inv.get("itc_status") or ""
        if status not in _OPEN_STATUSES:
            continue

        open_items += 1
        reasons[(inv.get("itc_block_reason") or status).strip()] += 1

        if status in _AT_RISK_STATUSES:
            at_risk += _money_at_stake(inv, status)
            # The supplier's GSTR-1 deadline is the real clock on an AT_RISK
            # item: after the 11th of the month following the invoice, the
            # supplier can no longer fix this period.
            inv_date = _parse_date(inv.get("invoice_date"))
            if inv_date:
                due = _gstr1_due_for(inv_date)
                if soonest is None or due < soonest:
                    soonest = due
        else:
            fixable += _money_at_stake(inv, status)

    unclaimed, reconciled, period = _unclaimed_for(tid, gstr2b_rows)

    rupees_at_risk = 0.0 if is_composition else round(at_risk + fixable, 2)
    top_reason, citation = _top_reason(reasons)

    needs, why = _attention(
        is_composition=is_composition,
        open_items=open_items,
        rupees_at_risk=rupees_at_risk,
        unclaimed=unclaimed,
        reconciled=reconciled,
        soonest=soonest,
        today=today,
    )

    return {
        "trader_id": tid,
        "name": trader.get("name") or "Unnamed",
        "business_name": trader.get("business_name") or "",
        "gstin": trader.get("gstin") or "",
        "whatsapp_number": trader.get("whatsapp_number") or "",
        "language_pref": trader.get("language_pref") or "en",
        "is_composition": is_composition,
        "invoices": len(invoices),
        "open_items": open_items,
        "at_risk_amount": round(at_risk, 2),
        "fixable_amount": round(fixable, 2),
        "rupees_at_risk": rupees_at_risk,
        "unclaimed_credit": round(unclaimed, 2),
        "unclaimed_period": period,
        "reconciled": reconciled,
        "top_reason": top_reason,
        "citation": citation.to_dict() if citation else None,
        "chase_by": soonest.isoformat() if soonest else None,
        "days_to_chase": (soonest - today).days if soonest else None,
        "last_activity": last_seen.isoformat() if last_seen else None,
        "needs_attention": needs,
        "why": why,
    }


def _gstr1_due_for(invoice_date: date) -> date:
    """The 11th of the month after the invoice — when the supplier's GSTR-1
    for that period is due, and so the last day chasing them can still work."""
    if invoice_date.month == 12:
        return date(invoice_date.year + 1, 1, _GSTR1_DAY)
    return date(invoice_date.year, invoice_date.month + 1, _GSTR1_DAY)


def _unclaimed_for(trader_id: str, gstr2b_rows: list[dict]) -> tuple[float, bool, Optional[str]]:
    """
    Unclaimed credit for this client's newest GSTR-2B period.

    Mirrors `/gstr2b/missed-itc` exactly, including its central caution: an
    unmatched row only means unclaimed credit if matching has actually been
    persisted for that period. Before that, every row is unmatched by
    definition and the figure would be the entire 2B value — confidently
    wrong, which on this screen is worse than blank.
    """
    mine = [r for r in gstr2b_rows if r.get("trader_id") == trader_id]
    if not mine:
        return 0.0, False, None

    newest = max((r.get("year") or 0, r.get("month") or 0) for r in mine)
    period_rows = [r for r in mine if (r.get("year") or 0, r.get("month") or 0) == newest]

    reconciled = any(r.get("matched_invoice_id") for r in period_rows)
    if not reconciled:
        return 0.0, False, f"{newest[1]}/{newest[0]}"

    unclaimed = sum(
        float(r.get("igst") or 0) + float(r.get("cgst") or 0) + float(r.get("sgst") or 0)
        for r in period_rows
        if not r.get("matched_invoice_id")
    )
    return unclaimed, True, f"{newest[1]}/{newest[0]}"


def _top_reason(reasons: Counter) -> tuple[Optional[str], Optional[statute.Citation]]:
    """The single reason behind most of this client's open items, with the
    clause of the Act it comes from. One reason, not a list: this row exists
    to tell a CA where to start, and a list is not a starting point."""
    if not reasons:
        return None, None
    reason = reasons.most_common(1)[0][0]
    return reason, statute.cite_for_reason(reason)


def _attention(
    *,
    is_composition: bool,
    open_items: int,
    rupees_at_risk: float,
    unclaimed: float,
    reconciled: bool,
    soonest: Optional[date],
    today: date,
) -> tuple[bool, str]:
    """
    Whether this client needs the CA this week, and the one-line reason.

    Ordered by urgency, most time-critical first, because only the first
    matching reason is shown. A client whose supplier deadline passes on
    Thursday is a different problem from one sitting on unclaimed credit, and
    conflating them is how the second never gets done.
    """
    if is_composition:
        return False, "Composition scheme — no input tax credit to manage."

    if soonest is not None:
        left = (soonest - today).days
        # Only a *recently* missed deadline is this week's news. An invoice
        # whose supplier window closed eight months ago is history: it belongs
        # in the client's brief, but letting it win this line would bury the
        # live problem behind a permanent red flag nobody can act on.
        if -_STALE_AFTER_DAYS <= left < 0:
            return True, (
                f"A supplier's GSTR-1 deadline passed {abs(left)} day"
                f"{'s' if abs(left) != 1 else ''} ago — this period can no longer be fixed at source."
            )
        if 0 <= left <= 7:
            return True, (
                f"{left} day{'s' if left != 1 else ''} left to chase a supplier "
                "before their GSTR-1 closes for this period."
            )

    if not reconciled:
        return True, "GSTR-2B has never been reconciled, so nothing here has been checked."

    if unclaimed > 0:
        return True, f"₹{round(unclaimed):,} of credit suppliers reported was never claimed."

    if rupees_at_risk > 0:
        return True, f"{open_items} open item{'s' if open_items != 1 else ''} worth ₹{round(rupees_at_risk):,}."

    return False, "Nothing outstanding."


@router.get("/client/{trader_id}/brief")
async def client_brief(trader_id: str, current_trader_id: str = Depends(get_current_trader_id)):
    """
    The one client in detail: what to actually do, in order.

    This is what a CA opens after the overview tells them where to start, so
    it answers the next question — not "how much", but "which invoices, whose
    supplier, by when".
    """
    from app.api.deps import verify_trader_access

    await verify_trader_access(trader_id, current_trader_id)
    try:
        today = date.today()
        db = get_supabase()
        invoices = (
            db.table("invoices")
            .select(
                "id, supplier_name, gstin_supplier, invoice_number, invoice_date, "
                "itc_status, itc_amount_eligible, itc_amount_blocked, itc_block_reason"
            )
            .eq("trader_id", trader_id)
            .in_("itc_status", sorted(_OPEN_STATUSES))
            .execute()
        ).data or []

        items = []
        for inv in invoices:
            status = inv.get("itc_status") or ""
            amount = _money_at_stake(inv, status)
            inv_date = _parse_date(inv.get("invoice_date"))
            due = _gstr1_due_for(inv_date) if (inv_date and status in _AT_RISK_STATUSES) else None
            citation = statute.cite_for_reason(inv.get("itc_block_reason")) or statute.cite_for_status(status)
            items.append({
                "invoice_id": inv["id"],
                "supplier_name": inv.get("supplier_name") or inv.get("gstin_supplier") or "Unknown supplier",
                "gstin_supplier": inv.get("gstin_supplier"),
                "invoice_number": inv.get("invoice_number"),
                "invoice_date": inv.get("invoice_date"),
                "status": status,
                "amount": round(amount, 2),
                "reason": inv.get("itc_block_reason"),
                "section": citation.section if citation else None,
                "fix": (citation.fix if citation else None),
                "chase_by": due.isoformat() if due else None,
                "days_to_chase": (due - today).days if due else None,
            })

        # Three buckets, in the order a CA would work them:
        #
        #   0  expiring soon  — still fixable, and running out. A ₹900 item
        #                       that dies on Thursday outranks a ₹40,000 one
        #                       with a month left, because only one of them
        #                       stops being recoverable.
        #   1  no clock       — fixable whenever; rank purely by money.
        #   2  already gone   — the supplier window closed. Kept, because a CA
        #                       still has to write these off, but never at the
        #                       top of a list headed "what to do".
        #
        # The first version sorted on days_to_chase alone, which put a
        # ₹0 invoice whose deadline passed 247 days ago at position one.
        def _bucket(i: dict) -> int:
            d = i["days_to_chase"]
            if d is None:
                return 1
            return 0 if d >= 0 else 2

        items.sort(key=lambda i: (
            _bucket(i),
            i["days_to_chase"] if _bucket(i) == 0 else 0,
            -i["amount"],
        ))

        return {
            "trader_id": trader_id,
            "generated_at": today.isoformat(),
            "count": len(items),
            "total_amount": round(sum(i["amount"] for i in items), 2),
            "actionable": sum(1 for i in items if _bucket(i) != 2),
            "expired": sum(1 for i in items if _bucket(i) == 2),
            "items": items,
        }
    except Exception as e:
        raise safe_http_error(logger, "Failed to build the client brief", e)
