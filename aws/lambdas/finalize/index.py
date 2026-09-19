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
import uuid
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])
traders_table = dynamodb.Table("munim-traders")
s3 = boto3.client("s3")
polly = boto3.client("polly")

META_WHATSAPP_TOKEN = os.environ.get("META_WHATSAPP_TOKEN", "")
META_PHONE_NUMBER_ID = os.environ.get("META_PHONE_NUMBER_ID", "")
META_API_VERSION = os.environ.get("META_API_VERSION", "v25.0")
GRAPH_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"
VOICE_BUCKET = os.environ.get("VOICE_BUCKET", "")

# Verified live via Polly describe-voices (see voice-handler): no hi-IN
# voice exists on its own, no mr-IN/gu-IN at all. "Kajal" is bilingual
# en-IN with hi-IN as an additional language. Marathi/Gujarati traders
# get text only -- not a bug, Polly genuinely cannot speak them.
VOICE_CAPABLE_LANGUAGES = {"en", "hi", "hi_dev"}

# compute-verdict never checks GSTR-2B reconciliation timing at all --
# every status here (CONFIRMED/FIXABLE_BLOCKED/INELIGIBLE/AT_RISK/
# FRAUD_FLAGGED) is a determination about the invoice itself (missing
# fields, invalid GSTIN, blocked HSN category, 16(4) time limit, 180-day
# payment-age proviso, fraud signals) -- so every non-CONFIRMED status
# here is a genuine invoice-level issue worth flagging, not upstream
# filing-timing noise.
_STATUS_OK = {"CONFIRMED"}

