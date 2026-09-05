"""
Munim.ai — GSTIN Verification Service
Verifies GSTINs via external API with Redis caching.
"""

import logging
from typing import Optional
from datetime import datetime

import httpx

from app.config import get_settings
from app.models.invoice import GSTINValidation
from app.services.redis_cache import cache_gstin, get_cached_gstin

logger = logging.getLogger(__name__)

settings = get_settings()


# GSTIN format: 2 digits state code + 10 digit PAN + 1 entity code + 1 Z + 1 check digit
def is_valid_gstin_format(gstin: str) -> bool:
    """Basic GSTIN format validation (15 alphanumeric characters)."""
    if not gstin or len(gstin) != 15:
        return False
    return gstin[:2].isdigit() and gstin.isalnum()


async def verify_gstin(gstin: str, use_cache: bool = True) -> GSTINValidation:
    """
    Verify a GSTIN via external API.
    Checks Redis cache first; on miss, calls the API and caches permanently.
    """

    # Format validation
    if not is_valid_gstin_format(gstin):
        return GSTINValidation(
            gstin=gstin,
            is_valid=False,
            is_active=False,
        )

    # Check Redis cache
    if use_cache:
        cached = get_cached_gstin(gstin)
        if cached:
            return GSTINValidation(**cached, cached=True)

    # Call external API
    try:
        result = await _call_gstin_api(gstin)

        # Cache the result
        if result.is_valid:
            cache_data = {
                "gstin": result.gstin,
                "is_valid": result.is_valid,
                "legal_name": result.legal_name,
                "trade_name": result.trade_name,
                "taxpayer_type": result.taxpayer_type,
                "registration_date": result.registration_date,
                "business_category": result.business_category,
                "is_active": result.is_active,
                "is_einvoice_mandated": result.is_einvoice_mandated,
                "filing_status": result.filing_status,
            }
            cache_gstin(gstin, cache_data)

        return result

    except Exception as e:
        logger.error(f"GSTIN verification failed for {gstin}: {e}")
        # Return a "mock" valid response for hackathon if API is unavailable
        return _mock_gstin_response(gstin)


async def _call_gstin_api(gstin: str) -> GSTINValidation:
    """Call the external GSTIN verification API."""
    url = f"{settings.gstin_api_base_url}/gstin/{gstin}"
    headers = {
        "Authorization": f"Bearer {settings.gstin_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=15)

        if response.status_code == 200:
            data = response.json()
            return GSTINValidation(
                gstin=gstin,
                is_valid=True,
                legal_name=data.get("legal_name", ""),
                trade_name=data.get("trade_name", ""),
                taxpayer_type=data.get("taxpayer_type", "Regular"),
                registration_date=data.get("registration_date"),
                business_category=data.get("business_category", ""),
                is_active=data.get("status", "").lower() == "active",
                is_einvoice_mandated=data.get("einvoice_mandated", False),
                filing_status=data.get("filing_status"),
            )
        else:
            logger.warning(f"GSTIN API returned {response.status_code} for {gstin}")
            return _mock_gstin_response(gstin)


def _mock_gstin_response(gstin: str) -> GSTINValidation:
    """
    Return a mock GSTIN validation for hackathon demo purposes.
    Uses the GSTIN format to infer state and generate plausible data.
    """
    state_codes = {
        "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
        "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana",
        "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
        "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
        "13": "Nagaland", "14": "Manipur", "15": "Mizoram",
        "16": "Tripura", "17": "Meghalaya", "18": "Assam",
        "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
        "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
        "27": "Maharashtra", "29": "Karnataka", "32": "Kerala",
        "33": "Tamil Nadu", "36": "Telangana", "37": "Andhra Pradesh",
    }

    state = state_codes.get(gstin[:2], "Unknown State")

    return GSTINValidation(
        gstin=gstin,
        is_valid=is_valid_gstin_format(gstin),
        legal_name=f"Demo Business ({state})",
        trade_name=f"Demo Trade ({state})",
        taxpayer_type="Regular",
        registration_date="2022-01-15",
        business_category="Trading",
        is_active=True,
        is_einvoice_mandated=False,
        filing_status="Filed",
        cached=False,
    )
