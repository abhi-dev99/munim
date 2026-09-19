from fastapi import HTTPException, Header, Depends, UploadFile, File, Form, BackgroundTasks
import jwt
from typing import Optional
from app.config import get_settings
from app.services.redis_cache import is_token_revoked
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

def _decode_token(authorization: Optional[str]) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")
    token = authorization.replace("Bearer ", "")
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_token_payload(authorization: str = Header(None)) -> dict:
    """Full decoded JWT payload for the caller's token (used where the
    caller needs claims beyond `sub`, e.g. `jti` for logout/revocation)."""
    return _decode_token(authorization)

def get_current_trader_id(authorization: str = Header(None)) -> str:
    payload = _decode_token(authorization)
    trader_id = payload.get("sub")
    if not trader_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Tokens issued before jti support was added have no jti and so can't
    # be individually revoked — that's an accepted limitation of the
    # migration, not a bug. Skip the check rather than crash on None.
    jti = payload.get("jti")
    if jti and is_token_revoked(jti):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    return trader_id

def _phone_variants(phone: str) -> list[str]:
    """Every spelling a CA's number might be stored under on their clients'
    `ca_whatsapp_number`. Delegates to services/phone so inbound lookup,
    outbound send and CA matching all agree on what "the same number" means —
    this used to be a second, sloppier implementation that mangled anything
    with a `+` or a space in it."""
    from app.services.phone import match_variants

    return match_variants(phone)


async def get_practice_client_ids(current_trader_id: str) -> list[str]:
    """
    Every trader the caller may act for: their own record, plus every client
    that names their phone number as its CA.

    Extracted because three places now need it (`/dashboard/traders`, the
    practice view, and `verify_trader_access` itself) and a fourth copy of a
    rule this load-bearing is how tenant-isolation bugs get in.
    """
    from app.services.supabase_client import get_supabase

    db = get_supabase()
    me = db.table("traders").select("whatsapp_number").eq("id", current_trader_id).execute()
    if not me.data:
        return []

    ids = {current_trader_id}
    variants = _phone_variants(me.data[0].get("whatsapp_number", ""))
    if variants:
        clients = db.table("traders").select("id").in_("ca_whatsapp_number", variants).execute()
        ids.update(c["id"] for c in (clients.data or []) if c.get("id"))
    return sorted(ids)


async def verify_trader_access(trader_id: str, current_trader_id: str = Depends(get_current_trader_id)) -> str:
    if trader_id == current_trader_id:
        return trader_id
        
    from app.services.supabase_client import get_supabase
    db = get_supabase()
    
    user_res = db.table("traders").select("whatsapp_number").eq("id", current_trader_id).execute()
    if not user_res.data:
        raise HTTPException(status_code=403, detail="Current user not found")
        
    # Same variant list the practice view uses. This was a third inline copy
    # of the 91-prefix rule; a tenant-isolation check is the last place that
    # should disagree with the rest of the codebase about what two numbers
    # being equal means.
    variants = _phone_variants(user_res.data[0].get("whatsapp_number", ""))
    if not variants:
        logger.warning(f"Access denied: user {current_trader_id} has no usable phone number")
        raise HTTPException(status_code=403, detail="Not authorized to access this trader's data")

    client_res = db.table("traders").select("id").eq("id", trader_id).in_("ca_whatsapp_number", variants).execute()
    
    if not client_res.data:
        logger.warning(f"Access denied: user {current_trader_id} tried to access trader {trader_id}")
        raise HTTPException(status_code=403, detail="Not authorized to access this trader's data")
        
    return trader_id
