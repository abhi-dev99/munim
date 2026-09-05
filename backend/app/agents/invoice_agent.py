"""
Munim.ai — LangGraph Invoice Processing Agent
Stateful directed graph for processing invoices end-to-end.

Graph flow:
  extract_entities → validate_gstin → validate_hsn → reconcile_gstr2b
    → compute_itc → score_fraud → generate_diagnosis → END

Conditional edges:
  - If extraction fails → handle_error → END
  - If GSTIN is invalid → short-circuit to generate_diagnosis
"""

import time
import logging
from typing import TypedDict, Optional, Annotated

from langgraph.graph import StateGraph, END

from app.models.invoice import (
    InvoiceJSON,
    GSTINValidation,
    HSNValidationResult,
    GSTR2BMatchResult,
    GSTR2BMatchStatus,
    FraudResult,
    ITCVerdict,
    ITCStatus,
    InvoiceDiagnosis,
)
from app.services import gemini
from app.services.gstin import verify_gstin
from app.services.supabase_client import get_supabase
from app.domain.itc_engine import ITCRulesEngine
from app.domain.hsn import HSNValidator
from app.domain.reconciler import GSTR2BReconciler, GSTR2BRecord
from app.domain.fraud import FraudScorer

logger = logging.getLogger(__name__)


# --- Agent State ---

class InvoiceAgentState(TypedDict):
    """State that flows through the LangGraph pipeline."""
    # Input
    trader_id: str
    media_url: Optional[str]
    raw_image: Optional[bytes]
    mime_type: str

    # Processing
    invoice_json: Optional[InvoiceJSON]
    gstin_validation: Optional[GSTINValidation]
    hsn_validations: list[HSNValidationResult]
    gstr2b_match: Optional[GSTR2BMatchResult]
    itc_verdict: Optional[ITCVerdict]
    fraud_result: Optional[FraudResult]

    # Output
    diagnosis_hi: str
    diagnosis_en: str
    action_items: list[str]
    error: Optional[str]

    # Metadata
    start_time: float
    processing_duration_ms: int


# --- Node Functions ---

async def extract_entities(state: InvoiceAgentState) -> dict:
    """Node 1: Extract structured invoice data from image using Gemini Vision."""
    logger.info(f"[InvoiceAgent] Extracting entities for trader {state['trader_id']}")

    if not state.get("raw_image"):
        return {"error": "No image data provided", "invoice_json": None}

    try:
        invoice_json = await gemini.extract_invoice_from_image(
            state["raw_image"],
            mime_type=state.get("mime_type", "image/jpeg"),
        )

        # Check for quota exceeded sentinel
        if invoice_json and invoice_json.confidence == -1.0:
            return {
                "error": "API_QUOTA_EXCEEDED",
                "invoice_json": None,
            }

        if not invoice_json or (invoice_json.confidence is not None and invoice_json.confidence < 0.4):
            conf = invoice_json.confidence if invoice_json else None
            return {
                "error": f"Low confidence extraction ({conf}) — image may be too blurry or not an invoice",
                "invoice_json": invoice_json,
            }

        # If confidence is None (field not returned by model), proceed — don't reject valid data
        return {"invoice_json": invoice_json, "error": None}


    except Exception as e:
        logger.error(f"Entity extraction failed: {e}")
        return {"error": f"Extraction failed: {str(e)}", "invoice_json": None}


async def validate_gstin(state: InvoiceAgentState) -> dict:
    """Node 2: Validate supplier GSTIN via API (cached)."""
    invoice = state.get("invoice_json")
    if not invoice or not invoice.gstin_supplier:
        return {"gstin_validation": None}

    try:
        validation = await verify_gstin(invoice.gstin_supplier)
        return {"gstin_validation": validation}
    except Exception as e:
        logger.error(f"GSTIN validation failed: {e}")
        return {"gstin_validation": None}


async def validate_hsn(state: InvoiceAgentState) -> dict:
    """Node 3: Validate HSN codes on all line items."""
    invoice = state.get("invoice_json")
    if not invoice or not invoice.line_items:
        return {"hsn_validations": []}

    try:
        db = get_supabase()
        validator = HSNValidator(db)
        validations = await validator.validate_all_line_items(invoice.line_items)
        return {"hsn_validations": validations}
    except Exception as e:
        logger.error(f"HSN validation failed: {e}")
        return {"hsn_validations": []}


