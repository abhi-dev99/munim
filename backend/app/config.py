"""
Munim.ai — Application Configuration
All settings loaded from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # --- App ---
    environment: str = "development"
    app_name: str = "Munim.ai"
    app_version: str = "1.0.0"
    fastapi_port: int = 8000
    debug: bool = True

    # --- Gemini ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "models/text-embedding-004"

    # --- Meta WhatsApp ---
    meta_whatsapp_token: str = ""
    meta_phone_number_id: str = ""
    meta_whatsapp_business_account_id: str = ""
    meta_verify_token: str = "munim_verify_2026"
    meta_app_secret: str = ""
    meta_api_version: str = "v21.0"

    # --- Supabase ---
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # --- Upstash Redis ---
    upstash_redis_url: str = ""
    upstash_redis_token: str = ""

    # --- GSTIN Verification API ---
    gstin_api_key: str = ""
    gstin_api_base_url: str = "https://api.deepvue.tech/v1"

    # --- Cache TTLs ---
    gstin_cache_ttl_seconds: int = 86400  # 24 hours
    session_ttl_seconds: int = 3600  # 1 hour

    # --- ITC Rules ---
    fuzzy_match_amount_tolerance: float = 0.02  # 2%
    fuzzy_match_date_window_days: int = 30
    fraud_score_hard_threshold: int = 70
    fraud_score_soft_threshold: int = 40

    # --- ngrok / Public URL ---
    public_url: str = ""  # ngrok or Railway URL

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
