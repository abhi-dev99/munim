import logging
import random
from typing import Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status
from app.services.supabase_client import get_supabase
from app.services import whatsapp

from app.services.redis_cache import get_redis, _mem_set, _mem_get, _mem_delete

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
logger = logging.getLogger(__name__)

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
    phone = data.mobile_number.strip().replace("+", "").replace(" ", "")
    
    # Optional: ensure number exists in DB
    db = get_supabase()
    
    # Check if number belongs to a trader OR is listed as a CA for a trader
    res_trader = db.table("traders").select("id").eq("whatsapp_number", phone).execute()
    res_ca = db.table("traders").select("id").eq("ca_whatsapp_number", phone).execute()
    
    if not res_trader.data and not res_ca.data:
        raise HTTPException(status_code=404, detail="Mobile number not registered.")

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
    
    # Send via WhatsApp
    msg = f"Your Munim.ai verification code is: *{otp}*. Do not share this with anyone."
    await whatsapp.send_text_message(phone, msg)
    
    return {"message": "OTP sent successfully via WhatsApp."}

@router.post("/verify-otp")
async def verify_otp(data: OTPVerify):
    phone = data.mobile_number.strip().replace("+", "").replace(" ", "")
    otp_submitted = data.otp.strip()
    
    record = get_otp(phone)
    if not record:
        raise HTTPException(status_code=400, detail="No active OTP found or expired. Please request a new one.")
        
    if record != otp_submitted:
        raise HTTPException(status_code=400, detail="Invalid OTP.")
        
    # Success
    delete_otp(phone)
    
    # Fetch user data to return
    db = get_supabase()
    res_trader = db.table("traders").select("*").eq("whatsapp_number", phone).execute()
    
    if res_trader.data:
        trader = res_trader.data[0]
    else:
        res_ca = db.table("traders").select("*").eq("ca_whatsapp_number", phone).execute()
        trader = res_ca.data[0] if res_ca.data else None
    
    import jwt
    from app.config import get_settings
    settings = get_settings()
    
    token = None
    if trader:
        payload = {
            "sub": trader["id"],
            "exp": datetime.utcnow() + timedelta(days=7),
            "iat": datetime.utcnow(),
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    
    return {
        "message": "Login successful.",
        "trader": trader,
        "token": token
    }
