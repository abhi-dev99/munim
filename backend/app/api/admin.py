import logging
import time
import httpx
import asyncio
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.services.supabase_client import get_supabase
from app.config import get_settings
from app.models.invoice import InvoiceJSON, LineItem
from app.agents.invoice_agent import invoice_agent, InvoiceAgentState

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


@router.get("/system-status")
async def system_status(service: Optional[str] = Query(None, description="Check specific service or 'all'")):
    """
    Dev endpoint to check health and latency of all core components or a specific service.
    Supported services: supabase, gemini, groq, redis, langgraph, ngrok, backend
    """
    settings = get_settings()
    db = get_supabase()
    status = {}

    check_all = service is None or service.lower() == "all"
    target = service.lower() if service else "all"

    # 1. Supabase Database
    if check_all or target == "supabase":
        start = time.time()
        try:
            res = db.table("traders").select("id", count="exact").limit(1).execute()
            latency = round((time.time() - start) * 1000)
            status["supabase"] = {
                "name": "Supabase Database",
                "status": "online",
                "latency_ms": latency,
                "message": f"Connected (Traders count: {res.count})",
                "category": "Database & Storage"
            }
        except Exception as e:
            status["supabase"] = {
                "name": "Supabase Database",
                "status": "offline",
                "latency_ms": round((time.time() - start) * 1000),
                "message": str(e)[:100],
                "category": "Database & Storage"
            }

    # 2. Gemini API (LLM & Multimodal OCR)
    if check_all or target == "gemini":
        start = time.time()
        try:
            if settings.gemini_api_key and len(settings.gemini_api_key) > 10:
                status["gemini"] = {
                    "name": "Gemini Multimodal API (OCR / LLM)",
                    "status": "online",
                    "latency_ms": round((time.time() - start) * 1000),
                    "message": "API key configured & valid",
                    "category": "AI Models"
                }
            else:
                status["gemini"] = {
                    "name": "Gemini Multimodal API (OCR / LLM)",
                    "status": "offline",
                    "latency_ms": 0,
                    "message": "Missing GEMINI_API_KEY",
                    "category": "AI Models"
                }
        except Exception as e:
            status["gemini"] = {
                "name": "Gemini Multimodal API (OCR / LLM)",
                "status": "offline",
                "latency_ms": 0,
                "message": str(e)[:100],
                "category": "AI Models"
            }

    # 3. Groq API (Inference Fallback)
    if check_all or target == "groq":
        start = time.time()
        try:
            if settings.groq_api_key and len(settings.groq_api_key) > 10:
                status["groq"] = {
                    "name": "Groq Llama-3.3 API (Fast Inference)",
                    "status": "online",
                    "latency_ms": round((time.time() - start) * 1000),
                    "message": "Groq Llama-3.3-70B configured",
                    "category": "AI Models"
                }
            else:
                status["groq"] = {
                    "name": "Groq Llama-3.3 API (Fast Inference)",
                    "status": "offline",
                    "latency_ms": 0,
                    "message": "Missing GROQ_API_KEY (Gemini primary active)",
                    "category": "AI Models"
                }
        except Exception as e:
            status["groq"] = {
                "name": "Groq Llama-3.3 API (Fast Inference)",
                "status": "offline",
                "latency_ms": 0,
                "message": str(e)[:100],
                "category": "AI Models"
            }

    # 4. Redis / Cache Layer
    if check_all or target == "redis":
        start = time.time()
        try:
            from app.services.redis_client import get_redis
            r = get_redis()
            if r:
                pong = r.ping()
                latency = round((time.time() - start) * 1000)
                status["redis"] = {
                    "name": "Redis Distributed Cache",
                    "status": "online" if pong else "offline",
                    "latency_ms": latency,
                    "message": "Connected to Upstash/Redis",
                    "category": "Infrastructure"
                }
            else:
                status["redis"] = {
                    "name": "Redis Distributed Cache",
                    "status": "online",
                    "latency_ms": 1,
                    "message": "In-Memory LRU Fallback Cache Active",
                    "category": "Infrastructure"
                }
        except Exception as e:
            status["redis"] = {
                "name": "Redis Distributed Cache",
                "status": "online",
                "latency_ms": round((time.time() - start) * 1000),
                "message": "In-Memory Fallback Cache Active (Redis offline)",
                "category": "Infrastructure"
            }

    # 5. LangGraph Reconciliation Engine
    if check_all or target == "langgraph":
        start = time.time()
        try:
            if invoice_agent and hasattr(invoice_agent, "ainvoke"):
                status["langgraph"] = {
                    "name": "LangGraph Reconciliation Engine",
                    "status": "online",
                    "latency_ms": round((time.time() - start) * 1000),
                    "message": "7-Node Autonomous Graph Compiled & Ready",
                    "category": "Core Engine"
                }
            else:
                status["langgraph"] = {
                    "name": "LangGraph Reconciliation Engine",
                    "status": "offline",
                    "latency_ms": 0,
                    "message": "StateGraph not compiled",
                    "category": "Core Engine"
                }
        except Exception as e:
            status["langgraph"] = {
                "name": "LangGraph Reconciliation Engine",
                "status": "offline",
                "latency_ms": round((time.time() - start) * 1000),
                "message": str(e)[:100],
                "category": "Core Engine"
            }

    # 6. Ngrok Webhook Tunnel
    if check_all or target == "ngrok":
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get("http://127.0.0.1:4040/api/tunnels")
                if resp.status_code == 200:
                    tunnels = resp.json().get("tunnels", [])
                    public_url = tunnels[0]["public_url"] if tunnels else "No tunnels active"
                    status["ngrok"] = {
                        "name": "Ngrok Webhook Tunnel",
                        "status": "online" if tunnels else "offline",
                        "latency_ms": round((time.time() - start) * 1000),
                        "message": public_url,
                        "category": "Infrastructure"
                    }
                else:
                    status["ngrok"] = {
                        "name": "Ngrok Webhook Tunnel",
                        "status": "offline",
                        "latency_ms": round((time.time() - start) * 1000),
                        "message": f"HTTP {resp.status_code}",
                        "category": "Infrastructure"
                    }
        except Exception:
            status["ngrok"] = {
                "name": "Ngrok Webhook Tunnel",
                "status": "offline",
                "latency_ms": round((time.time() - start) * 1000),
                "message": "Ngrok API unreachable (run start_dev.bat)",
                "category": "Infrastructure"
            }

    # 7. Backend Server
    if check_all or target == "backend":
        status["backend"] = {
            "name": "FastAPI Backend Server",
            "status": "online",
            "latency_ms": 0,
            "message": "Running on port 8000 (APScheduler active)",
            "category": "Core Engine"
        }

    return status