async def reconcile_gstr2b(state: InvoiceAgentState) -> dict:
    """Node 4: Match invoice against GSTR-2B records."""
    invoice = state.get("invoice_json")
    if not invoice or not invoice.gstin_supplier:
        return {"gstr2b_match": GSTR2BMatchResult(status=GSTR2BMatchStatus.UNRECONCILED)}

    try:
        from app.services.supabase_client import get_gstr2b_records
        from datetime import date

        # Use invoice's own month/year for lookup (not today's date).
        # GSTR-2B is filed by the supplier for the period the invoice belongs to.
        lookup_month = None
        lookup_year = None
        if invoice.invoice_date:
            try:
                inv_date = date.fromisoformat(invoice.invoice_date)
                lookup_month = inv_date.month
                lookup_year = inv_date.year
            except (ValueError, TypeError):
                pass

        # Also try current month as fallback if invoice date parse failed
        if not lookup_month:
            now = date.today()
            lookup_month = now.month
            lookup_year = now.year

        # Try invoice month first, then current month if no records found
        raw_records = await get_gstr2b_records(state["trader_id"], lookup_month, lookup_year)
        if not raw_records and lookup_month != date.today().month:
            now = date.today()
            raw_records = await get_gstr2b_records(state["trader_id"], now.month, now.year)

        if not raw_records:
            return {"gstr2b_match": GSTR2BMatchResult(status=GSTR2BMatchStatus.UNRECONCILED)}

        # Convert to GSTR2BRecord objects
        records = []
        for r in raw_records:
            try:
                date_obj = date.fromisoformat(r["invoice_date"])
                records.append(GSTR2BRecord(
                    record_id=r["id"],
                    supplier_gstin=r.get("supplier_gstin", ""),
                    invoice_number=r.get("invoice_number", ""),
                    invoice_date=date_obj,
                    taxable_value=float(r.get("taxable_value") or 0),
                    igst=float(r.get("igst") or 0),
                    cgst=float(r.get("cgst") or 0),
                    sgst=float(r.get("sgst") or 0),
                    record_type=r.get("record_type", "B2B")
                ))
                records[-1].matched_invoice_id = r.get("matched_invoice_id")
            except (ValueError, KeyError):
                continue

        reconciler = GSTR2BReconciler()
        result = reconciler.match_invoice(
            supplier_gstin=invoice.gstin_supplier,
            invoice_number=invoice.invoice_number,
            invoice_date_str=invoice.invoice_date,
            total_amount=invoice.total_amount or 0,
            gstr2b_records=records,
        )

        return {"gstr2b_match": result}

    except Exception as e:
        logger.error(f"GSTR-2B reconciliation failed: {e}")
        return {"gstr2b_match": GSTR2BMatchResult(status=GSTR2BMatchStatus.UNRECONCILED)}


async def compute_itc(state: InvoiceAgentState) -> dict:
    """Node 5: Compute ITC eligibility using rules engine."""
    invoice = state.get("invoice_json")
    if not invoice:
        return {"itc_verdict": ITCVerdict(status=ITCStatus.FIXABLE_BLOCKED, reason="No invoice data")}

    engine = ITCRulesEngine()
    verdict = engine.compute_verdict(
        invoice=invoice,
        hsn_validations=state.get("hsn_validations", []),
        gstin_validation=state.get("gstin_validation"),
        gstr2b_match=state.get("gstr2b_match"),
    )
    return {"itc_verdict": verdict}


async def score_fraud(state: InvoiceAgentState) -> dict:
    """Node 6: Compute multi-variate fraud score."""
    invoice = state.get("invoice_json")
    if not invoice:
        return {"fraud_result": FraudResult()}

    # Pull historical data from DB for this supplier
    historical_amounts: list[float] = []
    supplier_invoice_numbers: list[str] = []
    try:
        db = get_supabase()
        if invoice.gstin_supplier:
            hist = db.table("invoices").select(
                "total_amount, invoice_number"
            ).eq("gstin_supplier", invoice.gstin_supplier).limit(100).execute()
            for row in (hist.data or []):
                if row.get("total_amount"):
                    historical_amounts.append(float(row["total_amount"]))
                if row.get("invoice_number"):
                    supplier_invoice_numbers.append(row["invoice_number"])
    except Exception as e:
        logger.warning(f"Could not load historical data for fraud scoring: {e}")

    scorer = FraudScorer()
    result = scorer.compute_fraud_score(
        invoice=invoice,
        gstin_validation=state.get("gstin_validation"),
        historical_amounts=historical_amounts,
        supplier_invoice_numbers=supplier_invoice_numbers,
    )

    # Override ITC verdict if fraud score is high
    if result.is_hard_flag:
        return {
            "fraud_result": result,
            "itc_verdict": ITCVerdict(
                status=ITCStatus.FRAUD_FLAGGED,
                itc_amount=0.0,
                itc_blocked=invoice.total_tax_amount or 0,
                reason=f"Fraud score {result.total_score}/100 — manual review required",
                fix_action="Verify invoice authenticity with your CA before claiming ITC",
            ),
        }

    return {"fraud_result": result}


