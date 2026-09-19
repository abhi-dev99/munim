"""munim-finalize-invoice — last Step Functions task: persist the pipeline's
output, then notify the trader over WhatsApp. Conditional update, same
reasoning as the ingest Lambda: safe to retry, never a duplicate/lost write.

The notify step was missing entirely until 2026-09-20 -- the whole
invoice-photo pipeline (ingest -> extract -> compute-verdict ->
explain-verdict -> finalize) processed and stored verdicts correctly but
never told the trader anything came back. Confirmed live: a real invoice
sent to the newly-registered WhatsApp number produced a fully correct
DynamoDB verdict and zero reply. Fixed here, not upstream, since this is
the one step that already has the finished verdict in hand.
"""

import json
import logging
import os
import urllib.error
import urllib.request
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])
traders_table = dynamodb.Table("munim-traders")

META_WHATSAPP_TOKEN = os.environ.get("META_WHATSAPP_TOKEN", "")
META_PHONE_NUMBER_ID = os.environ.get("META_PHONE_NUMBER_ID", "")
META_API_VERSION = os.environ.get("META_API_VERSION", "v25.0")
GRAPH_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"

_VERDICT_TEMPLATE = {
    "hi": "Invoice check ho gaya!\n\nStatus: {status}\n{explanation}",
    "hi_dev": "इनवॉइस जांच पूरी हुई!\n\nस्टेटस: {status}\n{explanation}",
    "en": "Invoice checked!\n\nStatus: {status}\n{explanation}",
    "mr": "इनव्हॉइस तपासले!\n\nस्टेटस: {status}\n{explanation}",
    "gu": "ઇનવોઇસ ચેક થયું!\n\nસ્ટેટસ: {status}\n{explanation}",
}


def _to_dynamo_safe(value):
    """boto3's Table resource rejects native float outright ("Float types
    are not supported. Use Decimal types instead.") -- recursively convert
    every float in a nested dict/list to Decimal via its string repr
    (never via Decimal(float) directly, which would bake in float's own
    binary-representation error on financial amounts)."""
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: _to_dynamo_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_dynamo_safe(v) for v in value]
    return value


def handler(event, context):
    trader_id = event["trader_id"]
    invoice_id = event["invoice_id"]
    status = event.get("itc_verdict", {}).get("status", "UNKNOWN")
    explanation = event.get("explanation", "")

    try:
        table.update_item(
            Key={"trader_id": trader_id, "invoice_id": invoice_id},
            ConditionExpression="attribute_exists(invoice_id)",
            UpdateExpression=(
                "SET #s = :status, itc_verdict = :itc, fraud_result = :fraud, "
                "explanation = :explanation, gstin_supplier = :gstin, "
                "finalized_at = :ts"
            ),
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":status": status,
                ":itc": _to_dynamo_safe(event.get("itc_verdict", {})),
                ":fraud": _to_dynamo_safe(event.get("fraud_result", {})),
                ":explanation": explanation,
                ":gstin": event.get("gstin_supplier"),
                ":ts": _now_iso(),
            },
        )
    except ClientError as e:
        if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise

    _notify_trader(trader_id, status, explanation)

    return {"trader_id": trader_id, "invoice_id": invoice_id, "final_status": status}


def _notify_trader(trader_id, status, explanation):
    # Never let a notification failure undo the fact that the verdict is
    # already durably stored -- same resilience philosophy as the rest of
    # this pipeline. Worst case: the trader has to ask for their status
    # instead of getting it pushed, which meta-webhook's ITC-status intent
    # already answers correctly and deterministically.
    if not META_WHATSAPP_TOKEN or not META_PHONE_NUMBER_ID:
        logger.warning("WhatsApp not configured, skipping trader notification.")
        return

    lang = "hi"
    try:
        response = traders_table.get_item(Key={"trader_id": trader_id})
        lang = response.get("Item", {}).get("language_pref", "hi")
    except ClientError:
        logger.warning("Couldn't read trader language preference, defaulting to hi.")

    template = _VERDICT_TEMPLATE.get(lang, _VERDICT_TEMPLATE["hi"])
    text = template.format(status=status, explanation=explanation or "")

    body = json.dumps({
        "messaging_product": "whatsapp",
        "to": trader_id,
        "type": "text",
        "text": {"body": text},
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{GRAPH_BASE_URL}/{META_PHONE_NUMBER_ID}/messages",
        data=body,
        headers={"Authorization": f"Bearer {META_WHATSAPP_TOKEN}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=15)
    except urllib.error.HTTPError as e:
        try:
            error_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            error_body = "<could not read body>"
        logger.error("Failed to notify trader %s: HTTP %s -- %s", trader_id, e.code, error_body)
    except Exception:
        logger.exception("Failed to notify trader %s.", trader_id)


def _now_iso():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
