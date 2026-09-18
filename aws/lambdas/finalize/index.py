"""munim-finalize-invoice — last Step Functions task: persist the pipeline's
output. Conditional update, same reasoning as the ingest Lambda: safe to
retry, never a duplicate/lost write."""

import os
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


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
                ":status": event.get("itc_verdict", {}).get("status", "UNKNOWN"),
                ":itc": _to_dynamo_safe(event.get("itc_verdict", {})),
                ":fraud": _to_dynamo_safe(event.get("fraud_result", {})),
                ":explanation": event.get("explanation", ""),
                ":gstin": event.get("gstin_supplier"),
                ":ts": _now_iso(),
            },
        )
    except ClientError as e:
        if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise

    return {"trader_id": trader_id, "invoice_id": invoice_id, "final_status": event.get("itc_verdict", {}).get("status", "UNKNOWN")}


def _now_iso():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
