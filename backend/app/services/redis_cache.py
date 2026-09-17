"""
Munim.ai — Redis Cache Service (via Upstash Redis)
Caches: GSTIN lookups, conversation state, rate limiting.
"""

import json
import logging
from typing import Optional

import redis

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Upstash Redis connection
_redis_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        if settings.upstash_redis_url:
            is_ssl = settings.upstash_redis_url.startswith("rediss://")
            kwargs = {
                "decode_responses": True,
                "ssl": is_ssl,
            }
            if settings.upstash_redis_token:
                kwargs["password"] = settings.upstash_redis_token
                
            _redis_client = redis.from_url(
                settings.upstash_redis_url,
                **kwargs
            )
        else:
            logger.warning("Redis not configured — using in-memory fallback")
            return None
    return _redis_client


# --- GSTIN Cache ---

def cache_gstin(gstin: str, data: dict, ttl: int = None) -> None:
    """Cache GSTIN verification result permanently (invalidated on state change)."""
    r = get_redis()
    if not r:
        return
    try:
        key = f"gstin:{gstin}"
        r.set(key, json.dumps(data), ex=ttl or settings.gstin_cache_ttl_seconds)
    except Exception as e:
        logger.error(f"Redis cache_gstin failed: {e}")


def get_cached_gstin(gstin: str) -> Optional[dict]:
    """Get cached GSTIN verification result."""
    r = get_redis()
    if not r:
        return None
    try:
        key = f"gstin:{gstin}"
        data = r.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"Redis get_cached_gstin failed: {e}")
        return None


def invalidate_gstin_cache(gstin: str) -> None:
    """Invalidate GSTIN cache on state change."""
    r = get_redis()
    if not r:
        return
    try:
        r.delete(f"gstin:{gstin}")
    except Exception as e:
        logger.error(f"Redis invalidate_gstin failed: {e}")


# --- Conversation State ---

def set_conversation_state(phone: str, state: str, context: dict = None) -> None:
    """Set conversation state for a trader (by phone number)."""
    r = get_redis()
    if not r:
        return
    try:
        key = f"conv:{phone}"
        data = {"state": state, "context": context or {}}
        r.set(key, json.dumps(data), ex=settings.session_ttl_seconds)
    except Exception as e:
        logger.error(f"Redis set_conversation_state failed: {e}")


def get_conversation_state(phone: str) -> Optional[dict]:
    """Get conversation state for a trader."""
    r = get_redis()
    if not r:
        return None
    try:
        key = f"conv:{phone}"
        data = r.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"Redis get_conversation_state failed: {e}")
        return None


def clear_conversation_state(phone: str) -> None:
    """Clear conversation state."""
    r = get_redis()
    if not r:
        return
    try:
        r.delete(f"conv:{phone}")
    except Exception as e:
        logger.error(f"Redis clear_conversation_state failed: {e}")


# --- Rate Limiting ---

def check_rate_limit(key: str, max_requests: int = 10, window_seconds: int = 60) -> bool:
    """Check if a rate limit has been exceeded. Returns True if allowed."""
    r = get_redis()
    if not r:
        return True
    try:
        rl_key = f"rl:{key}"
        current = r.incr(rl_key)
        if current == 1:
            r.expire(rl_key, window_seconds)
        return current <= max_requests
    except Exception as e:
        logger.error(f"Redis rate_limit check failed: {e}")
        return True