async def generate_diagnosis(state: InvoiceAgentState) -> dict:
    """Node 7: Generate Hindi diagnosis message using Gemini."""
    invoice = state.get("invoice_json") or InvoiceJSON()
    verdict = state.get("itc_verdict") or ITCVerdict()
    fraud = state.get("fraud_result") or FraudResult()
    gstin_val = state.get("gstin_validation")

    # Build action items
    action_items = []
    if verdict.fix_action:
        action_items.append(verdict.fix_action)
    if fraud.is_hard_flag:
        action_items.append("CA se verify karwao pehle. ITC claim mat karo abhi.")
    if fraud.is_soft_flag:
        action_items.append("Invoice par dhyan rakhein — kuch suspicious signals hain.")

    # Prepare context for Gemini
    hsn_issues = "None"
    hsn_vals = state.get("hsn_validations", [])
    if hsn_vals:
        issues = [v for v in hsn_vals if v.rate_mismatch or not v.is_valid]
        if issues:
            hsn_issues = "; ".join(
                f"{v.hsn_code_extracted} → {v.suggestion or 'unknown'} (rate mismatch: {v.rate_mismatch})"
                for v in issues
            )

    supplier_flags = "None"
    gstin_status = "Valid" if (gstin_val and gstin_val.is_valid) else "Invalid/Unknown"

    fraud_signals = "None"
    if fraud.signals:
        triggered = [s for s in fraud.signals if s.triggered]
        if triggered:
            fraud_signals = "; ".join(f"{s.signal_name}: {s.detail}" for s in triggered)

    gstr2b_match = state.get("gstr2b_match")
    gstr2b_status = gstr2b_match.status.value if gstr2b_match else "Unreconciled"

    language_pref = "hi"
    try:
        from app.services.supabase_client import get_supabase
        db = get_supabase()
        trader_res = db.table("traders").select("language_pref").eq("id", state.get("trader_id")).execute()
        if trader_res.data and trader_res.data[0].get("language_pref"):
            language_pref = trader_res.data[0]["language_pref"]
    except Exception as e:
        logger.error(f"Failed to fetch language_pref: {e}")

    try:
        diagnosis_hi = await gemini.generate_hindi_diagnosis(
            supplier_name=invoice.supplier_name,
            total_amount=invoice.total_amount or 0,
            itc_status=verdict.status.value,
            itc_amount=verdict.itc_amount,
            itc_blocked=verdict.itc_blocked,
            block_reason=verdict.reason,
            fix_action=verdict.fix_action or "None",
            hsn_issues=hsn_issues,
            gstin_status=gstin_status,
            supplier_flags=supplier_flags,
            fraud_score=fraud.total_score,
            fraud_signals=fraud_signals,
            gstr2b_status=gstr2b_status,
            language_pref=language_pref,
        )
    except Exception as e:
        logger.error(f"Hindi diagnosis generation failed: {e}")
        diagnosis_hi = _fallback_diagnosis(invoice, verdict, fraud)

    elapsed = int((time.time() - state.get("start_time", time.time())) * 1000)

    return {
        "diagnosis_hi": diagnosis_hi,
        "diagnosis_en": verdict.reason,
        "action_items": action_items,
        "processing_duration_ms": elapsed,
    }


async def handle_error(state: InvoiceAgentState) -> dict:
    """Error recovery node — generates a helpful error message."""
    error = state.get("error", "Unknown error")
    diagnosis = (
        f"⚠️ Invoice process nahi ho paya.\n\n"
        f"Problem: {error}\n\n"
        f"Kya karein: Invoice ki photo dubara bhejo — achhi light mein, "
        f"poori invoice dikhni chahiye."
    )
    elapsed = int((time.time() - state.get("start_time", time.time())) * 1000)

    return {
        "diagnosis_hi": diagnosis,
        "diagnosis_en": f"Processing failed: {error}",
        "action_items": ["Resend a clearer photo of the invoice"],
        "processing_duration_ms": elapsed,
    }