# The rules engine's own `reason`/`fix_action` strings are English,
# legalistic, and were never meant to be read raw by a trader -- an
# earlier version of this Lambda just inserted them directly, which is
# unusable for a low-literacy trader regardless of what language wrapper
# surrounds them. These are genuinely simple, pre-written sentences per
# category, not translations of the technical text. Matched by the
# stable English substrings compute-verdict actually emits (grepped
# directly from its source, not guessed) since status+legal_section
# alone doesn't disambiguate every case cleanly.
_SIMPLE_MESSAGES = {
    "missing_gstin": {
        "hi": "Bill mein dukaandar ka GST number nahi hai. Unse sahi bill mangwao.",
        "hi_dev": "बिल में दुकानदार का जीएसटी नंबर नहीं है। उनसे सही बिल मंगवाएं।",
        "en": "This bill is missing the seller's GST number. Ask them for a correct bill.",
        "mr": "बिलावर दुकानदाराचा जीएसटी नंबर नाही. त्यांच्याकडून योग्य बिल मागवा.",
        "gu": "બિલ પર દુકાનદારનો જીએસટી નંબર નથી. તેમની પાસેથી સાચું બિલ મંગાવો.",
    },
    "unregistered_dealer": {
        "hi": "Yeh dukaandar GST mein register nahi hai, isliye is bill par tax credit nahi milega.",
        "hi_dev": "यह दुकानदार जीएसटी में रजिस्टर नहीं है, इसलिए इस बिल पर टैक्स क्रेडिट नहीं मिलेगा।",
        "en": "This seller isn't GST-registered, so there's no tax credit on this bill.",
        "mr": "हा दुकानदार जीएसटीमध्ये नोंदणीकृत नाही, त्यामुळे या बिलावर कर सवलत मिळणार नाही.",
        "gu": "આ દુકાનદાર જીએસટીમાં નોંધાયેલ નથી, તેથી આ બિલ પર કોઈ ટેક્સ ક્રેડિટ નહીં મળે.",
    },
    "missing_fields": {
        "hi": "Bill mein kuch zaroori jaankari missing hai. Dukaandar se poora bill mangwao.",
        "hi_dev": "बिल में कुछ ज़रूरी जानकारी नहीं है। दुकानदार से पूरा बिल मंगवाएं।",
        "en": "This bill is missing some required details. Ask the seller for a complete bill.",
        "mr": "बिलावर काही आवश्यक माहिती नाही. दुकानदाराकडून पूर्ण बिल मागवा.",
        "gu": "બિલ પર કેટલીક જરૂરી માહિતી નથી. દુકાનદાર પાસેથી પૂરું બિલ મંગાવો.",
    },
    "time_expired": {
        "hi": "Is bill ka time nikal gaya hai, ab iska tax credit nahi le sakte.",
        "hi_dev": "इस बिल का समय निकल गया है, अब इसका टैक्स क्रेडिट नहीं ले सकते।",
        "en": "The time limit for this bill has passed -- its tax credit can no longer be claimed.",
        "mr": "या बिलाची वेळ निघून गेली आहे, आता याचा कर क्रेडिट घेता येणार नाही.",
        "gu": "આ બિલનો સમય પૂરો થઈ ગયો છે, હવે તેનો ટેક્સ ક્રેડિટ લઈ શકાશે નહીં.",
    },
    "payment_age": {
        "hi": "Yeh bill 180 din se purana hai. Check karo ki dukaandar ko payment ho chuka hai ya nahi.",
        "hi_dev": "यह बिल 180 दिन से पुराना है। चेक करें कि दुकानदार को भुगतान हो चुका है या नहीं।",
        "en": "This bill is over 180 days old. Please check whether payment to the seller has been made.",
        "mr": "हे बिल 180 दिवसांपेक्षा जुने आहे. दुकानदाराला पेमेंट झाले आहे का ते तपासा.",
        "gu": "આ બિલ 180 દિવસથી જૂનું છે. દુકાનદારને પેમેન્ટ થયું છે કે નહીં તે તપાસો.",
    },
    "bad_hsn": {
        "hi": "Bill mein item ka code sahi nahi lag raha. Dukaandar se check karwao.",
        "hi_dev": "बिल में आइटम का कोड सही नहीं लग रहा। दुकानदार से चेक करवाएं।",
        "en": "The item code on this bill doesn't look right. Please get it checked with the seller.",
        "mr": "बिलावरील वस्तूचा कोड बरोबर वाटत नाही. दुकानदाराकडून तपासून घ्या.",
        "gu": "બિલ પરનો વસ્તુનો કોડ સાચો લાગતો નથી. દુકાનદાર પાસે ચેક કરાવો.",
    },
    "blocked_category": {
        "hi": "Is tarah ki kharidari par tax credit nahi milta.",
        "hi_dev": "इस तरह की खरीदारी पर टैक्स क्रेडिट नहीं मिलता।",
        "en": "Tax credit isn't allowed on this type of purchase.",
        "mr": "अशा प्रकारच्या खरेदीवर कर क्रेडिट मिळत नाही.",
        "gu": "આ પ્રકારની ખરીદી પર ટેક્સ ક્રેડિટ મળતો નથી.",
    },
    "fraud": {
        "hi": "Is bill mein kuch gadbad lag rahi hai. Apne CA se turant baat karo.",
        "hi_dev": "इस बिल में कुछ गड़बड़ लग रही है। अपने सीए से तुरंत बात करें।",
        "en": "Something looks off with this bill. Please talk to your CA right away.",
        "mr": "या बिलात काहीतरी गडबड वाटते. लगेच तुमच्या सीएशी बोला.",
        "gu": "આ બિલમાં કંઈક ગડબડ લાગે છે. તરત તમારા સીએ સાથે વાત કરો.",
    },
    "generic": {
        "hi": "Is bill mein ek dikkat mili hai. Apne CA se check karwao.",
        "hi_dev": "इस बिल में एक समस्या मिली है। अपने सीए से चेक करवाएं।",
        "en": "There's an issue with this bill. Please get it checked with your CA.",
        "mr": "या बिलात एक समस्या आढळली आहे. तुमच्या सीएकडून तपासून घ्या.",
        "gu": "આ બિલમાં એક સમસ્યા મળી છે. તમારા સીએ પાસે ચેક કરાવો.",
    },
}


