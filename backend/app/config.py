"""
Munim.ai — Application Configuration
All settings loaded from environment variables with sensible defaults.
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # --- App ---
    environment: str = "development"
    app_name: str = "Munim.ai"
    app_version: str = "1.0.0"
    fastapi_port: int = 8000
    debug: bool = False
    jwt_secret: str = "default_secret_key_change_in_prod"
    allowed_origins: str = "http://localhost:3000,http://localhost:3002,https://moaning-thwarting-dinginess.ngrok-free.dev"

    # --- Gemini (key pool: add up to 7 keys, system auto-rotates on 429) ---
    gemini_api_key: str = ""
    gemini_api_key_2: str = ""
    gemini_api_key_3: str = ""
    gemini_api_key_4: str = ""
    gemini_api_key_5: str = ""
    gemini_api_key_6: str = ""
    gemini_api_key_7: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"

    # --- Groq ---
    groq_api_key: str = ""
    # llama-3.1-8b-instant (and Groq's whole Llama lineup) has been removed
    # from Groq's model catalog -- confirmed live via GET /openai/v1/models,
    # which returned 404 model_not_found for it and no llama-3.x model at
    # all. openai/gpt-oss-20b is the closest current equivalent: fast,
    # general-purpose, open-weight.
    groq_model: str = "openai/gpt-oss-20b"

    # --- Meta WhatsApp ---
    meta_whatsapp_token: str = ""
    meta_phone_number_id: str = ""
    meta_whatsapp_business_account_id: str = ""
    meta_verify_token: str = "munim_verify_2026"
    meta_app_secret: str = ""
    meta_api_version: str = "v21.0"
    # Dialable WhatsApp number behind meta_phone_number_id, used to build
    # wa.me deep links (the Graph API phone_number_id itself isn't dialable).
    whatsapp_business_number: str = ""

    # --- Supabase ---
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # --- Upstash Redis ---
    upstash_redis_url: str = ""
    upstash_redis_token: str = ""

    # --- GSTIN Verification API (Sandbox.co.in + Dubey fallback) ---
    sandbox_api_key: str = ""
    sandbox_api_secret: str = ""
    gstin_api_key: str = ""
    gstin_api_base_url: str = "https://api.gstverify.dubey.app"

    # --- Admin API (gates backend/app/api/admin.py) ---
    admin_api_key: str = ""

    # --- Resend API ---
    resend_api_key: str = ""

    # --- Cache TTLs ---
    gstin_cache_ttl_seconds: int = 86400  # 24 hours
    session_ttl_seconds: int = 3600  # 1 hour

    # --- ITC Rules ---
    fuzzy_match_amount_tolerance: float = 0.02  # 2%
    fuzzy_match_date_window_days: int = 30
    fraud_score_hard_threshold: int = 70
    fraud_score_soft_threshold: int = 40

    # --- ngrok / Public URL ---
    public_url: str = ""  # ngrok or server URL

    # Where the browser-facing app is served from. Used to build links that
    # leave the system and are opened by someone who is not a user -- today
    # that is the vendor fix link (app/api/vendor.py), which a supplier opens
    # from WhatsApp. Getting this wrong in production does not fail loudly: it
    # produces a link to localhost that the supplier simply cannot open, so
    # `frontend_base_url` refuses to guess and falls back to `public_url`
    # before the localhost default.
    frontend_url: str = ""

    @property
    def frontend_base_url(self) -> str:
        return (self.frontend_url or self.public_url or "http://localhost:3000").rstrip("/")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
