"""
munim-meta-webhook -- API Gateway (REST, Lambda proxy) target for
GET/POST /webhook, talking to Meta's WhatsApp Cloud API DIRECTLY.

Exists because AWS End User Messaging Social's own inbound relay
(WABA event destination -> SNS -> munim-whatsapp-inbound) is stuck:
every AWS-side setting is confirmed correct (event destination, SNS
subscription, IAM), yet zero events ever arrive from Meta, across
multiple real test messages over two days. Rather than keep waiting on
an unexplained third-party relay, this Lambda receives Meta's webhook
the same way the *existing* munim-ai FastAPI backend already does
successfully (via ngrok) -- ported from backend/app/api/webhook.py and
backend/app/services/whatsapp.py, same verification, same parsing,
same media-download flow, just registered against a new AWS URL
instead of an ngrok tunnel.

Deliberately does NOT port the real backend's one known bug: its
signature check fails OPEN if META_APP_SECRET is empty and
ENVIRONMENT=development (a documented P0 in that codebase). This
Lambda always attempts real HMAC verification -- an empty or wrong
secret fails CLOSED (every request rejected) rather than open.

GET handles Meta's one-time verification handshake. POST verifies
X-Hub-Signature-256 over the *raw* request body, checks the sender
against munim-traders (same anti-abuse gate as every other trigger
path in this pipeline), downloads the media directly from Meta's Graph
API, and writes it to the invoices bucket -- the existing S3 event
notification takes over from there, unchanged.
"""

import hashlib
import hmac
import json
import logging
import os
import re
import urllib.request
import uuid

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
traders_table = dynamodb.Table("munim-traders")

INVOICES_BUCKET = "munim-invoices-0710-753654068031-ap-south-1-an"

META_VERIFY_TOKEN = os.environ["META_VERIFY_TOKEN"]
META_APP_SECRET = os.environ.get("META_APP_SECRET", "")
META_WHATSAPP_TOKEN = os.environ["META_WHATSAPP_TOKEN"]
META_API_VERSION = os.environ.get("META_API_VERSION", "v21.0")
GRAPH_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"

NON_DIGIT = re.compile(r"\D")

EXTENSION_BY_MIME = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "application/pdf": "pdf",
}


def handler(event, context):
    method = event.get("httpMethod")
    if method == "GET":
        return _handle_verification(event)
    if method == "POST":
        return _handle_webhook_post(event)
    return {"statusCode": 405, "body": "Method not allowed"}


def _handle_verification(event):
    params = event.get("queryStringParameters") or {}
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge", "")

    if mode == "subscribe" and token == META_VERIFY_TOKEN:
        logger.info("Webhook verification succeeded.")
        return {"statusCode": 200, "headers": {"Content-Type": "text/plain"}, "body": challenge}

    logger.warning("Webhook verification failed -- bad mode or verify_token.")
    return {"statusCode": 403, "body": "Verification failed"}


def _handle_webhook_post(event):
    raw_body = event.get("body") or ""
    signature = _get_header(event, "x-hub-signature-256") or ""

    if not _verify_signature(raw_body, signature):
        logger.warning("Webhook signature verification failed -- rejecting.")
        return {"statusCode": 403, "body": "Invalid signature"}

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        logger.warning("Webhook body is not valid JSON -- rejecting.")
        return {"statusCode": 400, "body": "Invalid JSON"}

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                try:
                    _handle_message(message)
                except Exception:
                    # One malformed/unexpected message must never take
                    # the rest of the batch down -- same philosophy as
                    # every other Lambda in this pipeline.
                    logger.exception("Failed to process one inbound message.")

    # Meta expects a fast 200 regardless of downstream processing outcome,
    # or it will retry (and eventually stop sending events altogether).
    return {"statusCode": 200, "body": "OK"}


def _get_header(event, name):
    headers = event.get("headers") or {}
    name_lower = name.lower()
    for key, value in headers.items():
        if key.lower() == name_lower:
            return value
    return None


def _verify_signature(raw_body, signature):
    expected = hmac.new(META_APP_SECRET.encode("utf-8"), raw_body.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def _handle_message(message):
    sender = NON_DIGIT.sub("", message.get("from", "")) or "unknown"
    message_id = message.get("id", str(uuid.uuid4()))

    media = message.get("image") or message.get("document")
    if not media:
        logger.info("Inbound message has no media -- not an invoice, skipping.")
        return

    media_id = media.get("id")
    if not media_id:
        logger.warning("Media message %s missing media id, can't fetch.", message_id)
        return

    if not _is_registered_trader(sender):
        # Same reasoning as every other trigger path in this pipeline:
        # a stranger messaging the number must never cost us a Graph API
        # call plus a full Textract/Bedrock run downstream.
        logger.warning("Message %s from unregistered sender -- dropping, not fetching media.", message_id)
        return

    media_bytes, mime_type = _download_media(media_id)
    if media_bytes is None:
        return

    extension = EXTENSION_BY_MIME.get(mime_type, "jpg")
    s3_key = f"{sender}/{message_id}.{extension}"

    try:
        s3.put_object(Bucket=INVOICES_BUCKET, Key=s3_key, Body=media_bytes, ContentType=mime_type)
    except ClientError:
        logger.exception("Failed to write inbound media to S3 for message %s.", message_id)
        return

    logger.info("Wrote inbound media for message %s to s3://%s/%s", message_id, INVOICES_BUCKET, s3_key)


def _is_registered_trader(sender):
    try:
        response = traders_table.get_item(Key={"trader_id": sender})
    except ClientError:
        logger.exception("Failed to look up trader %s in registry -- treating as unregistered.", sender)
        return False
    return response.get("Item", {}).get("status") == "active"


def _download_media(media_id):
    headers = {"Authorization": f"Bearer {META_WHATSAPP_TOKEN}"}
    try:
        lookup_req = urllib.request.Request(f"{GRAPH_BASE_URL}/{media_id}", headers=headers)
        with urllib.request.urlopen(lookup_req, timeout=10) as response:
            media_meta = json.loads(response.read())

        download_url = media_meta["url"]
        mime_type = media_meta.get("mime_type", "image/jpeg")

        download_req = urllib.request.Request(download_url, headers=headers)
        with urllib.request.urlopen(download_req, timeout=15) as response:
            return response.read(), mime_type
    except Exception:
        logger.exception("Failed to download media %s from Meta's Graph API.", media_id)
        return None, None
