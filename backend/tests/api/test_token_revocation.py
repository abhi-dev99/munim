"""
Regression tests for JWT revocation (jti claim + Redis-backed revocation
list). Runs against the in-memory fallback cache in redis_cache.py — no
live Redis needed, same as the rest of this suite in a dev environment
with no Upstash credentials configured.
"""

from datetime import datetime, timedelta

import jwt as pyjwt
import pytest
from fastapi import HTTPException

from app.api import deps
from app.config import get_settings
from app.services.redis_cache import is_token_revoked, revoke_token


def _make_token(sub: str = "trader-1", jti: str = None, exp_delta: timedelta = timedelta(days=1)) -> str:
    settings = get_settings()
    payload = {
        "sub": sub,
        "exp": datetime.utcnow() + exp_delta,
        "iat": datetime.utcnow(),
    }
    if jti is not None:
        payload["jti"] = jti
    return pyjwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def test_revoke_token_round_trip():
    jti = "test-jti-round-trip"
    other_jti = "test-jti-untouched"

    assert is_token_revoked(jti) is False

    revoke_token(jti, ttl=60)

    assert is_token_revoked(jti) is True
    # A different jti was never revoked and must not be affected.
    assert is_token_revoked(other_jti) is False


def test_is_token_revoked_handles_missing_jti_without_crashing():
    assert is_token_revoked(None) is False
    assert is_token_revoked("") is False


def test_get_current_trader_id_accepts_token_without_jti():
    # Simulates a token issued before this migration — no jti claim at all.
    token = _make_token(sub="trader-legacy", jti=None)
    trader_id = deps.get_current_trader_id(authorization=f"Bearer {token}")
    assert trader_id == "trader-legacy"


def test_get_current_trader_id_rejects_revoked_token():
    jti = "test-jti-revoked-rejection"
    token = _make_token(sub="trader-2", jti=jti)
    revoke_token(jti, ttl=60)

    with pytest.raises(HTTPException) as exc_info:
        deps.get_current_trader_id(authorization=f"Bearer {token}")
    assert exc_info.value.status_code == 401


def test_get_current_trader_id_accepts_non_revoked_token_with_jti():
    jti = "test-jti-still-valid"
    token = _make_token(sub="trader-3", jti=jti)
    trader_id = deps.get_current_trader_id(authorization=f"Bearer {token}")
    assert trader_id == "trader-3"
