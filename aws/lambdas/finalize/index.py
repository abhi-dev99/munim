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
import re
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

# compute-verdict never checks GSTR-2B reconciliation timing at all --
# every status here (CONFIRMED/FIXABLE_BLOCKED/INELIGIBLE/AT_RISK/
# FRAUD_FLAGGED) is a determination about the invoice itself (missing
# fields, invalid GSTIN, blocked HSN category, 16(4) time limit, 180-day
# payment-age proviso, fraud signals) -- so every non-CONFIRMED status
# here is a genuine invoice-level issue worth flagging, not upstream
# filing-timing noise. Explicit instruction: plain language, amount
# first, only flag real problems -- no legal jargon for the trader.
_STATUS_OK = {"CONFIRMED"}

_SECTION_CITATION_RE = re.compile(r"\s*\([^)]*[Ss]ection[^)]*\)")


def _plain_reason(reason):
    """Strips legal-citation parentheticals for the trader-facing
    message -- the raw reason (with citation) still gets stored in
    DynamoDB and used by explain-verdict/meta-webhook internally. A
    trader doesn't need "(Section 16(2) 2nd Proviso)" to understand
    there's a problem."""
    return _SECTION_CITATION_RE.sub("", reason or "").strip()


_VERDICT_OK_TEMPLATE = {
    "hi": "Invoice check ho gaya! ✅\n\nEligible ITC: Rs.{amount}",
    "hi_dev": "इनवॉइस जांच पूरी! ✅\n\nयोग्य ITC: Rs.{amount}",
    "en": "Invoice checked! ✅\n\nEligible ITC: Rs.{amount}",
    "mr": "इनव्हॉइस तपासले! ✅\n\nपात्र ITC: Rs.{amount}",
    "gu": "ઇનવોઇસ ચેક થયું! ✅\n\nપાત્ર ITC: Rs.{amount}",
}

_VERDICT_ISSUE_TEMPLATE = {
    "hi": "Invoice mein dikkat hai ⚠️\n\n{reason}\n{fix_line}",
    "hi_dev": "इनवॉइस में समस्या है ⚠️\n\n{reason}\n{fix_line}",
    "en": "There's an issue with this invoice ⚠️\n\n{reason}\n{fix_line}",
    "mr": "इनव्हॉइसमध्ये समस्या आहे ⚠️\n\n{reason}\n{fix_line}",
    "gu": "ઇનવોઇસમાં સમસ્યા છે ⚠️\n\n{reason}\n{fix_line}",
}

_FIX_LABEL = {
    "hi": "Kya karein: ",
    "hi_dev": "क्या करें: ",
    "en": "What to do: ",
    "mr": "काय करावे: ",
    "gu": "શું કરવું: ",
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
    verdict = event.get("itc_verdict", {})
    status = verdict.get("status", "UNKNOWN")
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

    _notify_trader(trader_id, verdict)

    return {"trader_id": trader_id, "invoice_id": invoice_id, "final_status": status}


def _notify_trader(trader_id, verdict):
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

    status = verdict.get("status", "UNKNOWN")
    if status in _STATUS_OK:
        amount = verdict.get("itc_amount", 0)
        template = _VERDICT_OK_TEMPLATE.get(lang, _VERDICT_OK_TEMPLATE["hi"])
        text = template.format(amount=amount)
    else:
        reason = _plain_reason(verdict.get("reason", "")) or "Please check this invoice."
        fix_action = verdict.get("fix_action")
        fix_line = f"{_FIX_LABEL.get(lang, _FIX_LABEL['hi'])}{fix_action}" if fix_action else ""
        template = _VERDICT_ISSUE_TEMPLATE.get(lang, _VERDICT_ISSUE_TEMPLATE["hi"])
        text = template.format(reason=reason, fix_line=fix_line).strip()

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
