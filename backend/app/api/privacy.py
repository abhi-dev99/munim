import json
import logging
from fastapi import APIRouter, HTTPException, Depends

from app.api.deps import get_current_trader_id, verify_trader_access
from app.services.privacy_layer import AUDIT_LOG_PATH
from app.services.supabase_client import get_supabase
from app.utils.errors import safe_http_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/privacy", tags=["privacy"])


def _rows_to_calls(rows: list[dict]) -> list[dict]:
    """Flatten audit_log rows into the call shape the transparency view wants."""
    calls = []
    for row in rows:
        entry = row.get("event_data") or {}
        if isinstance(entry, str):
            try:
                entry = json.loads(entry)
            except (ValueError, TypeError):
                entry = {}
        calls.append({
            **entry,
            "trader_id": row.get("trader_id"),
            "logged_at": row.get("created_at"),
        })
    return calls


@router.get("/llm-calls/{trader_id}")
async def get_llm_calls_for_trader(
    trader_id: str = Depends(verify_trader_access),
    limit: int = 50,
) -> dict:
    """
    What Munim sent to a model provider on this trader's behalf, and which
    fields were masked before it left.

    Scoped to one trader and gated by the same CA-access check as the rest of
    the API. The previous version of this endpoint authenticated the caller
    and then ignored who they were, returning every tenant's calls to anyone
    holding a valid token.
    """
    try:
        limit = max(1, min(limit, 200))
        rows = (
            get_supabase()
            .table("audit_log")
            .select("trader_id, event_data, created_at")
            .eq("trader_id", trader_id)
            .eq("event_type", "llm_anonymization")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        ).data or []
        return {"trader_id": trader_id, "calls": _rows_to_calls(rows)}
    except Exception as e:
        raise safe_http_error(logger, "Failed to read the model-call audit trail", e)


@router.get("/last-llm-calls")
async def get_last_llm_calls(limit: int = 10, caller: str = Depends(get_current_trader_id)) -> dict:
    """
    The caller's own model-call trail.

    Kept because it is the original path; it now returns only the caller's own
    rows rather than every tenant's. Use /llm-calls/{trader_id} to read a
    client's trail as their CA.

    `source` says where the rows came from, because that distinction is the
    whole point of this endpoint: "db" is the durable trail, "file" is a
    local-development fallback that does not survive a App Runner restart and
    is per-instance, so it must never be mistaken for a complete record.
    """
    try:
        limit = max(1, min(limit, 200))
        rows = (
            get_supabase()
            .table("audit_log")
            .select("trader_id, event_data, created_at")
            .eq("trader_id", caller)
            .eq("event_type", "llm_anonymization")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        ).data or []
        if rows:
            return {"source": "db", "calls": _rows_to_calls(rows)}
    except Exception as e:
        logger.warning(f"audit_log read failed, falling back to the local file: {e}")

    try:
        lines = []
        with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    lines.append(json.loads(line))
        lines.reverse()
        return {"source": "file", "calls": lines[:limit]}
    except FileNotFoundError:
        return {"source": "db", "calls": []}
    except Exception as e:
        raise safe_http_error(logger, "Failed to read the model-call audit trail", e)
