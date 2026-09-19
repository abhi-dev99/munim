import logging
import random
import time
import uuid
from typing import Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status, Depends
from app.services.supabase_client import get_supabase
from app.services import whatsapp

from app.services.redis_cache import (
    get_redis,
    _mem_set,
    _mem_get,
    _mem_delete,
    check_rate_limit,
    revoke_token,
)
from app.api.deps import get_current_token_payload
from app.services.phone import match_variants, normalize_msisdn

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
logger = logging.getLogger(__name__)


def _login_identity(raw: str) -> tuple[str, list[str]]:
    """
    Turn whatever somebody typed into the login box into (canonical, variants).

    A person signing in types the number they know: ten digits, no country
    code. `traders.whatsapp_number` may hold it either way, because rows reach
    that table from onboarding, seed scripts and CSVs. Matching the typed
    string directly meant a trader stored as `919822062252` simply could not
    log in as `9822062252` -- the lookup found nothing, and the endpoint's
    (correct) refusal to leak whether a number is registered meant they got
    "if this number is registered, an OTP has been sent" and no OTP, forever,
    with nothing to tell them what was wrong.

    `canonical` is also what keys the OTP and the rate limiter. That matters
    twice over: it means a code requested as `9822062252` verifies as
    `+91 98220 62252`, and it closes a rate-limit bypass, since the three
    spellings used to be three separate buckets.
    """
    canonical = normalize_msisdn(raw)
    variants = match_variants(raw)
    return canonical, variants

def set_otp(phone: str, otp: str):
    r = get_redis()
    key = f"otp:{phone}"
    if r:
        try:
            r.set(key, otp, ex=300)
            return
        except:
            pass
    _mem_set(key, otp, ex=300)

def get_otp(phone: str) -> Optional[str]:
    r = get_redis()
    key = f"otp:{phone}"
    if r:
        try:
            return r.get(key)
        except:
            pass
    return _mem_get(key)

def delete_otp(phone: str):
    r = get_redis()
    key = f"otp:{phone}"
    if r:
        try:
            r.delete(key)
        except:
            pass
    _mem_delete(key)

class OTPRequest(BaseModel):
    mobile_number: str

class OTPVerify(BaseModel):
    mobile_number: str
    otp: str

@router.post("/request-otp")
async def request_otp(data: OTPRequest):
    phone, variants = _login_identity(data.mobile_number)
    if not phone:
        # Nothing dialable was typed. Same generic answer as an unregistered
        # number -- this endpoint deliberately tells the caller nothing.
        return {"message": "If this number is registered, an OTP has been sent via WhatsApp."}

    if not check_rate_limit(f"otp-req:{phone}", max_requests=3, window_seconds=300):
        raise HTTPException(status_code=429, detail="Too many OTP requests. Please wait a few minutes and try again.")

    # Response is identical whether or not this number is registered --
    # returning 404 only for unregistered numbers is a direct oracle for
    # enumerating which phone numbers are onboarded traders/CAs. An OTP is
    # only actually generated and sent when the number IS registered; the
    # caller can't tell the difference from the response alone.
    GENERIC_RESPONSE = {"message": "If this number is registered, an OTP has been sent via WhatsApp."}

    try:
        db = get_supabase()
        # Match every spelling the number might be stored under, not just the
        # one that was typed.
        res_trader = db.table("traders").select("id, language_pref").in_("whatsapp_number", variants).execute()
        res_ca = db.table("traders").select("id, language_pref").in_("ca_whatsapp_number", variants).execute()
    except Exception as e:
        logger.error(f"DB Error: {e}")
        return GENERIC_RESPONSE

    if not res_trader.data and not res_ca.data:
        return GENERIC_RESPONSE

    # Generate OTP
    otp = str(random.randint(100000, 999999))

    # In development, print the OTP to the terminal since WhatsApp won't deliver it
    from app.config import get_settings
    if get_settings().debug:
        logger.info("=" * 40)
        logger.info(f"DEMO OTP FOR {phone}: {otp}")
        logger.info("=" * 40)

    # Store OTP with 5 min expiry via Redis/Memory
    set_otp(phone, otp)

    # Fetch user language preference
    lang = "en"
    if res_trader.data:
        lang = res_trader.data[0].get("language_pref") or "en"
    elif res_ca.data:
        lang = res_ca.data[0].get("language_pref") or "en"

    if lang == "hi":
        msg = f"Aapka Munim.ai verification code hai: *{otp}*. Ise kisi ke saath share na karein."
    elif lang == "mr":
        msg = f"Tumcha Munim.ai verification code aahe: *{otp}*. Ha code konashihi share karu naka."
    elif lang == "gu":
        msg = f"Tamaro Munim.ai verification code chhe: *{otp}*. Aa code koi pan sathe share na karo."
    else:
        msg = f"Your Munim.ai verification code is: *{otp}*. Do not share this with anyone."

    # Send via WhatsApp
    await whatsapp.send_text_message(phone, msg)

    return GENERIC_RESPONSE

