import json
import logging
from fastapi import APIRouter, HTTPException
from typing import List

from app.services.privacy_layer import AUDIT_LOG_PATH

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/privacy", tags=["privacy"])

@router.get("/last-llm-calls")
async def get_last_llm_calls(limit: int = 10) -> dict:
    """
    Returns the last N audit log entries showing exactly what was anonymized and sent to LLMs.
    This provides transparency for CA firms on data privacy.
    """
    try:
        lines = []
        with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    lines.append(json.loads(line))
        
        # Return latest first
        lines.reverse()
        return {"calls": lines[:limit]}
    except FileNotFoundError:
        return {"calls": []}
    except Exception as e:
        logger.error(f"Failed to read privacy audit logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to read audit logs")