def _simple_message(status, reason, lang):
    """Picks a genuinely simple, pre-written sentence for the trader --
    never the rules engine's own English text, in any language."""
    if status == "FRAUD_FLAGGED":
        key = "fraud"
    else:
        reason = reason or ""
        if "GSTIN is missing" in reason:
            key = "missing_gstin"
        elif "Unregistered Dealer" in reason:
            key = "unregistered_dealer"
        elif "missing required fields" in reason:
            key = "missing_fields"
        elif "time limit expired" in reason:
            key = "time_expired"
        elif ">180 days old" in reason:
            key = "payment_age"
        elif "not found in the GST master list" in reason:
            key = "bad_hsn"
        elif "blocked category" in reason or "Section 17(5)" in reason:
            key = "blocked_category"
        else:
            key = "generic"
    bucket = _SIMPLE_MESSAGES[key]
    return bucket.get(lang, bucket["hi"])


_VERDICT_OK_TEMPLATE = {
    "hi": "Invoice check ho gaya! ✅\n\nEligible ITC: Rs.{amount}",
    "hi_dev": "इनवॉइस जांच पूरी! ✅\n\nयोग्य ITC: Rs.{amount}",
    "en": "Invoice checked! ✅\n\nEligible ITC: Rs.{amount}",
    "mr": "इनव्हॉइस तपासले! ✅\n\nपात्र ITC: Rs.{amount}",
    "gu": "ઇનવોઇસ ચેક થયું! ✅\n\nપાત્ર ITC: Rs.{amount}",
}

_VERDICT_ISSUE_TEMPLATE = {
    "hi": "Invoice mein dikkat hai ⚠️\n\n{message}",
    "hi_dev": "इनवॉइस में समस्या है ⚠️\n\n{message}",
    "en": "There's an issue with this invoice ⚠️\n\n{message}",
    "mr": "इनव्हॉइसमध्ये समस्या आहे ⚠️\n\n{message}",
    "gu": "ઇનવોઇસમાં સમસ્યા છે ⚠️\n\n{message}",
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
        message = _simple_message(status, verdict.get("reason", ""), lang)
        template = _VERDICT_ISSUE_TEMPLATE.get(lang, _VERDICT_ISSUE_TEMPLATE["hi"])
        text = template.format(message=message)

    _send_text(trader_id, text)

    # Voice too, not just a simplified text -- a genuinely illiterate
    # trader can't use text regardless of language or how simple the
    # wording is. Best-effort: text has already gone out above, so a
    # voice failure here never leaves the trader with nothing.
    if lang in VOICE_CAPABLE_LANGUAGES and VOICE_BUCKET:
        _send_voice(trader_id, lang, text)


def _send_text(trader_id, text):
    body = json.dumps({
        "messaging_product": "whatsapp",
        "to": trader_id,
        "type": "text",
        "text": {"body": text},
    }).encode("utf-8")
    _graph_post_messages(trader_id, body)


def _send_voice(trader_id, lang, text):
    try:
        response = polly.synthesize_speech(
            Text=text,
            OutputFormat="mp3",
            VoiceId="Kajal",
            Engine="neural",
            LanguageCode="hi-IN" if lang in ("hi", "hi_dev") else "en-IN",
        )
        audio_bytes = response["AudioStream"].read()
        key = f"voice-replies/{trader_id}/{uuid.uuid4()}.mp3"
        s3.put_object(Bucket=VOICE_BUCKET, Key=key, Body=audio_bytes, ContentType="audio/mpeg")
        presigned_url = s3.generate_presigned_url("get_object", Params={"Bucket": VOICE_BUCKET, "Key": key}, ExpiresIn=1800)
        body = json.dumps({
            "messaging_product": "whatsapp",
            "to": trader_id,
            "type": "audio",
            "audio": {"link": presigned_url},
        }).encode("utf-8")
        _graph_post_messages(trader_id, body)
    except Exception:
        logger.exception("Voice notification failed for %s (non-fatal, text already sent).", trader_id)


def _graph_post_messages(trader_id, body):
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
