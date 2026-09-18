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

def verify_trader_access(trader_id: str, current_trader_id: str = Depends(get_current_trader_id)) -> str:
    if trader_id != current_trader_id:
        logger.warning(f"Access denied: user {current_trader_id} tried to access trader {trader_id}")
        raise HTTPException(status_code=403, detail="Not authorized to access this trader's data")
    return trader_id
