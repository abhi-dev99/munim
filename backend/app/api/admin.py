import logging
from fastapi import APIRouter, HTTPException
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@router.delete("/invoices/{invoice_id}")
async def delete_invoice(invoice_id: str):
    """Delete an invoice by ID (for demo admin purposes)."""
    db = get_supabase()
    try:
        db.table("invoices").delete().eq("id", invoice_id).execute()
        return {"status": "success", "deleted_id": invoice_id}
    except Exception as e:
        logger.error(f"Failed to delete invoice {invoice_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

import time
import httpx
import asyncio
from app.config import get_settings

@router.get("/system-status")
async def system_status():
    """Dev endpoint to check health and latency of external dependencies."""
    settings = get_settings()
    db = get_supabase()
    status = {}

    # 1. Supabase Check
    start = time.time()
    try:
        # Simple count query to test connection and wake up the DB
        res = db.table("traders").select("id", count="exact").limit(1).execute()
        latency = round((time.time() - start) * 1000)
        status["supabase"] = {
            "status": "online",
            "latency_ms": latency,
            "message": f"Connected (Count: {res.count})"
        }
    except Exception as e:
        status["supabase"] = {
            "status": "offline",
            "latency_ms": round((time.time() - start) * 1000),
            "message": str(e)
        }

    # 2. Gemini API Check
    start = time.time()
    try:
        # Just check if key exists and isn't empty, since actual LLM ping costs money/time
        if settings.gemini_api_key and len(settings.gemini_api_key) > 10:
            status["gemini"] = {
                "status": "online",
                "latency_ms": 0,
                "message": "API Key configured"
            }
        else:
            status["gemini"] = {
                "status": "offline",
                "latency_ms": 0,
                "message": "Missing API Key"
            }
    except Exception as e:
        status["gemini"] = {"status": "offline", "message": str(e)}

    # 3. Ngrok Check
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get("http://127.0.0.1:4040/api/tunnels")
            if resp.status_code == 200:
                tunnels = resp.json().get("tunnels", [])
                public_url = tunnels[0]["public_url"] if tunnels else "No tunnels active"
                status["ngrok"] = {
                    "status": "online" if tunnels else "offline",
                    "latency_ms": round((time.time() - start) * 1000),
                    "message": public_url
                }
            else:
                status["ngrok"] = {"status": "offline", "message": f"HTTP {resp.status_code}"}
    except Exception as e:
        status["ngrok"] = {
            "status": "offline",
            "latency_ms": round((time.time() - start) * 1000),
            "message": "Ngrok API unreachable"
        }

    return status
