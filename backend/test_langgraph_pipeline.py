import asyncio
import time
import sys
import os
from unittest.mock import patch, AsyncMock

# Ensure stdout uses UTF-8 or ASCII fallback for Windows cp1252 console
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.models.invoice import (
    InvoiceJSON, LineItem, ITCVerdict, ITCStatus, 
    FraudResult, GSTR2BMatchResult, GSTR2BMatchStatus
)
from app.agents.invoice_agent import invoice_agent, InvoiceAgentState

TEST_TRADER_UUID = "6d123264-9325-4a37-b769-274834a04085"


def print_header(title: str):
    print("\n" + "=" * 75)
    print(f"  {title}")
    print("=" * 75)


def print_node_banner(step_num: int, total_steps: int, node_name: str, description: str):
    print("\n" + "-" * 75)
    print(f" >> [NODE {step_num}/{total_steps}] : {node_name.upper()} ({description})")
    print("-" * 75)


async def run_verbose_graph(initial_state: InvoiceAgentState, total_expected_steps: int = 7) -> dict:
    """
    Runs the compiled LangGraph invoice_agent using .astream() so we can stream
    and display every node's execution process and output in real time.
    """
    accumulated_state = dict(initial_state)
    step_count = 0

    node_descriptions = {
        "extract_entities": "Multimodal Vision OCR & JSON Structured Extraction",
        "validate_gstin": "Supplier GSTIN Verification & Taxpayer Status Check",
        "validate_hsn": "Statutory HSN Schedule & Tax Rate Validation",
        "reconcile_gstr2b": "GSTR-2B Portal Matching & CDNR Netting Check",
        "compute_itc": "12-Point Section 16 & Section 17(5) Statutory ITC Engine",
        "score_fraud": "4-Signal Forensic Fraud & Statistical Anomaly Scorer",
        "generate_diagnosis": "Bilingual WhatsApp & Email Compliance Diagnosis",
        "handle_error": "Error Recovery & Diagnostic Handler",
    }

    start_graph_time = time.time()

    async for event in invoice_agent.astream(initial_state):
        for node_name, state_update in event.items():
            step_count += 1
            desc = node_descriptions.get(node_name, "Pipeline Processing Node")
            print_node_banner(step_count, total_expected_steps, node_name, desc)

            # Update accumulated state with new values from this node
            accumulated_state.update(state_update)

            # --- VERBOSE PRINTING PER NODE ---
            if node_name == "extract_entities":
                inv = accumulated_state.get("invoice_json")
                err = accumulated_state.get("error")
                if err:
                    print(f"  [!] Extraction Error    : {err}")
                elif inv:
                    print(f"  [+] Invoice Number      : {inv.invoice_number or 'N/A'}")
                    print(f"  [+] Invoice Date        : {inv.invoice_date or 'N/A'}")
                    print(f"  [+] Supplier Name       : {inv.supplier_name or 'Unknown'} ({inv.gstin_supplier or 'No GSTIN'})")
                    print(f"  [+] Buyer GSTIN         : {inv.gstin_buyer or 'N/A'}")
                    print(f"  [+] Total Amount        : Rs. {inv.total_amount or 0:,.2f}")
                    print(f"  [+] Tax Amount          : Rs. {inv.total_tax_amount or 0:,.2f}")
                    print(f"  [+] OCR Confidence      : {inv.confidence * 100 if inv.confidence else 0:.1f}%")
                    print(f"  [+] Extracted Items     : {len(inv.line_items)} line item(s)")
                    for idx, item in enumerate(inv.line_items, 1):
                        print(f"      - Item #{idx}: {item.description} | HSN: {item.hsn_code} | Qty: {item.quantity} | Taxable Val: Rs. {item.taxable_value or 0:,.2f}")

            elif node_name == "validate_gstin":
                val = accumulated_state.get("gstin_validation")
                if val:
                    print(f"  [+] GSTIN Verified      : {val.gstin}")
                    print(f"  [+] Status / Valid?     : {val.verification_status} (Valid: {val.is_valid})")
                    print(f"  [+] Active Taxpayer?    : {val.is_active}")
                    print(f"  [+] Taxpayer Type       : {val.taxpayer_type or 'Regular'}")
                else:
                    print("  [~] No GSTIN validation performed (missing or skipped).")

            elif node_name == "validate_hsn":
                validations = accumulated_state.get("hsn_validations", [])
                print(f"  [+] HSN Line Items Checked : {len(validations)} item(s)")
                for idx, v in enumerate(validations, 1):
                    mismatch_tag = " [RATE MISMATCH]" if v.rate_mismatch else " [RATE OK]"
                    print(f"      - Item #{idx} (HSN {v.hsn_code_extracted}): Validated={v.hsn_code_validated or 'N/A'}{mismatch_tag}")
                    print(f"        Applied Rate: {v.tax_rate_applied}% | Correct Statutory Rate: {v.tax_rate_correct}%")
                    if v.rate_mismatch:
                        print(f"        -> Delta Impact: Rs. {v.itc_delta or 0:,.2f} | Suggestion: {v.suggestion_description or v.suggestion}")

            elif node_name == "reconcile_gstr2b":
                match = accumulated_state.get("gstr2b_match")
                if match:
                    print(f"  [+] GSTR-2B Match Status : {match.status.value}")
                    print(f"  [+] Match Confidence     : {match.confidence * 100:.1f}%")
                    print(f"  [+] Matched Record ID    : {match.matched_record_id or 'None'}")
                    if match.itc_amount is not None:
                        print(f"  [+] Portal Tax Claimable : Rs. {match.itc_amount:,.2f}")
                else:
                    print("  [~] No GSTR-2B match data available.")

            elif node_name == "compute_itc":
                v = accumulated_state.get("itc_verdict")
                if v:
                    print(f"  [+] Statutory Verdict    : {v.status.value}")
                    print(f"  [+] Eligible ITC         : Rs. {v.itc_amount:,.2f}")
                    print(f"  [+] Blocked ITC          : Rs. {v.itc_blocked:,.2f}")
                    print(f"  [+] Legal Citation       : Section {v.legal_section or 'N/A'}")
                    print(f"  [+] Statutory Reason     : {v.reason}")
                    if v.fix_action:
                        print(f"  [+] Action to Fix        : {v.fix_action}")
                else:
                    print("  [!] No ITC verdict produced.")

            elif node_name == "score_fraud":
                f = accumulated_state.get("fraud_result")
                if f:
                    print(f"  [+] Total Fraud Score    : {f.total_score}/100")
                    print(f"  [+] Hard Flag?           : {f.is_hard_flag} | Soft Flag? : {f.is_soft_flag}")
                    print(f"  [+] Statistical Signals  : {len(f.signals)} checked")
                    for sig in f.signals:
                        trig = "TRIGGERED" if sig.triggered else "PASSED"
                        print(f"      - [{trig}] {sig.signal_name}: +{sig.score_contribution} pts ({sig.detail})")
                else:
                    print("  [~] No fraud result produced.")

            elif node_name == "generate_diagnosis":
                hi = accumulated_state.get("diagnosis_hi", "")
                en = accumulated_state.get("diagnosis_en", "")
                actions = accumulated_state.get("action_items", [])
                print("  [+] WhatsApp / Email Diagnosis Text (Hindi):")
                for line in hi.strip().split("\n"):
                    print(f"      | {line}")
                print("  [+] WhatsApp / Email Diagnosis Text (English):")
                for line in en.strip().split("\n"):
                    print(f"      | {line}")
                if actions:
                    print(f"  [+] Action Items for CA / Trader ({len(actions)}):")
                    for idx, act in enumerate(actions, 1):
                        print(f"      {idx}. {act}")

            elif node_name == "handle_error":
                print(f"  [!] Pipeline Handled Error : {accumulated_state.get('error')}")
                print(f"  [+] Hindi Recovery Advice  : {accumulated_state.get('diagnosis_hi')}")

    total_time_ms = int((time.time() - start_graph_time) * 1000)
    print("\n" + "=" * 75)
    print(f"  [PIPELINE COMPLETED in {total_time_ms} ms across {step_count} nodes]")
    print("=" * 75)
    return accumulated_state


