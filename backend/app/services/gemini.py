"""
Munim.ai — Gemini AI Service
Handles: Vision extraction, Hindi text generation, embeddings.
"""

import json
import logging
from typing import Optional

from google import genai
from google.genai import types

from app.config import get_settings
from app.models.invoice import InvoiceJSON, LineItem

logger = logging.getLogger(__name__)

settings = get_settings()

client = genai.Client(api_key=settings.gemini_api_key)

# --- Prompts ---

EXTRACTION_PROMPT = """You are a GST invoice parser for India. Extract ALL fields from this invoice image.
Return ONLY valid JSON matching this exact schema. No prose. No markdown. No code fences.

Schema:
{
  "invoice_number": "string",
  "invoice_date": "YYYY-MM-DD",
  "gstin_supplier": "15-char GSTIN or null",
  "gstin_buyer": "15-char GSTIN or null",
  "supplier_name": "string",
  "line_items": [
    {
      "description": "string",
      "hsn_code": "string or null",
      "quantity": number,
      "unit": "string",
      "unit_price": number,
      "taxable_value": number,
      "cgst_rate": number,
      "sgst_rate": number,
      "igst_rate": number,
      "cgst_amount": number,
      "sgst_amount": number,
      "igst_amount": number
    }
  ],
  "total_taxable_amount": number,
  "total_tax_amount": number,
  "total_amount": number,
  "confidence": number
}

Rules:
- Extract GSTIN exactly as printed (15 alphanumeric characters).
- If a field is not visible or unreadable, set it to null.
- For amounts, use numbers without currency symbols.
- Parse dates into YYYY-MM-DD format.
- confidence should be 0.0 to 1.0 reflecting extraction quality.
"""

DIAGNOSIS_PROMPT_TEMPLATE = """You are Munim, a GST compliance assistant for Indian traders.
Generate a WhatsApp message in Hindi (Hinglish script — Hindi words in Roman letters) explaining this invoice diagnosis to a small business owner.

Rules:
- Keep it simple, conversational, like talking to a friend.
- Use ₹ symbol for amounts.
- Use emojis: ✅ for good, ⚠️ for fixable, 🚨 for risky, 🚫 for fraud.
- Always state the action the trader should take.
- Max 300 words.
- Do NOT use Devanagari script. Use Roman/Latin letters for Hindi words.

Invoice Details:
- Supplier: {supplier_name}
- Amount: ₹{total_amount}
- ITC Status: {itc_status}
- ITC Amount: ₹{itc_amount}
- Blocked Amount: ₹{itc_blocked}
- Block Reason: {block_reason}
- Fix Action: {fix_action}
- HSN Issues: {hsn_issues}
- GSTIN Status: {gstin_status}
- Supplier Flags: {supplier_flags}
- Fraud Score: {fraud_score}/100
- Fraud Signals: {fraud_signals}
- GSTR-2B Match: {gstr2b_status}

Generate the WhatsApp message:
"""


async def extract_invoice_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> InvoiceJSON:
    """Extract structured invoice data from an image using Gemini Vision."""
    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                        types.Part.from_text(text=EXTRACTION_PROMPT),
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=4096,
            ),
        )

        raw_text = response.text.strip()

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3].strip()

        invoice_data = json.loads(raw_text)
        return InvoiceJSON(**invoice_data)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON: {e}")
        logger.error(f"Raw response: {raw_text[:500]}")
        return InvoiceJSON(confidence=0.0)
    except Exception as e:
        logger.error(f"Gemini extraction failed: {e}")
        raise


async def generate_hindi_diagnosis(
    supplier_name: str,
    total_amount: float,
    itc_status: str,
    itc_amount: float,
    itc_blocked: float = 0.0,
    block_reason: str = "None",
    fix_action: str = "None",
    hsn_issues: str = "None",
    gstin_status: str = "Valid",
    supplier_flags: str = "None",
    fraud_score: int = 0,
    fraud_signals: str = "None",
    gstr2b_status: str = "Unreconciled",
) -> str:
    """Generate a Hindi WhatsApp diagnosis message."""
    prompt = DIAGNOSIS_PROMPT_TEMPLATE.format(
        supplier_name=supplier_name or "Unknown",
        total_amount=total_amount or 0,
        itc_status=itc_status,
        itc_amount=itc_amount,
        itc_blocked=itc_blocked,
        block_reason=block_reason,
        fix_action=fix_action,
        hsn_issues=hsn_issues,
        gstin_status=gstin_status,
        supplier_flags=supplier_flags,
        fraud_score=fraud_score,
        fraud_signals=fraud_signals,
        gstr2b_status=gstr2b_status,
    )

    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=1024,
            ),
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Hindi diagnosis generation failed: {e}")
        # Fallback static message
        return f"📄 Invoice processed: {supplier_name} | ₹{total_amount}\nITC Status: {itc_status}\nAmount: ₹{itc_amount}"


async def transcribe_voice_note(audio_bytes: bytes, mime_type: str = "audio/ogg") -> str:
    """Transcribe a WhatsApp voice note using Gemini."""
    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                        types.Part.from_text(
                            text="Transcribe this Hindi/Hinglish audio. Return only the transcription, no commentary."
                        ),
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=2048,
            ),
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Voice transcription failed: {e}")
        return ""


async def embed_text(text: str) -> list[float]:
    """Generate embedding for a text using Gemini."""
    try:
        response = client.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=text,
        )
        return response.embeddings[0].values
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return []
