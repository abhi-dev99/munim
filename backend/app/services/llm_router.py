import json
import logging
import base64
from enum import Enum
from typing import Optional, Dict, Any

from app.config import get_settings
from app.services.ollama_client import ollama_client
from app.services.privacy_layer import privacy_layer

# Gemini imports moved to function level to avoid circular dependency

logger = logging.getLogger(__name__)
settings = get_settings()

class LLMTask(str, Enum):
    DIAGNOSIS = "DIAGNOSIS"
    INTENT = "INTENT"
    SUMMARY = "SUMMARY"
    EXTRACTION = "EXTRACTION"

class LLMRouter:
    def __init__(self):
        self.prefer_local = getattr(settings, 'PREFER_LOCAL_LLM', True)
        self.online_enabled = getattr(settings, 'ONLINE_LLM_ENABLED', True)
        self.ollama_text_model = getattr(settings, 'OLLAMA_TEXT_MODEL', 'llama3.1:8b')
        self.ollama_vision_model = getattr(settings, 'OLLAMA_VISION_MODEL', 'llava:7b')
        self.available_ollama_models = []

    async def initialize(self):
        self.available_ollama_models = await ollama_client.list_models()
        logger.info(f"LLMRouter init: available Ollama models: {self.available_ollama_models}")

    async def _generate_online(self, prompt: str, context: Dict[str, Any], task: LLMTask, temperature: float) -> str:
        from app.services.gemini import client as gemini_client, settings as gemini_settings
        from google.genai import types

        if not self.online_enabled:
            logger.warning("Online LLM disabled, failing back to None.")
            return ""

        # Anonymize context for online usage
        anon_ctx, de_anon_fn = privacy_layer.anonymize_for_llm(context, "gemini", task.value)
        
        # Build prompt with anonymized context
        full_prompt = f"{prompt}\n\nContext:\n{json.dumps(anon_ctx, indent=2)}"

        try:
            response = gemini_client.models.generate_content(
                model=gemini_settings.gemini_model,
                contents=full_prompt,
                config=types.GenerateContentConfig(temperature=temperature)
            )
            raw_text = response.text.strip()
            
            # Since online generated text, we might need to de-anonymize.
            # But the prompt might just ask for a generic verdict.
            # For JSON outputs, we should parse it, de-anonymize, then stringify again.
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[1]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3].strip()

            try:
                parsed_json = json.loads(raw_text)
                restored_json = de_anon_fn(parsed_json)
                return json.dumps(restored_json)
            except json.JSONDecodeError:
                # If not JSON, just return text. Deanonymization on raw text is harder,
                # but usually verdicts don't echo IDs.
                return raw_text
                
        except Exception as e:
            logger.error(f"Online LLM call failed: {e}")
            return ""

    async def generate_text(self, prompt: str, context: Dict[str, Any], task: LLMTask, temperature: float = 0.3) -> str:
        # Check if local is preferred and available
        if self.prefer_local and any(m.startswith(self.ollama_text_model.split(":")[0]) for m in self.available_ollama_models):
            # For local, we can technically pass raw data, but let's be safe and use privacy layer anyway,
            # or just log it locally. We'll pass raw to Ollama.
            full_prompt = f"{prompt}\n\nContext:\n{json.dumps(context, indent=2)}"
            response = await ollama_client.generate(self.ollama_text_model, full_prompt, temperature=temperature)
            if response:
                return response.strip()

        # Fallback to online
        return await self._generate_online(prompt, context, task, temperature)

    async def extract_invoice(self, image_bytes: bytes, mime_type: str) -> Optional[Dict[str, Any]]:
        # Skip Ollama for vision — llava:7b is too unreliable for structured Indian invoice extraction
        # Go straight to Gemini which handles complex multi-line Indian invoices correctly

        if not self.online_enabled:
            return None

        from app.services.gemini import client as gemini_client, settings as gemini_settings
        from google.genai import types

        EXTRACTION_PROMPT = """You are an expert Indian GST invoice parser. Extract ALL data from this invoice image.

Return a JSON object with EXACTLY these fields (use null for missing values):
{
  "invoice_number": "string or null",
  "invoice_date": "YYYY-MM-DD format or null",
  "supplier_name": "business/company name of the seller",
  "supplier_email": "email address of the seller or null",
  "supplier_phone": "phone number of the seller or null",
  "gstin_supplier": "15-char GST number of seller or null",
  "gstin_buyer": "15-char GST number of buyer or null",
  "total_taxable_amount": number or null,
  "total_tax_amount": number or null,
  "total_amount": grand total number or null,
  "confidence": 0.0 to 1.0 (your confidence this is a real invoice),
  "line_items": [
    {
      "description": "item description",
      "hsn_code": "HSN/SAC code string or null",
      "quantity": number or null,
      "unit": "unit string or null",
      "unit_price": number or null,
      "taxable_value": number or null,
      "cgst_rate": number or null,
      "sgst_rate": number or null,
      "igst_rate": number or null,
      "cgst_amount": number or null,
      "sgst_amount": number or null,
      "igst_amount": number or null
    }
  ]
}

IMPORTANT rules:
- If this is NOT an invoice, set confidence to 0.1 and all other fields to null
- GSTIN format is exactly 15 characters (e.g. 27AABCU9603R1ZM)
- Amounts must be numbers, not strings
- For Composition scheme invoices, there is no GST breakdown — still extract the total
- Return ONLY the JSON, no markdown, no explanation"""

        try:
            gemini_response = gemini_client.models.generate_content(
                model=gemini_settings.gemini_model,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    types.Part.from_text(text=EXTRACTION_PROMPT),
                ],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=8192,
                )
            )
            raw = gemini_response.text.strip() if gemini_response.text else ""
            logger.info(f"Gemini raw extraction response (first 300): {raw[:300]}")
            # Strip markdown code fences if Gemini wraps output
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:])
                if raw.endswith("```"):
                    raw = raw[:-3].strip()
            try:
                result = json.loads(raw)
            except json.JSONDecodeError:
                # Response was truncated mid-JSON — try to salvage it
                logger.warning("JSON truncated, attempting repair...")
                # Find the last complete top-level field before truncation
                # Strategy: find last complete '},\n' or '}\n' and close the JSON
                salvage = raw
                # Close any open array
                open_arrays = salvage.count("[") - salvage.count("]")
                open_objects = salvage.count("{") - salvage.count("}")
                # Strip trailing incomplete string (find last complete ",)
                last_quote = salvage.rfind('",')
                last_newline = salvage.rfind('\n', 0, last_quote) if last_quote > 0 else -1
                if last_newline > 0:
                    salvage = salvage[:last_newline]
                salvage += "]" * max(0, open_arrays) + "}" * max(0, open_objects)
                try:
                    result = json.loads(salvage)
                    result["confidence"] = result.get("confidence", 0.7)  # partial = assume readable
                    logger.info(f"Salvaged truncated JSON: {list(result.keys())}")
                except Exception:
                    logger.error(f"Salvage failed too. Raw (first 500): {raw[:500]}")
                    return None
            logger.info(f"Invoice extracted: supplier={result.get('supplier_name')}, confidence={result.get('confidence')}, items={len(result.get('line_items', []))}")
            return result
        except Exception as e:
            err_str = str(e)
            logger.error(f"Gemini extraction exception (full): {err_str}")
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                logger.error("Gemini API quota exceeded — invoice extraction unavailable")
                return {"__quota_exceeded__": True}
            logger.error(f"Gemini extraction failed: {e}")
            return None

llm_router = LLMRouter()

