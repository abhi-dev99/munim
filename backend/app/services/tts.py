"""
Munim.ai — Text-to-Speech Service
Uses gTTS (Google Text-to-Speech) for completely free voice generation.
"""

import os
import uuid
import logging
from gtts import gTTS
from app.services.supabase_client import upload_file

logger = logging.getLogger(__name__)

async def generate_and_upload_tts(text: str, lang: str = "hi") -> str | None:
    """
    Generates speech from text and uploads the MP3 to Supabase Storage.
    Returns the public URL of the uploaded audio file.
    """
    if not text:
        return None
        
    try:
        # Generate speech
        tts = gTTS(text=text, lang=lang)
        
        filename = f"{uuid.uuid4()}.mp3"
        filepath = f"/tmp/{filename}" if os.name != 'nt' else f"{os.getenv('TEMP', 'C:\\Windows\\Temp')}\\{filename}"
        
        # Save locally first
        tts.save(filepath)
        
        # Read the file to upload
        with open(filepath, "rb") as f:
            file_bytes = f.read()
            
        # Upload to Supabase 'invoices' bucket (or a dedicated 'media' bucket if preferred)
        # Using 'invoices' bucket since it's already configured and public
        storage_path = f"voice_notes/{filename}"
        public_url = await upload_file("invoices", storage_path, file_bytes, "audio/mpeg")
        
        # Cleanup
        try:
            os.remove(filepath)
        except Exception:
            pass
            
        return public_url
    except Exception as e:
        logger.error(f"TTS generation or upload failed: {e}")
        return None