def _fallback_diagnosis(invoice: InvoiceJSON, verdict: ITCVerdict, fraud: FraudResult) -> str:
    """Static fallback if Gemini is unavailable."""
    status_emoji = {
        ITCStatus.CONFIRMED: "✅",
        ITCStatus.FIXABLE_BLOCKED: "⚠️",
        ITCStatus.AT_RISK: "🚨",
        ITCStatus.MISSED: "💰",
        ITCStatus.INELIGIBLE: "🚫",
        ITCStatus.FRAUD_FLAGGED: "🚫",
    }
    emoji = status_emoji.get(verdict.status, "📄")

    msg = f"{emoji} Invoice: {invoice.supplier_name or 'Unknown'} | ₹{invoice.total_amount or 0:,.0f}\n\n"
    msg += f"ITC Status: {verdict.status.value}\n"
    msg += f"ITC Amount: ₹{verdict.itc_amount:,.0f}\n"

    if verdict.itc_blocked > 0:
        msg += f"Blocked: ₹{verdict.itc_blocked:,.0f}\n"
        msg += f"Reason: {verdict.reason}\n"

    if verdict.fix_action:
        msg += f"\n🔧 Fix: {verdict.fix_action}"

    if fraud.total_score > 0:
        msg += f"\n\nFraud Score: {fraud.total_score}/100"

    return msg


# --- Routing Functions ---

def route_after_extraction(state: InvoiceAgentState) -> str:
    """Route after extraction: error → handle_error, success → validate_gstin."""
    if state.get("error") or not state.get("invoice_json"):
        return "handle_error"
    return "validate_gstin"


def route_after_gstin(state: InvoiceAgentState) -> str:
    """Route after GSTIN: invalid GSTIN → generate_diagnosis (short-circuit), else → validate_hsn."""
    gstin_val = state.get("gstin_validation")
    if gstin_val and not gstin_val.is_valid:
        return "generate_diagnosis"
    return "validate_hsn"


# --- Build the Graph ---

def build_invoice_agent() -> StateGraph:
    """Construct the LangGraph invoice processing agent."""
    graph = StateGraph(InvoiceAgentState)

    # Add nodes
    graph.add_node("extract_entities", extract_entities)
    graph.add_node("validate_gstin", validate_gstin)
    graph.add_node("validate_hsn", validate_hsn)
    graph.add_node("reconcile_gstr2b", reconcile_gstr2b)
    graph.add_node("compute_itc", compute_itc)
    graph.add_node("score_fraud", score_fraud)
    graph.add_node("generate_diagnosis", generate_diagnosis)
    graph.add_node("handle_error", handle_error)

    # Set entry point
    graph.set_entry_point("extract_entities")

    # Conditional edge after extraction
    graph.add_conditional_edges(
        "extract_entities",
        route_after_extraction,
        {
            "handle_error": "handle_error",
            "validate_gstin": "validate_gstin",
        },
    )

    # Conditional edge after GSTIN validation
    graph.add_conditional_edges(
        "validate_gstin",
        route_after_gstin,
        {
            "generate_diagnosis": "generate_diagnosis",
            "validate_hsn": "validate_hsn",
        },
    )

    # Linear edges for the rest
    graph.add_edge("validate_hsn", "reconcile_gstr2b")
    graph.add_edge("reconcile_gstr2b", "compute_itc")
    graph.add_edge("compute_itc", "score_fraud")
    graph.add_edge("score_fraud", "generate_diagnosis")

    # Terminal edges
    graph.add_edge("generate_diagnosis", END)
    graph.add_edge("handle_error", END)

    return graph.compile()


# Singleton compiled agent
invoice_agent = build_invoice_agent()


async def process_invoice(
    trader_id: str,
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
) -> InvoiceDiagnosis:
    """
    Main entry point: process an invoice image through the full pipeline.
    Returns an InvoiceDiagnosis with all results.
    """
    initial_state: InvoiceAgentState = {
        "trader_id": trader_id,
        "media_url": None,
        "raw_image": image_bytes,
        "mime_type": mime_type,
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

    # Run the graph
    final_state = await invoice_agent.ainvoke(initial_state)

    return InvoiceDiagnosis(
        trader_id=trader_id,
        supplier_name=(final_state.get("invoice_json") or InvoiceJSON()).supplier_name,
        total_amount=(final_state.get("invoice_json") or InvoiceJSON()).total_amount,
        invoice_json=final_state.get("invoice_json"),
        itc_verdict=final_state.get("itc_verdict") or ITCVerdict(),
        hsn_validations=final_state.get("hsn_validations", []),
        gstin_validation=final_state.get("gstin_validation"),
        gstr2b_match=final_state.get("gstr2b_match"),
        fraud_result=final_state.get("fraud_result"),
        diagnosis_hi=final_state.get("diagnosis_hi", ""),
        diagnosis_en=final_state.get("diagnosis_en", ""),
        action_items=final_state.get("action_items", []),
        processing_duration_ms=final_state.get("processing_duration_ms", 0),
    )
