import httpx
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url

    async def list_models(self) -> List[str]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.debug(f"Ollama list_models failed: {e}")
        return []

    async def generate(self, model: str, prompt: str, temperature: float = 0.3) -> Optional[str]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": temperature}
                    },
                    timeout=60.0
                )
                if resp.status_code == 200:
                    return resp.json().get("response")
        except Exception as e:
            logger.error(f"Ollama generate failed: {e}")
        return None

    async def generate_vision(self, model: str, prompt: str, image_b64: str, temperature: float = 0.3) -> Optional[str]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "images": [image_b64],
                        "stream": False,
                        "options": {"temperature": temperature}
                    },
                    timeout=120.0
                )
                if resp.status_code == 200:
                    return resp.json().get("response")
        except Exception as e:
            logger.error(f"Ollama vision generate failed: {e}")
        return None

ollama_client = OllamaClient()
