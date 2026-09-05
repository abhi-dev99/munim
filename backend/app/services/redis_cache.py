"""
Munim.ai — Redis Cache Service (via Upstash Redis)
Caches: GSTIN lookups, conversation state, rate limiting.
Falls back to in-memory dict when Redis is unavailable (for local dev/demo).
"""

import json
import logging
import time
from typing import Optional

import redis

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Upstash Redis connection
_redis_client: Optional[redis.Redis] = None

# In-memory fallback cache (dict: key → (value, expires_at or None))
_memory_cache: dict = {}


def get_redis() -> Optional[redis.Redis]:
    """Get or create Redis client. Returns None if unavailable (fallback to memory)."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if settings.upstash_redis_url:
        try:
            is_ssl = settings.upstash_redis_url.startswith("rediss://")
            kwargs = {
                "decode_responses": True,
                "ssl": is_ssl,
                "socket_connect_timeout": 2,
                "socket_timeout": 2,
            }
            if settings.upstash_redis_token:
                kwargs["password"] = settings.upstash_redis_token
            client = redis.from_url(settings.upstash_redis_url, **kwargs)
            client.ping()  # Test connection
            _redis_client = client
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}) — using in-memory fallback cache")
            _redis_client = None
    return _redis_client


def _mem_set(key: str, value: str, ex: int = None) -> None:
    """Set value in memory cache with optional TTL in seconds."""
    expires_at = time.time() + ex if ex else None
    _memory_cache[key] = (value, expires_at)


def _mem_get(key: str) -> Optional[str]:
    """Get value from memory cache, respecting TTL."""
    entry = _memory_cache.get(key)
    if not entry:
        return None
    value, expires_at = entry
    if expires_at and time.time() > expires_at:
        del _memory_cache[key]
        return None
    return value


def _mem_delete(key: str) -> None:
    _memory_cache.pop(key, None)


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
    key = f"gstin:{gstin}"
    if r:
        try:
            data = r.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis get_cached_gstin failed: {e}")
    # Memory fallback
    data = _mem_get(key)
    return json.loads(data) if data else None


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
    key = f"conv:{phone}"
    data = json.dumps({"state": state, "context": context or {}})
    ttl = settings.session_ttl_seconds
    if r:
        try:
            r.set(key, data, ex=ttl)
            return
        except Exception as e:
            logger.error(f"Redis set_conversation_state failed: {e}")
    # Memory fallback
    _mem_set(key, data, ex=ttl)


def get_conversation_state(phone: str) -> Optional[dict]:
    """Get conversation state for a trader."""
    r = get_redis()
    key = f"conv:{phone}"
    if r:
        try:
            data = r.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis get_conversation_state failed: {e}")
    # Memory fallback
    data = _mem_get(key)
    return json.loads(data) if data else None


def clear_conversation_state(phone: str) -> None:
    """Clear conversation state."""
    r = get_redis()
    key = f"conv:{phone}"
    if r:
        try:
            r.delete(key)
        except Exception as e:
            logger.error(f"Redis clear_conversation_state failed: {e}")
    _mem_delete(key)


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
