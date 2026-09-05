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

async def verify_trader_access(trader_id: str, current_trader_id: str = Depends(get_current_trader_id)) -> str:
    if trader_id == current_trader_id:
        return trader_id
        
    from app.services.supabase_client import get_supabase
    db = get_supabase()
    
    user_res = db.table("traders").select("whatsapp_number").eq("id", current_trader_id).execute()
    if not user_res.data:
        raise HTTPException(status_code=403, detail="Current user not found")
        
    phone = user_res.data[0].get("whatsapp_number", "")
    phone_full = phone if phone.startswith("91") else f"91{phone}"
    phone_10 = phone[-10:] if len(phone) >= 10 else phone
    
    client_res = db.table("traders").select("id").eq("id", trader_id).in_("ca_whatsapp_number", [phone_full, phone_10]).execute()
    
    if not client_res.data:
        logger.warning(f"Access denied: user {current_trader_id} tried to access trader {trader_id}")
        raise HTTPException(status_code=403, detail="Not authorized to access this trader's data")
        
    return trader_id
