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
            # redis.from_url reads ssl from URL scheme (rediss:// = ssl)
            # Don't pass ssl= kwarg separately — causes errors with newer redis-py
            kwargs = {
                "decode_responses": True,
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
    key = f"gstin:{gstin}"
    encoded = json.dumps(data)
    if r:
        try:
            r.set(key, encoded, ex=ttl or settings.gstin_cache_ttl_seconds)
            return
        except Exception as e:
            logger.error(f"Redis cache_gstin failed: {e}")
    _mem_set(key, encoded, ex=ttl or settings.gstin_cache_ttl_seconds)


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


# --- Webhook Idempotency ---

def mark_message_processed(message_id: str, ttl: int = 3600) -> bool:
    """
    Claim a WhatsApp message_id for processing. Returns True the first time
    a given message_id is seen (Meta retries webhook deliveries on slow
    responses), False on any subsequent delivery of the same message.
    """
    r = get_redis()
    key = f"wa_msg:{message_id}"
    if r:
        try:
            return bool(r.set(key, "1", nx=True, ex=ttl))
        except Exception as e:
            logger.error(f"Redis mark_message_processed failed: {e}")
            return True
    if _mem_get(key) is not None:
        return False
    _mem_set(key, "1", ex=ttl)
    return True


# --- Token Revocation ---

def revoke_token(jti: str, ttl: int) -> None:
    """
    Revoke a JWT by its jti claim. TTL should match the token's remaining
    lifetime so the revocation record expires alongside the token it guards,
    instead of accumulating forever.
    """
    r = get_redis()
    key = f"revoked_jti:{jti}"
    ttl = max(int(ttl), 1)
    if r:
        try:
            r.set(key, "1", ex=ttl)
            return
        except Exception as e:
            logger.error(f"Redis revoke_token failed: {e}")
    _mem_set(key, "1", ex=ttl)


def is_token_revoked(jti: Optional[str]) -> bool:
    """Check whether a jti has been revoked. Tokens with no jti (issued
    before revocation support existed) can't be individually revoked —
    callers should treat a falsy jti as "not revoked" rather than calling
    this at all."""
    if not jti:
        return False
    r = get_redis()
    key = f"revoked_jti:{jti}"
    if r:
        try:
            return r.get(key) is not None
        except Exception as e:
            logger.error(f"Redis is_token_revoked failed: {e}")
    return _mem_get(key) is not None


# --- Per-Phone Processing Lock ---

def acquire_phone_lock(phone: str, ttl: int = 15) -> bool:
    """
    Claim an exclusive processing slot for a phone number's in-flight
    webhook message. Returns True the first caller to acquire it; False if
    another message from the same number is already being processed
    (SETNX-with-TTL, same pattern as mark_message_processed). The TTL is a
    backstop against a crashed/hung handler — normal completion releases
    the lock explicitly via release_phone_lock.
    """
    r = get_redis()
    key = f"phone_lock:{phone}"
    if r:
        try:
            return bool(r.set(key, "1", nx=True, ex=ttl))
        except Exception as e:
            logger.error(f"Redis acquire_phone_lock failed: {e}")
            return True
    if _mem_get(key) is not None:
        return False
    _mem_set(key, "1", ex=ttl)
    return True


def release_phone_lock(phone: str) -> None:
    """Release the per-phone processing lock."""
    r = get_redis()
    key = f"phone_lock:{phone}"
    if r:
        try:
            r.delete(key)
            return
        except Exception as e:
            logger.error(f"Redis release_phone_lock failed: {e}")
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

