"""
Munim.ai — small typed event store over the existing `audit_log` table.

Why this exists instead of new tables
-------------------------------------
`audit_log(trader_id UUID, event_type VARCHAR, event_data JSONB, created_at)`
is already in the live database and is already generic. Features that need to
remember a *fact about something that happened* — we asked this trader about a
missing bill; this vendor said they would file by Friday — are event-shaped,
and putting them here means they work against the database as it actually
exists today.

That matters more than usual in this codebase. Schema drift is the recurring
bug class here: `backend/schema.sql` is not the live database, migrations are
applied by hand, and code written against a column that was never migrated
fails *silently* through the per-record try/except pattern. Two migrations are
outstanding right now. Adding two more tables to that queue would mean two more
features that look like they work and quietly store nothing.

The trade-off, stated plainly: no foreign keys into `event_data`, no indexes on
its fields, and filtering happens in Python over a bounded fetch. At this
product's scale — tens of clients, hundreds of open items — that is the right
side of the trade. If a practice ever carries thousands of open recovery
requests, these become real tables with real indexes, and `record`/`find`/
`update` are the only three functions that have to change.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# Stable event_type values. Anything written here is queried by exact match, so
# these strings are effectively schema — do not rename them casually.
ITC_RECOVERY_REQUEST = "itc_recovery_request"
VENDOR_FIX_RESPONSE = "vendor_fix_response"
VENDOR_FIX_LINK_ISSUED = "vendor_fix_link_issued"


def _valid_uuid(value: Any) -> Optional[str]:
    """audit_log.trader_id is a real FK, so a non-UUID has to become null
    rather than fail the insert."""
    if not value:
        return None
    try:
        uuid.UUID(str(value))
        return str(value)
    except (ValueError, AttributeError, TypeError):
        return None


def record(trader_id: Optional[str], event_type: str, data: dict) -> Optional[str]:
    """
    Append one event. Returns its row id, or None if the write failed.

    Callers must treat None as a failure and say so to the user. The silent
    `inserted: 0` pattern this codebase already suffers from is exactly what
    a returned id is here to prevent.
    """
    try:
        payload = dict(data)
        payload.setdefault("recorded_at", datetime.now(timezone.utc).isoformat())
        res = (
            get_supabase()
            .table("audit_log")
            .insert({
                "trader_id": _valid_uuid(trader_id),
                "event_type": event_type,
                "event_data": payload,
            })
            .execute()
        )
        if res.data:
            return res.data[0].get("id")
        logger.error("event_store.record: insert returned no row for %s", event_type)
        return None
    except Exception as e:
        logger.error("event_store.record failed for %s: %s", event_type, e)
        return None


def _flatten(row: dict) -> dict:
    """Present a stored row the way callers want to read it: the event payload
    with the row's own identity merged in. `event_id` and `created_at` are
    reserved and always win over anything in the payload."""
    out = dict(row.get("event_data") or {})
    out["event_id"] = row.get("id")
    out["created_at"] = row.get("created_at")
    out["trader_id"] = row.get("trader_id") or out.get("trader_id")
    return out


def find(
    event_type: str,
    trader_id: Optional[str] = None,
    limit: int = 200,
    where: Optional[dict] = None,
) -> list[dict]:
    """
    Newest-first events of one type, optionally scoped to a trader.

    `where` filters on keys inside the JSON payload, in Python — see the
    module docstring on why that is acceptable at this scale. It is applied
    after the fetch, so a narrow `where` over a large history can return fewer
    than `limit` rows; pass a larger limit if that matters to the caller.
    """
    try:
        q = (
            get_supabase()
            .table("audit_log")
            .select("id, trader_id, event_data, created_at")
            .eq("event_type", event_type)
        )
        tid = _valid_uuid(trader_id)
        if tid:
            q = q.eq("trader_id", tid)
        rows = (q.order("created_at", desc=True).limit(limit).execute()).data or []
    except Exception as e:
        logger.error("event_store.find failed for %s: %s", event_type, e)
        return []

    events = [_flatten(r) for r in rows]
    if where:
        events = [
            e for e in events
            if all(e.get(k) == v for k, v in where.items())
        ]
    return events


def get(event_id: str) -> Optional[dict]:
    """One event by row id, flattened. None if it does not exist."""
    try:
        rows = (
            get_supabase()
            .table("audit_log")
            .select("id, trader_id, event_data, created_at")
            .eq("id", event_id)
            .limit(1)
            .execute()
        ).data or []
        return _flatten(rows[0]) if rows else None
    except Exception as e:
        logger.error("event_store.get failed for %s: %s", event_id, e)
        return None


def update(event_id: str, patch: dict) -> bool:
    """
    Shallow-merge `patch` into an event's payload.

    Read-then-write, because PostgREST cannot merge a jsonb column in place.
    Two concurrent updates to the same event would therefore last-write-wins.
    Every caller here updates an event in response to one human action on one
    item, so the race is not reachable in practice — but it is a real limit and
    is why nothing financial is ever stored only in an event payload.
    """
    try:
        db = get_supabase()
        rows = (
            db.table("audit_log")
            .select("event_data")
            .eq("id", event_id)
            .limit(1)
            .execute()
        ).data or []
        if not rows:
            logger.warning("event_store.update: no event %s", event_id)
            return False
        merged = dict(rows[0].get("event_data") or {})
        merged.update(patch)
        merged["updated_at"] = datetime.now(timezone.utc).isoformat()
        db.table("audit_log").update({"event_data": merged}).eq("id", event_id).execute()
        return True
    except Exception as e:
        logger.error("event_store.update failed for %s: %s", event_id, e)
        return False
