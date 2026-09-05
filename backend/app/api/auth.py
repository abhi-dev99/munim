import logging
import random
from typing import Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status
from app.services.supabase_client import get_supabase
from app.services import whatsapp

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
logger = logging.getLogger(__name__)

# In-memory OTP store for demo
# Format: { "919822062252": {"otp": "123456", "expires_at": datetime} }
otp_store: Dict[str, dict] = {}

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
    
    # Store OTP with 5 min expiry
    otp_store[phone] = {
        "otp": otp,
        "expires_at": datetime.now() + timedelta(minutes=5)
    }
    
    # Send via WhatsApp
    msg = f"Your Munim.ai verification code is: *{otp}*. Do not share this with anyone."
    await whatsapp.send_text_message(phone, msg)
    
    return {"message": "OTP sent successfully via WhatsApp."}

@router.post("/verify-otp")
async def verify_otp(data: OTPVerify):
    phone = data.mobile_number.strip().replace("+", "").replace(" ", "")
    otp_submitted = data.otp.strip()
    
    record = otp_store.get(phone)
    if not record:
        raise HTTPException(status_code=400, detail="No active OTP found for this number. Please request a new one.")
        
    if datetime.now() > record["expires_at"]:
        del otp_store[phone]
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")
        
    if record["otp"] != otp_submitted:
        raise HTTPException(status_code=400, detail="Invalid OTP.")
        
    # Success
    del otp_store[phone]
    
    # Fetch user data to return
    db = get_supabase()
    res_trader = db.table("traders").select("*").eq("whatsapp_number", phone).execute()
    
    if res_trader.data:
        trader = res_trader.data[0]
    else:
        res_ca = db.table("traders").select("*").eq("ca_whatsapp_number", phone).execute()
        trader = res_ca.data[0] if res_ca.data else None
    
    return {
        "message": "Login successful.",
        "trader": trader
    }
