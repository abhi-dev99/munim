"""
munim-explain-verdict — Step Functions task Lambda.

The second of the product's exactly-two LLM jobs: rephrase an
already-computed verdict in plain language. Bedrock never sees line items
or amounts beyond what's already in the verdict, and never influences
itc_verdict/fraud_result -- those come entirely from munim-compute-verdict,
upstream and untouched here.

Model: Amazon Nova Micro, not Claude -- picked deliberately, not out of
default familiarity. This is a one-sentence rephrase of already-decided
structured data, zero multi-step reasoning required, and Nova Micro is
roughly two orders of magnitude cheaper per token than Claude Haiku while
being explicitly trained with strong Hindi proficiency (AWS's own
Flores200 benchmarks) -- the one quality axis that actually matters for
this specific call. Using Bedrock's unified Converse API rather than a
model-specific request body, so swapping models later is an env var
change, not a rewrite.

Falls back to the deterministic `reason` string the rules engine already
produced (not a generic error) on any Bedrock failure -- model access not
granted, throttling, whatever.
"""

import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock = boto3.client("bedrock-runtime")

MODEL_ID = os.environ.get("EXPLAIN_MODEL_ID", "amazon.nova-micro-v1:0")


def handler(event, context):
    verdict = event.get("itc_verdict", {})
    fraud = event.get("fraud_result", {})

    fallback = verdict.get("reason", "Unable to process this invoice.")
    if verdict.get("fix_action"):
        fallback = f"{fallback} {verdict['fix_action']}"

    prompt = (
        "You explain GST input-tax-credit decisions to Indian shopkeepers "
        "who are not accountants. Write ONE short, plain sentence in "
        "simple Hindi-English (Hinglish) -- no legal jargon, no section "
        "numbers spelled out in the sentence itself.\n\n"
        f"Status: {verdict.get('status')}\n"
        f"ITC eligible: Rs.{verdict.get('itc_amount', 0)}\n"
        f"ITC blocked: Rs.{verdict.get('itc_blocked', 0)}\n"
        f"Reason: {verdict.get('reason')}\n"
        f"What to do: {verdict.get('fix_action') or 'Nothing needed.'}\n"
        f"Fraud flag: {'yes' if fraud.get('is_hard_flag') else 'no'}"
    )

    try:
        response = bedrock.converse(
            modelId=MODEL_ID,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 150},
        )
        explanation = response["output"]["message"]["content"][0]["text"].strip()
    except ClientError as e:
        # Most likely cause right now: Bedrock model access not yet
        # granted for this account (a one-time console step, separate
        # from IAM) -- see local-notes/AWS_ROADMAP.md §0. Any other
        # Bedrock failure degrades the same way: never block the
        # pipeline on the explanation step, only on the verdict itself.
        logger.warning("Bedrock explain failed (%s), using deterministic fallback.", e.response.get("Error", {}).get("Code"))
        explanation = fallback
    except Exception:
        logger.exception("Unexpected error calling Bedrock, using deterministic fallback.")
        explanation = fallback

    return {**event, "explanation": explanation, "explanation_model": MODEL_ID}
