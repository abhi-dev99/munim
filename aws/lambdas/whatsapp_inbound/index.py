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

Before fetching any media, the sender's phone number must exist in
munim-traders with status "active". WhatsApp Business numbers are
public -- without this check, any stranger who messages the number
would trigger a real GetWhatsAppMessageMedia call and a full
Textract + Bedrock run on our bill, with no registered trader to even
send the result to.
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
dynamodb = boto3.resource("dynamodb")
traders_table = dynamodb.Table("munim-traders")

INVOICES_BUCKET = "munim-invoices-0710-753654068031-ap-south-1-an"

# GetWhatsAppMessageMedia requires AWS's own "phone-number-id-..." form,
# but the webhook's metadata block carries Meta's numeric phone_number_id
# -- confirmed by a live ValidationException when the raw webhook value
# was passed through unmapped. Only one number is linked right now, so a
# static map is enough; look this up via list_linked_whatsapp_business_accounts
# instead if a second number is ever added.
META_TO_AWS_PHONE_NUMBER_ID = {
    "1361765560349695": "phone-number-id-8e342661ea254843aefec3783673c83a",
}

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

    aws_phone_number_id = META_TO_AWS_PHONE_NUMBER_ID.get(phone_number_id)
    if not aws_phone_number_id:
        logger.warning("Message %s from unmapped phone_number_id %s, can't fetch.", message_id, phone_number_id)
        return

    if not _is_registered_trader(sender):
        # Anyone can message a public WhatsApp Business number. Without this
        # check, a stranger's photo would still trigger a real
        # GetWhatsAppMessageMedia call and, once it lands in S3, a full
        # Textract + Bedrock run -- i.e. an unauthenticated sender spending
        # our AWS bill. Drop it before any paid API call happens.
        logger.warning("Message %s from unregistered sender -- dropping, not fetching media.", message_id)
        return

    extension = "pdf" if msg_type == "document" else "jpg"
    s3_key = f"{sender}/{message_id}.{extension}"

    try:
        social.get_whatsapp_message_media(
            mediaId=media_id,
            originationPhoneNumberId=aws_phone_number_id,
            destinationS3File={"bucketName": INVOICES_BUCKET, "key": s3_key},
        )
    except ClientError:
        logger.exception("Failed to fetch WhatsApp media %s for message %s.", media_id, message_id)
        return

    # Deliberately not logging sender/media details beyond IDs already
    # necessary for debugging -- same discipline as the rest of the
    # pipeline: shape and outcome in logs, never content.
    logger.info("Wrote inbound media for message %s to s3://%s/%s", message_id, INVOICES_BUCKET, s3_key)


def _is_registered_trader(sender):
    try:
        response = traders_table.get_item(Key={"trader_id": sender})
    except ClientError:
        # Fail closed: if we can't confirm registration, don't spend money
        # processing the message. A registry read error should never turn
        # into open-door processing for anyone who messages the number.
        logger.exception("Failed to look up trader %s in registry -- treating as unregistered.", sender)
        return False

    return response.get("Item", {}).get("status") == "active"
