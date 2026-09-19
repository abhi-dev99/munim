"""
Pings Bedrock on a schedule and records whether invocation is currently
allowed for this account, in a table other Lambdas can check.

Not a gate: meta_webhook/voice_handler/explain_verdict already have their
own try/except -> deterministic fallback, and keep working with this
Lambda entirely absent. This exists purely for visibility -- so nobody has
to manually re-test Bedrock every day to find out if AWS's account-level
eligibility gate (see local-notes/AWS_ROADMAP.md, 2026-09-19 entry) has
lifted.
"""
import datetime
import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MODEL_ID = os.environ.get("HEALTHCHECK_MODEL_ID", "apac.amazon.nova-micro-v1:0")
STATUS_TABLE = os.environ.get("STATUS_TABLE", "munim-system-status")

bedrock = boto3.client("bedrock-runtime")
dynamodb = boto3.resource("dynamodb")
status_table = dynamodb.Table(STATUS_TABLE)


def handler(event, context):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    available = False
    error_code = None
    error_message = None

    try:
        bedrock.converse(
            modelId=MODEL_ID,
            messages=[{"role": "user", "content": [{"text": "reply with one word: alive"}]}],
            inferenceConfig={"maxTokens": 8},
        )
        available = True
    except Exception as e:
        error_code = getattr(e, "response", {}).get("Error", {}).get("Code", type(e).__name__)
        error_message = getattr(e, "response", {}).get("Error", {}).get("Message", str(e))
        logger.warning("Bedrock healthcheck failed: %s -- %s", error_code, error_message)

    item = {
        "component": "bedrock",
        "available": available,
        "last_checked": now,
        "model_id": MODEL_ID,
    }
    if not available:
        item["last_error_code"] = error_code
        item["last_error_message"] = error_message[:500] if error_message else None

    status_table.put_item(Item=item)

    if available:
        logger.info("Bedrock is now available -- gate has lifted.")

    return {"available": available, "checked_at": now}
