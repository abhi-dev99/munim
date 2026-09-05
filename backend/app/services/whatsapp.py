"""
Munim.ai — WhatsApp Cloud API Service
Handles: sending messages, receiving webhook events, downloading media.
"""

import hashlib
import hmac
import logging
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

BASE_URL = f"https://graph.facebook.com/{settings.meta_api_version}"


async def send_text_message(to: str, message: str) -> bool:
    """Send a text message via WhatsApp Cloud API."""
    url = f"{BASE_URL}/{settings.meta_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.meta_whatsapp_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                logger.info(f"Message sent to {to}")
                return True
            else:
                logger.error(f"WhatsApp send failed: {response.status_code} — {response.text}")
                return False
    except Exception as e:
        logger.error(f"WhatsApp send error: {e}")
        return False


async def send_document(to: str, document_url: str, caption: str = "", filename: str = "munim_report.pdf") -> bool:
    """Send a document (PDF) via WhatsApp."""
    url = f"{BASE_URL}/{settings.meta_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.meta_whatsapp_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "document",
        "document": {
            "link": document_url,
            "caption": caption,
            "filename": filename,
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                logger.info(f"Document sent to {to}")
                return True
            else:
                logger.error(f"WhatsApp send document failed: {response.status_code} — {response.text}")
                return False
    except Exception as e:
        logger.error(f"WhatsApp send document error: {e}")
        return False


async def send_audio_message(to: str, audio_url: str) -> bool:
    """Send an audio/voice message via WhatsApp."""
    url = f"{BASE_URL}/{settings.meta_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.meta_whatsapp_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "audio",
        "audio": {
            "link": audio_url
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                logger.info(f"Audio sent to {to}")
                return True
            else:
                logger.error(f"WhatsApp send audio failed: {response.status_code} — {response.text}")
                return False
    except Exception as e:
        logger.error(f"WhatsApp audio send error: {e}")
        return False


async def download_media(media_id: str) -> tuple[Optional[bytes], Optional[str]]:
    """
    Download media from WhatsApp (two-step: get URL, then download).
    Returns (file_bytes, mime_type).
    """
    headers = {"Authorization": f"Bearer {settings.meta_whatsapp_token}"}

    try:
        async with httpx.AsyncClient() as client:
            # Step 1: Get media URL
            media_url_response = await client.get(
                f"{BASE_URL}/{media_id}", headers=headers, timeout=15
            )
            if media_url_response.status_code != 200:
                logger.error(f"Failed to get media URL: {media_url_response.text}")
                return None, None

            media_data = media_url_response.json()
            download_url = media_data.get("url")
            mime_type = media_data.get("mime_type", "image/jpeg")

            if not download_url:
                return None, None

            # Step 2: Download the actual file
            file_response = await client.get(
                download_url, headers=headers, timeout=60
            )
            if file_response.status_code == 200:
                return file_response.content, mime_type
            else:
                logger.error(f"Failed to download media: {file_response.status_code}")
                return None, None

    except Exception as e:
        logger.error(f"Media download error: {e}")
        return None, None


async def mark_message_read(message_id: str) -> None:
    """Mark a message as read (blue ticks)."""
    url = f"{BASE_URL}/{settings.meta_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.meta_whatsapp_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }

    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, headers=headers, timeout=10)
    except Exception as e:
        logger.error(f"Mark read error: {e}")


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify webhook payload signature from Meta."""
    if not settings.meta_app_secret:
        return True  # Skip verification in dev mode

    expected = hmac.new(
        settings.meta_app_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)


def parse_webhook_message(body: dict) -> Optional[dict]:
    """
    Parse incoming webhook body from Meta and extract message info.
    Returns dict with: from_number, message_id, message_type, text, media_id, mime_type
    """
    try:
        entry = body.get("entry", [])
        if not entry:
            return None

        changes = entry[0].get("changes", [])
        if not changes:
            return None

        value = changes[0].get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return None

        msg = messages[0]
        result = {
            "from_number": msg.get("from", ""),
            "message_id": msg.get("id", ""),
            "message_type": msg.get("type", ""),
            "timestamp": msg.get("timestamp", ""),
        }

        if msg["type"] == "text":
            result["text"] = msg.get("text", {}).get("body", "")
        elif msg["type"] == "image":
            image = msg.get("image", {})
            result["media_id"] = image.get("id")
            result["mime_type"] = image.get("mime_type", "image/jpeg")
            result["caption"] = image.get("caption", "")
        elif msg["type"] == "document":
            doc = msg.get("document", {})
            result["media_id"] = doc.get("id")
            result["mime_type"] = doc.get("mime_type", "application/pdf")
            result["filename"] = doc.get("filename", "")
        elif msg["type"] == "audio":
            audio = msg.get("audio", {})
            result["media_id"] = audio.get("id")
            result["mime_type"] = audio.get("mime_type", "audio/ogg")
        elif msg["type"] == "reaction":
            reaction = msg.get("reaction", {})
            result["reaction_emoji"] = reaction.get("emoji", "")
            result["reaction_message_id"] = reaction.get("message_id", "")

        # Extract context if it's a reply
        if "context" in msg:
            result["reply_to_message_id"] = msg["context"].get("id", "")

        return result

    except (IndexError, KeyError) as e:
        logger.error(f"Webhook parse error: {e}")
        return None