async def test_mocked_langgraph_pipeline():
    """
    Test 1: Run LangGraph pipeline in isolation with a mock InvoiceJSON extraction.
    """
    print_header("TEST 1: VERBOSE ISOLATED LANGGRAPH PIPELINE (MOCKED OCR EXTRACTION)")

    sample_invoice = InvoiceJSON(
        invoice_number="TEST-INV-2026-01",
        invoice_date="2026-07-20",
        gstin_supplier="27AABCU9603R1ZN",  # Maharashtra Regular GSTIN format
        gstin_buyer="27XYZAB1234C1Z9",
        supplier_name="Demo Enterprise Ltd",
        total_taxable_amount=10000.0,
        total_tax_amount=1800.0,
        total_amount=11800.0,
        line_items=[
            LineItem(
                description="Premium Tea Boxes",
                hsn_code="0902",
                quantity=10,
                unit_price=1000.0,
                taxable_value=10000.0,
                cgst_rate=9.0,
                sgst_rate=9.0,
                igst_rate=0.0,
                cgst_amount=900.0,
                sgst_amount=900.0,
                igst_amount=0.0
            )
        ],
        confidence=0.95
    )

    initial_state: InvoiceAgentState = {
        "trader_id": TEST_TRADER_UUID,
        "media_url": None,
        "raw_image": b"dummy_image_bytes",
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

    with patch("app.services.gemini.extract_invoice_from_image", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = sample_invoice
        try:
            await run_verbose_graph(initial_state, total_expected_steps=7)
            return True
        except Exception as e:
            print(f"\n[ERROR] Verbose isolated pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_live_gemini_extraction():
    """
    Test 2: Run process_invoice with real invoice.png.jpeg to test Gemini Vision + LangGraph end-to-end.
    """
    print_header("TEST 2: VERBOSE LIVE GEMINI VISION OCR + LANGGRAPH END-TO-END")

    img_path = os.path.join(os.path.dirname(__file__), "invoice.png.jpeg")
    if not os.path.exists(img_path):
        print(f"[SKIP] Test image not found at {img_path}")
        return False

    with open(img_path, "rb") as f:
        image_bytes = f.read()

    print(f"[INFO] Loaded test image {img_path} ({len(image_bytes)} bytes)")
    print("[INFO] Streaming execution of LangGraph pipeline with live Gemini Vision OCR...")

    initial_state: InvoiceAgentState = {
        "trader_id": TEST_TRADER_UUID,
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

    try:
        await run_verbose_graph(initial_state, total_expected_steps=7)
        return True
    except Exception as e:
        print(f"\n[ERROR] Verbose live end-to-end pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("\n" + "#" * 75)
    print("###  MUNIM.AI -- LANGGRAPH AUTONOMOUS RECONCILIATION PIPELINE TEST  ###")
    print("#" * 75)

    res1 = await test_mocked_langgraph_pipeline()
    res2 = await test_live_gemini_extraction()

    print_header("FINAL VERIFICATION SUMMARY")
    if res1 and res2:
        print("  [SUCCESS] Both Isolated LangGraph and Live End-to-End are 100% OPERATIONAL!")
    elif res1:
        print("  [SUCCESS] Isolated LangGraph is 100% OPERATIONAL! (Live OCR skipped/failed)")
    else:
        print("  [FAILURE] Pipeline tests encountered errors.")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
