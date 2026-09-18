"""
munim-invoice-ingest — S3 trigger.

Simplified from its original shape: this used to also call Textract
inline. Now it only does the two things that must happen the instant a
file lands (record it exists, idempotently; kick off the real pipeline)
and hands everything else to the Step Functions state machine, which is
where the actual per-node Lambdas (extract, compute-verdict, explain,
finalize) now live -- matching the architecture thesis: the pipeline is
a state machine, not a monolithic function.
"""

import logging
import os
import urllib.parse

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])
sfn = boto3.client("stepfunctions")

STATE_MACHINE_ARN = os.environ["STATE_MACHINE_ARN"]


def handler(event, context):
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        size = record["s3"]["object"].get("size", 0)

        trader_id = key.split("/")[0] if "/" in key else "unassigned"
        invoice_id = key

        try:
            table.put_item(
                Item={
                    "trader_id": trader_id,
                    "invoice_id": invoice_id,
                    "s3_bucket": bucket,
                    "s3_key": key,
                    "size_bytes": size,
                    "status": "RECEIVED",
                    "received_at": _now_iso(),
                },
                ConditionExpression="attribute_not_exists(invoice_id)",
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                logger.info("Duplicate delivery for %s, already ingested — skipping.", invoice_id)
                continue
            raise

        sfn.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            # Execution names must be unique per state machine; the S3 key
            # already is (see the finalize/compute-verdict Lambdas' own
            # idempotency reasoning) but Step Functions' name charset is
            # narrower than S3's, so unsafe characters are swapped out
            # rather than risking a StartExecution failure on a real
            # filename.
            name=_safe_execution_name(invoice_id),
            input=_json_dumps({"bucket": bucket, "key": key, "trader_id": trader_id, "invoice_id": invoice_id}),
        )

    return {"statusCode": 200}


def _safe_execution_name(invoice_id):
    import re

    safe = re.sub(r"[^a-zA-Z0-9\-_]", "-", invoice_id)
    return safe[:80]


def _json_dumps(obj):
    import json

    return json.dumps(obj)


def _now_iso():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
