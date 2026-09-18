"""
munim-whatsapp-inbound — SNS trigger, fires on every inbound WhatsApp event
(messages, delivery statuses, etc.) once AWS End User Messaging Social
publishes them.

Only cares about one thing: a message carrying an image or document
(an invoice photo). For those, it asks AWS to write the media directly
into the invoices bucket via GetWhatsAppMessageMedia's `destinationS3File`
-- this Lambda never touches the raw bytes itself, AWS handles the
fetch-from-Meta-and-store-to-S3 step server-side. That upload is what
actually starts the real pipeline: the same S3 event notification that
already triggers munim-invoice-ingest fires the moment this write lands,
so nothing else has to change to connect WhatsApp to the existing
Extract -> ComputeVerdict -> Explain -> Finalize pipeline.

Text messages and status updates are deliberately no-ops for now --
conversational Q&A over WhatsApp isn't built in this AWS pipeline yet,
only the invoice-processing path.
"""

import json
import logging
import re
import uuid

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

social = boto3.client("socialmessaging")

INVOICES_BUCKET = "munim-invoices-0710-753654068031-ap-south-1-an"

# WhatsApp phone numbers in webhook payloads come with a leading "+" and
# no separators (e.g. "919136875481") -- strip anything that isn't a
# digit so the S3 key prefix is a clean, predictable trader identifier.
NON_DIGIT = re.compile(r"\D")


def handler(event, context):
    for record in event["Records"]:
        try:
            _handle_sns_record(record)
        except Exception:
            # One malformed/unexpected event must never take the rest of
            # the batch down with it -- log and move on, same philosophy
            # as every other Lambda in this pipeline.
            logger.exception("Failed to process one inbound WhatsApp SNS record.")

    return {"statusCode": 200}


def _handle_sns_record(record):
    body = json.loads(record["Sns"]["Message"])
    webhook_entry = json.loads(body["whatsAppWebhookEntry"])

    for entry in webhook_entry.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            # `phone_number_id` identifies which of our WhatsApp numbers
            # received this message -- Meta puts it in the webhook's
            # metadata block, not on the individual message object.
            # GetWhatsAppMessageMedia requires it explicitly, since a
            # media ID is only ever valid for the number that received it.
            phone_number_id = value.get("metadata", {}).get("phone_number_id")
            for message in value.get("messages", []):
                _handle_message(message, phone_number_id)


def _handle_message(message, phone_number_id):
    sender = NON_DIGIT.sub("", message.get("from", "")) or "unknown"
    message_id = message.get("id", str(uuid.uuid4()))
    msg_type = message.get("type")

    media = message.get("image") or message.get("document")
    if not media:
        logger.info("Inbound message type '%s' has no media -- not an invoice, skipping.", msg_type)
        return

    media_id = media.get("id")
    if not media_id or not phone_number_id:
        logger.warning("Media message %s missing media id or phone_number_id, can't fetch.", message_id)
        return

    extension = "pdf" if msg_type == "document" else "jpg"
    s3_key = f"{sender}/{message_id}.{extension}"

    try:
        social.get_whatsapp_message_media(
            mediaId=media_id,
            originationPhoneNumberId=phone_number_id,
            destinationS3File={"bucketName": INVOICES_BUCKET, "key": s3_key},
        )
    except ClientError:
        logger.exception("Failed to fetch WhatsApp media %s for message %s.", media_id, message_id)
        return

    # Deliberately not logging sender/media details beyond IDs already
    # necessary for debugging -- same discipline as the rest of the
    # pipeline: shape and outcome in logs, never content.
    logger.info("Wrote inbound media for message %s to s3://%s/%s", message_id, INVOICES_BUCKET, s3_key)
