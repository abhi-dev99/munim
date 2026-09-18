"""
munim-deadline-alerts -- EventBridge Scheduler target, cron 10:00 IST
on the 5th/10th/18th of each month.

Ports backend/app/main.py's `_send_deadline_alerts` job -- same day<=11
GSTR-1/11 vs GSTR-3B/20 split, same FIXABLE_BLOCKED/AT_RISK invoice
filter, same "only alert if the summed blocked+eligible amount across
those invoices is > 0" gate. Reads DynamoDB instead of Supabase, so
field names differ (itc_verdict.status / itc_verdict.itc_blocked /
itc_verdict.itc_amount here, vs a flat itc_status / itc_amount_blocked /
itc_amount_eligible column there) -- same logic, same thresholds,
different storage shape.

Sending is best-effort, deliberately not the point of this Lambda:
WhatsApp inbound is still blocked by an unexplained Meta-side relay
issue (see the roadmap), and outbound has never been tested against a
real number -- every trader currently in munim-traders is a test
identifier, not a real phone number. A send failure for one trader is
logged and doesn't stop the rest of the batch, and doesn't change
whether this Lambda did its actual job: correctly identifying who is
owed an alert and why, computed from real DynamoDB data with the real
backend's exact thresholds.
"""

import json
import logging
from datetime import date

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
traders_table = dynamodb.Table("munim-traders")
invoices_table = dynamodb.Table("munim-invoices")
social = boto3.client("socialmessaging")

ALERT_STATUSES = {"FIXABLE_BLOCKED", "AT_RISK"}

# Same number munim-whatsapp-inbound already maps Meta's phone_number_id
# to -- only one WhatsApp number is linked to this account.
AWS_PHONE_NUMBER_ID = "phone-number-id-8e342661ea254843aefec3783673c83a"
META_API_VERSION = "v21.0"


def handler(event, context):
    today = date.today()
    if today.day <= 11:
        filing_type, deadline_day = "GSTR-1", 11
    else:
        filing_type, deadline_day = "GSTR-3B", 20
    days_remaining = deadline_day - today.day

    alerted = 0
    skipped_no_channel = 0

    for trader in _active_traders():
        trader_id = trader["trader_id"]
        blocked_amount, flagged_count = _blocked_amount_for(trader_id)

        if blocked_amount <= 0:
            continue

        message = _build_message(filing_type, days_remaining, flagged_count, blocked_amount, deadline_day)
        logger.info(
            "ALERT trader=%s filing_type=%s flagged=%d blocked_amount=%.2f",
            trader_id, filing_type, flagged_count, blocked_amount,
        )

        if _looks_like_phone_number(trader_id):
            if _send_whatsapp(trader_id, message):
                alerted += 1
        else:
            # A test/S3-key-prefix identifier, not a real phone number --
            # correctly identified as owed an alert (logged above), just
            # nothing to send it to yet.
            skipped_no_channel += 1

    logger.info(
        "Deadline alert run complete: filing_type=%s alerted=%d skipped_no_channel=%d",
        filing_type, alerted, skipped_no_channel,
    )
    return {
        "filing_type": filing_type,
        "days_remaining": days_remaining,
        "alerted": alerted,
        "skipped_no_channel": skipped_no_channel,
    }


def _active_traders():
    response = traders_table.scan()
    items = response.get("Items", [])
    while "LastEvaluatedKey" in response:
        response = traders_table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))
    return [t for t in items if t.get("status") == "active"]


def _blocked_amount_for(trader_id):
    response = invoices_table.query(KeyConditionExpression=Key("trader_id").eq(trader_id))
    items = response.get("Items", [])
    while "LastEvaluatedKey" in response:
        response = invoices_table.query(
            KeyConditionExpression=Key("trader_id").eq(trader_id),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    total = 0.0
    count = 0
    for item in items:
        verdict = item.get("itc_verdict") or {}
        if verdict.get("status") not in ALERT_STATUSES:
            continue
        total += float(verdict.get("itc_blocked") or 0) + float(verdict.get("itc_amount") or 0)
        count += 1
    return total, count


def _build_message(filing_type, days_remaining, flagged_count, blocked_amount, deadline_day):
    return (
        f"Munim alert: {filing_type} is due on the {deadline_day}th "
        f"({days_remaining} din baaki). {flagged_count} invoice(s) me "
        f"Rs.{blocked_amount:,.0f} ka ITC abhi block/at-risk hai -- "
        f"Munim app me dekh lo, {filing_type} file karne se pehle fix ho "
        f"sakta hai."
    )


def _looks_like_phone_number(trader_id):
    return trader_id.isdigit() and 10 <= len(trader_id) <= 15


def _send_whatsapp(trader_id, message):
    payload = json.dumps({
        "messaging_product": "whatsapp",
        "to": trader_id,
        "type": "text",
        "text": {"body": message},
    }).encode("utf-8")
    try:
        social.send_whatsapp_message(
            originationPhoneNumberId=AWS_PHONE_NUMBER_ID,
            message=payload,
            metaApiVersion=META_API_VERSION,
        )
        return True
    except ClientError:
        logger.exception("Failed to send WhatsApp deadline alert -- logged above regardless, batch continues.")
        return False
