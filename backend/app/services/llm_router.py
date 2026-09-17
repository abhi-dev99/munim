import json
import logging
import base64
from enum import Enum
from typing import Optional, Dict, Any

from app.config import get_settings
from app.services.ollama_client import ollama_client
from app.services.privacy_layer import privacy_layer

# Only import gemini client logic if we need it to fallback
from app.services.gemini import client as gemini_client, settings as gemini_settings
from google.genai import types

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
        # Vision task: Try Ollama first if llava is available
        prompt = "Extract all invoice details into a JSON object: gstin_supplier, total_amount, invoice_number, invoice_date. Return ONLY JSON."
        if self.prefer_local and any(m.startswith("llava") for m in self.available_ollama_models):
            b64_image = base64.b64encode(image_bytes).decode("utf-8")
            response = await ollama_client.generate_vision(self.ollama_vision_model, prompt, b64_image, temperature=0.1)
            if response:
                try:
                    text = response.strip()
                    if text.startswith("```"):
                        text = text.split("\n", 1)[1]
                        if text.endswith("```"):
                            text = text[:-3].strip()
                    return json.loads(text)
                except Exception as e:
                    logger.debug(f"Failed to parse Ollama vision output: {e}")

        # Fallback to Gemini
        if not self.online_enabled:
            return None

        # For vision extraction, we don't have context to anonymize YET, we're extracting it.
        # So we just send the image directly to Gemini. This is an accepted privacy tradeoff for extraction.
        try:
            gemini_response = gemini_client.models.generate_content(
                model=gemini_settings.gemini_model,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt,
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                )
            )
            return json.loads(gemini_response.text.strip())
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            return None

llm_router = LLMRouter()
