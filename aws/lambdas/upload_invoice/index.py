"""
munim-upload-invoice — API Gateway (REST, Lambda proxy integration) target
for POST /invoices.

Second, fully AWS-native trigger path into the same
Extract -> ComputeVerdict -> Explain -> Finalize pipeline that WhatsApp
inbound feeds -- this Lambda just writes the uploaded image to S3 under
the caller's trader prefix, and the existing S3 event notification takes
over unchanged. Exists so a demo (or any future integration) never
depends on WhatsApp/Meta's relay being up.

Two independent layers of access control, same shape as the WhatsApp
path: API Gateway's own API-key + usage-plan gate gets checked before
this code ever runs (rejects an unknown caller entirely, and caps
request rate/volume so a leaked key can't run up an unbounded bill), and
this Lambda separately checks the request's own trader_id against
munim-traders -- a valid API key does not by itself mean the trader_id
in the body is real. Fails closed on both checks and on any malformed
input: reject before writing anything to S3, never guess.
"""

import base64
import json
import logging
import re
import uuid

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
traders_table = dynamodb.Table("munim-traders")

INVOICES_BUCKET = "munim-invoices-0710-753654068031-ap-south-1-an"
MAX_UPLOAD_BYTES = 8 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "application/pdf": "pdf",
}

TRADER_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "Body must be valid JSON."})

    trader_id = str(body.get("trader_id", "")).strip()
    content_type = body.get("content_type", "")
    content_base64 = body.get("content_base64", "")

    if not TRADER_ID_PATTERN.fullmatch(trader_id):
        return _response(400, {"error": "trader_id is required and must be alphanumeric."})

    if not _is_registered_trader(trader_id):
        # Same reasoning as munim-whatsapp-inbound: a valid API key proves
        # the *caller* is trusted, not that the trader_id they supplied is
        # real. Reject before any S3 write / pipeline spend happens.
        logger.warning("Upload request for unregistered trader_id -- rejecting.")
        return _response(403, {"error": "trader_id is not a registered, active trader."})

    extension = ALLOWED_EXTENSIONS.get(content_type)
    if not extension:
        return _response(400, {"error": f"content_type must be one of {sorted(ALLOWED_EXTENSIONS)}."})

    try:
        file_bytes = base64.b64decode(content_base64, validate=True)
    except (ValueError, TypeError):
        return _response(400, {"error": "content_base64 is not valid base64."})

    if not file_bytes:
        return _response(400, {"error": "content_base64 decoded to zero bytes."})
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        return _response(413, {"error": f"File exceeds the {MAX_UPLOAD_BYTES} byte limit."})

    invoice_key = f"{trader_id}/{uuid.uuid4()}.{extension}"

    try:
        s3.put_object(
            Bucket=INVOICES_BUCKET,
            Key=invoice_key,
            Body=file_bytes,
            ContentType=content_type,
        )
    except ClientError:
        logger.exception("Failed to write uploaded invoice to S3.")
        return _response(502, {"error": "Could not store the invoice. Try again."})

    # Deliberately not logging trader_id/invoice_key beyond what's already
    # in this success message -- same discipline as the rest of the
    # pipeline: shape and outcome in logs, never content.
    logger.info("Wrote uploaded invoice to s3://%s/%s", INVOICES_BUCKET, invoice_key)

    return _response(202, {
        "invoice_id": invoice_key,
        "status": "RECEIVED",
        "message": "Invoice accepted, processing started.",
    })


def _is_registered_trader(trader_id):
    try:
        response = traders_table.get_item(Key={"trader_id": trader_id})
    except ClientError:
        logger.exception("Trader registry lookup failed -- treating as unregistered.")
        return False
    return response.get("Item", {}).get("status") == "active"


def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body_dict),
    }
