"""
munim-extract-invoice — Step Functions task Lambda.

Textract's AnalyzeExpense is a generic invoice/receipt extractor -- it has
no concept of a GSTIN, because it wasn't built for Indian GST specifically
(unlike the current Gemini-based extraction, which is prompted explicitly
to pull one out). So GSTIN comes from a second pass: a regex over every
line of text Textract detected, since the GSTIN appears somewhere in the
document even though Textract doesn't label it as a semantic field.
"""

import logging
import re
import time
import urllib.parse

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
textract = boto3.client("textract")

MAX_INLINE_BYTES = 5 * 1024 * 1024
MAX_TEXTRACT_ATTEMPTS = 4
BACKOFF_BASE_SECONDS = 1.5

# 2-digit state code + 10-char PAN (5 letters, 4 digits, 1 letter) + 1
# entity code (digit or letter) + literal 'Z' + 1 checksum char = 15 total.
# (An earlier version of this pattern had an extra [A-Z] group before the
# 'Z', requiring 16 characters -- it never matched a real GSTIN at all,
# on either this native-field path or the raw-text fallback below, since
# both use this same pattern. Caught by testing against a real invoice,
# not by inspection.)
GSTIN_PATTERN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]\b")


def handler(event, context):
    bucket = event["bucket"]
    key = event["key"]

    file_bytes = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    if len(file_bytes) > MAX_INLINE_BYTES:
        return {**event, "extraction_status": "TOO_LARGE_FOR_SYNC_EXTRACT", "extracted_fields": {}, "line_items": [], "gstin_supplier": None}

    response = _call_textract_with_retry(file_bytes, event.get("invoice_id", key))
    if response is None:
        return {**event, "extraction_status": "EXTRACT_FAILED", "extracted_fields": {}, "line_items": [], "gstin_supplier": None}

    fields = _parse_summary_fields(response)
    line_items = _parse_line_items(response)

    # Textract's AnalyzeExpense turns out to have native GST awareness after
    # all -- TAX_PAYER_ID/VENDOR_GST_NUMBER are real fields it returns when
    # it recognizes one, semantically labeled and higher-confidence than a
    # blind regex scan. Prefer those; fall back to the regex sweep over all
    # detected text only when Textract didn't surface any. Scanned from the
    # raw response, not the deduped `fields` dict above -- a real invoice
    # can carry two distinct GSTINs (supplier's and the buyer's) both
    # labeled the same field type, and a dict keyed by field type can only
    # ever keep the last one, silently dropping the other.
    gstins = _find_native_gstins(response) or _find_gstins(response)

    # Two GSTINs found (buyer + supplier) is the common case; one found is
    # ambiguous but still usable as the supplier's -- most invoices show
    # the supplier's GSTIN more prominently near the header than the
    # buyer's. Zero found is a real, honest gap the ITC engine already
    # handles as a defective/URD invoice, not a crash.
    gstin_supplier = gstins[0] if gstins else None

    return {
        **event,
        "extraction_status": "EXTRACTED",
        "extracted_fields": fields,
        "line_items": line_items,
        "gstin_supplier": gstin_supplier,
        "gstin_buyer": gstins[1] if len(gstins) > 1 else None,
        "invoice_date_iso": _parse_date(fields.get("INVOICE_RECEIPT_DATE", {}).get("value")),
    }


def _call_textract_with_retry(file_bytes, invoice_id):
    for attempt in range(1, MAX_TEXTRACT_ATTEMPTS + 1):
        try:
            return textract.analyze_expense(Document={"Bytes": file_bytes})
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code in ("ThrottlingException", "ProvisionedThroughputExceededException") and attempt < MAX_TEXTRACT_ATTEMPTS:
                sleep_for = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
                logger.warning("Textract throttled on %s (attempt %d/%d), backing off %.1fs.", invoice_id, attempt, MAX_TEXTRACT_ATTEMPTS, sleep_for)
                time.sleep(sleep_for)
                continue
            logger.exception("Textract call failed for %s: %s", invoice_id, code)
            return None
    return None


def _parse_summary_fields(response):
    fields = {}
    for doc in response.get("ExpenseDocuments", []):
        for f in doc.get("SummaryFields", []):
            ftype = f.get("Type", {}).get("Text")
            value = f.get("ValueDetection", {})
            if ftype and "Text" in value:
                fields[ftype] = {"value": value["Text"], "confidence": round(value.get("Confidence", 0), 1)}
    return fields


def _parse_line_items(response):
    items = []
    for doc in response.get("ExpenseDocuments", []):
        for group in doc.get("LineItemGroups", []):
            for line_item in group.get("LineItems", []):
                item = {}
                for f in line_item.get("LineItemExpenseFields", []):
                    ftype = f.get("Type", {}).get("Text")
                    value = f.get("ValueDetection", {}).get("Text")
                    if ftype == "ITEM":
                        item["description"] = value or ""
                    elif ftype == "PRODUCT_CODE":
                        # Textract's AnalyzeExpense is a generic invoice
                        # extractor with no concept of "HSN code" -- but on
                        # a real Indian invoice with an HSN column, that's
                        # exactly what lands in the generic PRODUCT_CODE
                        # field. Confirmed against a real invoice: "2523"
                        # for cement, "7214" for TMT bar, matching their
                        # actual GST HSN chapters.
                        item["hsn_code"] = (value or "").strip() or None
                if item:
                    items.append(item)
    return items


NATIVE_GSTIN_FIELD_TYPES = {"VENDOR_GST_NUMBER", "TAX_PAYER_ID", "RECEIVER_GST_NUMBER"}


def _find_native_gstins(response):
    """Every SummaryField labeled as a GST-number type, across every
    occurrence -- not deduped by type -- in first-seen order."""
    found = []
    for doc in response.get("ExpenseDocuments", []):
        for f in doc.get("SummaryFields", []):
            if f.get("Type", {}).get("Text") not in NATIVE_GSTIN_FIELD_TYPES:
                continue
            value = f.get("ValueDetection", {}).get("Text", "").strip().upper()
            if GSTIN_PATTERN.fullmatch(value) and value not in found:
                found.append(value)
    return found


def _find_gstins(response):
    """Scans every detected text block -- summary fields, line items, and
    raw expense-block text -- for GSTIN-shaped strings, deduplicated in
    the order first seen."""
    found = []
    for doc in response.get("ExpenseDocuments", []):
        for block in doc.get("Blocks", []):
            text = block.get("Text", "")
            for match in GSTIN_PATTERN.findall(text.upper()):
                if match not in found:
                    found.append(match)
        for f in doc.get("SummaryFields", []):
            text = f.get("ValueDetection", {}).get("Text", "")
            for match in GSTIN_PATTERN.findall(text.upper()):
                if match not in found:
                    found.append(match)
    return found


def _parse_date(raw):
    """Textract returns dates in whatever format the invoice used, not
    guaranteed ISO. Best-effort common-format parse; None (not a crash)
    on anything unrecognized -- the ITC engine already treats a missing
    invoice_date as "assume valid" rather than failing closed."""
    if not raw:
        return None
    from datetime import datetime

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None