@router.post("/verify-otp")
async def verify_otp(data: OTPVerify):
    # Canonical form, so a code requested under one spelling verifies under
    # another -- the OTP cache is keyed on this.
    phone, variants = _login_identity(data.mobile_number)
    otp_submitted = data.otp.strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Enter a valid mobile number.")

    if not check_rate_limit(f"otp-verify:{phone}", max_requests=5, window_seconds=300):
        raise HTTPException(status_code=429, detail="Too many attempts. Please request a new OTP.")

    record = get_otp(phone)

    from app.config import get_settings
    settings = get_settings()

    # Demo bypass exists so a live demo survives WhatsApp's 24h re-engagement
    # window. It must never be reachable outside a debug build.
    demo_bypass = settings.debug and otp_submitted == "123456"

    if not demo_bypass:
        if not record:
            raise HTTPException(status_code=400, detail="No active OTP found or expired. Please request a new one.")

        if record != otp_submitted:
            raise HTTPException(status_code=400, detail="Invalid OTP.")

    # Success
    delete_otp(phone)
    
    # Fetch user data to return. `roles` tells the frontend whether this
    # phone number needs a "log in as Trader / CA" choice: it's their own
    # number on a traders row (role "trader") and/or another trader's
    # ca_whatsapp_number (role "ca") -- the two are independent checks, not
    # mutually exclusive, so a person who is both their own trader AND
    # someone else's CA (a real case in the seed data, see CLAUDE.md) gets
    # both roles back rather than whichever check happened to run first.
    trader = None
    roles = []
    try:
        db = get_supabase()
        res_trader = db.table("traders").select("*").in_("whatsapp_number", variants).execute()
        res_ca = db.table("traders").select("id").in_("ca_whatsapp_number", variants).execute()

        if res_trader.data:
            trader = res_trader.data[0]
            roles.append("trader")
        if res_ca.data:
            roles.append("ca")
            if not trader:
                # No own-trader row -- this number only exists as a CA
                # identifier, so fall back to the first client record the
                # same way this endpoint always has.
                full_ca = db.table("traders").select("*").in_("ca_whatsapp_number", variants).execute()
                trader = full_ca.data[0] if full_ca.data else None
    except Exception as e:
        # This used to swallow the error and still return 200 "Login
        # successful." with a null token — the frontend stored the null and
        # every subsequent call 401'd, bouncing the user back to login with
        # nothing to explain why. A DB outage is a 503, not a login.
        logger.error(f"verify_otp: trader lookup failed for {phone}: {e}")
        raise HTTPException(
            status_code=503,
            detail="Could not reach the account service. Please try again in a moment.",
        )

    if not trader:
        # OTP was valid but this number matches no trader row and is nobody's
        # CA — there is no identity to mint a token for, so never claim success.
        raise HTTPException(status_code=401, detail="No account is registered for this number.")

    import jwt

    payload = {
        "sub": trader["id"],
        "jti": str(uuid.uuid4()),
        "exp": datetime.utcnow() + timedelta(days=365),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

    return {
        "message": "Login successful.",
        "trader": trader,
        "token": token,
        "roles": roles,
    }


@router.post("/logout")
async def logout(payload: dict = Depends(get_current_token_payload)):
    """
    Revoke the caller's current token. Tokens issued before jti support was
    added have no jti to revoke — logging out with one of those is a no-op
    on the server side (the client should still discard it locally).
    """
    jti = payload.get("jti")
    if jti:
        exp = payload.get("exp")
        ttl = max(int(exp - time.time()), 1) if exp else 3600
        revoke_token(jti, ttl)

    return {"message": "Logged out successfully."}
