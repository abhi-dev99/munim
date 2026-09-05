from fastapi import HTTPException, Header, Depends, UploadFile, File, Form, BackgroundTasks
import jwt
from typing import Optional
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

def get_current_trader_id(authorization: str = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        trader_id = payload.get("sub")
        if not trader_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return trader_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

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