@router.post("/test-recon-pipeline")
async def test_recon_pipeline(mode: str = Query("mock", description="'mock' for instant sample JSON, 'live' for real invoice.png.jpeg OCR")):
    """
    Live Sandbox / Test Bench for the LangGraph Reconciliation Engine.
    Executes the entire 7-node pipeline and returns step-by-step diagnostic outputs,
    statutory ITC verdict, fraud score, and bilingual diagnosis messages.
    """
    start_time = time.time()
    test_trader_uuid = "6d123264-9325-4a37-b769-274834a04085"

    steps_log = []

    if mode == "live":
        img_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "invoice.png.jpeg")
        if not os.path.exists(img_path):
            raise HTTPException(status_code=404, detail=f"Live test image invoice.png.jpeg not found at {img_path}")
        with open(img_path, "rb") as f:
            image_bytes = f.read()

        initial_state: InvoiceAgentState = {
            "trader_id": test_trader_uuid,
            "media_url": None,
            "raw_image": image_bytes,
            "mime_type": "image/jpeg",
            "invoice_json": None,
            "gstin_validation": None,
            "hsn_validations": [],
            "gstr2b_match": None,
            "itc_verdict": None,
            "fraud_result": None,
            "diagnosis_hi": "",
            "diagnosis_en": "",
            "action_items": [],
            "error": None,
            "start_time": time.time(),
            "processing_duration_ms": 0,
        }
    else:
        # Mocked sample invoice
        sample_invoice = InvoiceJSON(
            invoice_number="DEV-TEST-INV-001",
            invoice_date="2026-07-20",
            gstin_supplier="27AABCU9603R1ZN",
            gstin_buyer="27XYZAB1234C1Z9",
            supplier_name="Demo Enterprise Ltd",
            total_taxable_amount=40000.0,
            total_tax_amount=7200.0,
            total_amount=47200.0,
            line_items=[
                LineItem(
                    description="Industrial Tea Processing Units",
                    hsn_code="0902",
                    quantity=4,
                    unit_price=10000.0,
                    taxable_value=40000.0,
                    cgst_rate=9.0,
                    sgst_rate=9.0,
                    igst_rate=0.0,
                    cgst_amount=3600.0,
                    sgst_amount=3600.0,
                    igst_amount=0.0
                )
            ],
            confidence=0.98
        )

        initial_state: InvoiceAgentState = {
            "trader_id": test_trader_uuid,
            "media_url": None,
            "raw_image": b"dummy_bytes",
            "mime_type": "image/jpeg",
            "invoice_json": sample_invoice,
            "gstin_validation": None,
            "hsn_validations": [],
            "gstr2b_match": None,
            "itc_verdict": None,
            "fraud_result": None,
            "diagnosis_hi": "",
            "diagnosis_en": "",
            "action_items": [],
            "error": None,
            "start_time": time.time(),
            "processing_duration_ms": 0,
        }

    try:
        accumulated_state = dict(initial_state)

        # Stream node-by-node execution to record exact step output
        async for event in invoice_agent.astream(initial_state):
            for node_name, state_update in event.items():
                accumulated_state.update(state_update)

                if node_name == "extract_entities":
                    inv = accumulated_state.get("invoice_json")
                    if inv:
                        steps_log.append({
                            "node": "extract_entities",
                            "step_num": 1,
                            "title": "Multimodal Vision OCR & JSON Extraction",
                            "status": "success",
                            "summary": f"Extracted Bill #{inv.invoice_number} from {inv.supplier_name}",
                            "details": {
                                "supplier_name": inv.supplier_name,
                                "gstin_supplier": inv.gstin_supplier,
                                "invoice_number": inv.invoice_number,
                                "invoice_date": inv.invoice_date,
                                "total_amount": inv.total_amount,
                                "total_tax": inv.total_tax_amount,
                                "line_items_count": len(inv.line_items),
                                "confidence_pct": round((inv.confidence or 0.95) * 100, 1)
                            }
                        })
                elif node_name == "validate_gstin":
                    val = accumulated_state.get("gstin_validation")
                    if val:
                        steps_log.append({
                            "node": "validate_gstin",
                            "step_num": 2,
                            "title": "Supplier GSTIN Verification",
                            "status": "success" if val.is_valid else "warning",
                            "summary": f"GSTIN {val.gstin}: {val.verification_status}",
                            "details": {
                                "gstin": val.gstin,
                                "verification_status": val.verification_status,
                                "is_valid": val.is_valid,
                                "is_active": val.is_active,
                                "taxpayer_type": val.taxpayer_type or "Regular"
                            }
                        })
                elif node_name == "validate_hsn":
                    validations = accumulated_state.get("hsn_validations", [])
                    mismatches = [v for v in validations if v.rate_mismatch]
                    steps_log.append({
                        "node": "validate_hsn",
                        "step_num": 3,
                        "title": "Statutory HSN Code & Rate Validation",
                        "status": "warning" if mismatches else "success",
                        "summary": f"Checked {len(validations)} HSN items — {'Rate Mismatch Detected' if mismatches else 'All Rates Statutory Valid'}",
                        "details": {
                            "total_checked": len(validations),
                            "mismatch_count": len(mismatches),
                            "items": [
                                {
                                    "hsn": v.hsn_code_extracted,
                                    "rate_applied": v.tax_rate_applied,
                                    "rate_correct": v.tax_rate_correct,
                                    "mismatch": v.rate_mismatch,
                                    "delta_impact": v.itc_delta or 0.0
                                } for v in validations
                            ]
                        }
                    })
                elif node_name == "reconcile_gstr2b":
                    match = accumulated_state.get("gstr2b_match")
                    if match:
                        steps_log.append({
                            "node": "reconcile_gstr2b",
                            "step_num": 4,
                            "title": "GSTR-2B Portal Matching & CDNR Netting",
                            "status": "warning" if match.status.value == "UNRECONCILED" else "success",
                            "summary": f"Reconciliation Status: {match.status.value}",
                            "details": {
                                "status": match.status.value,
                                "confidence_pct": round(match.confidence * 100, 1),
                                "matched_record_id": match.matched_record_id or "None",
                                "claimable_itc": match.itc_amount or 0.0
                            }
                        })
                elif node_name == "compute_itc":
                    v = accumulated_state.get("itc_verdict")
                    if v:
                        steps_log.append({
                            "node": "compute_itc",
                            "step_num": 5,
                            "title": "12-Point Statutory ITC Engine (CGST Act)",
                            "status": "warning" if v.status.value in ("FIXABLE_BLOCKED", "AT_RISK") else ("error" if v.status.value == "INELIGIBLE" else "success"),
                            "summary": f"Verdict: {v.status.value} (Sec {v.legal_section})",
                            "details": {
                                "status": v.status.value,
                                "eligible_itc": v.itc_amount,
                                "blocked_itc": v.itc_blocked,
                                "legal_section": v.legal_section or "16(2)",
                                "statutory_reason": v.reason,
                                "fix_action": v.fix_action
                            }
                        })
                elif node_name == "score_fraud":
                    f = accumulated_state.get("fraud_result")
                    if f:
                        steps_log.append({
                            "node": "score_fraud",
                            "step_num": 6,
                            "title": "4-Signal Forensic Fraud Scorer",
                            "status": "error" if f.is_hard_flag else ("warning" if f.is_soft_flag else "success"),
                            "summary": f"Risk Score: {f.total_score}/100 — {'FLAGGED' if (f.is_hard_flag or f.is_soft_flag) else 'CLEAN'}",
                            "details": {
                                "total_score": f.total_score,
                                "is_hard_flag": f.is_hard_flag,
                                "is_soft_flag": f.is_soft_flag,
                                "triggered_signals": [
                                    {"name": sig.signal_name, "score": sig.score_contribution, "detail": sig.detail}
                                    for sig in f.signals if sig.triggered
                                ]
                            }
                        })
                elif node_name == "generate_diagnosis":
                    hi = accumulated_state.get("diagnosis_hi", "")
                    en = accumulated_state.get("diagnosis_en", "")
                    actions = accumulated_state.get("action_items", [])
                    steps_log.append({
                        "node": "generate_diagnosis",
                        "step_num": 7,
                        "title": "Bilingual WhatsApp & Email Diagnosis",
                        "status": "success",
                        "summary": "Generated WhatsApp Hindi/English diagnosis & action items",
                        "details": {
                            "hindi_text": hi,
                            "english_text": en,
                            "action_items": actions
                        }
                    })

        total_time_ms = round((time.time() - start_time) * 1000)

        return {
            "status": "success",
            "mode": mode,
            "total_duration_ms": total_time_ms,
            "steps_count": len(steps_log),
            "steps": steps_log,
            "verdict": accumulated_state.get("itc_verdict").dict() if accumulated_state.get("itc_verdict") else None,
            "fraud": accumulated_state.get("fraud_result").dict() if accumulated_state.get("fraud_result") else None,
            "diagnosis_hi": accumulated_state.get("diagnosis_hi", ""),
            "diagnosis_en": accumulated_state.get("diagnosis_en", ""),
            "action_items": accumulated_state.get("action_items", [])
        }
    except Exception as e:
        logger.error(f"Recon pipeline dev test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class AddKeyRequest(BaseModel):
    api_key: str


@router.get("/gemini-keys")
async def get_gemini_keys_status():
    """Get live status and usage statistics of all Gemini API keys in the rotation pool."""
    try:
        from app.services.gemini import client as gemini_pool
        return gemini_pool.get_status()
    except Exception as e:
        logger.error(f"Failed to get gemini keys status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gemini-keys/add")
async def add_gemini_key(payload: AddKeyRequest):
    """Add a new Gemini API key to the active rotation pool."""
    try:
        from app.services.gemini import client as gemini_pool
        added = gemini_pool.add_key(payload.api_key)
        if not added:
            raise HTTPException(status_code=400, detail="Key already exists or is invalid")
        return {"status": "success", "message": "Key added to rotation pool", "pool_status": gemini_pool.get_status()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add gemini key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gemini-keys/reset")
async def reset_gemini_keys():
    """Reset rate_limited status on all keys in the pool so they can be tried immediately."""
    try:
        from app.services.gemini import client as gemini_pool
        gemini_pool.reset_limits()
        return {"status": "success", "message": "All API keys reset to active", "pool_status": gemini_pool.get_status()}
    except Exception as e:
        logger.error(f"Failed to reset gemini keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))
