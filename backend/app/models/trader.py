"""
Munim.ai — Pydantic Models for Traders and Suppliers
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class SupplierFlagType(str, Enum):
    MISSED_FILING = "MISSED_FILING"
    HABITUAL_LATE = "HABITUAL_LATE"
    ERRATIC_FILER = "ERRATIC_FILER"
    ITC_GHOST = "ITC_GHOST"
    GSTIN_CANCELLED = "GSTIN_CANCELLED"
    SCHEME_SWITCH = "SCHEME_SWITCH"
    EINVOICE_NON_COMPLIANT = "EINVOICE_NON_COMPLIANT"
    CANCELLATION_RISK = "CANCELLATION_RISK"
    NEW_GSTIN_RISK = "NEW_GSTIN_RISK"
    SECTOR_RISK = "SECTOR_RISK"


class ConversationState(str, Enum):
    IDLE = "idle"
    AWAITING_GSTIN = "awaiting_gstin"
    AWAITING_INVOICE = "awaiting_invoice"
    PROCESSING = "processing"
    AWAITING_CLARIFICATION = "awaiting_clarification"


class TraderCreate(BaseModel):
    whatsapp_number: str
    name: Optional[str] = None
    gstin: Optional[str] = None
    business_name: Optional[str] = None
    language_pref: str = "hi"
    ca_whatsapp_number: Optional[str] = None


class TraderResponse(BaseModel):
    id: str
    whatsapp_number: str
    name: Optional[str] = None
    gstin: Optional[str] = None
    business_name: Optional[str] = None
    language_pref: str = "hi"
    ca_whatsapp_number: Optional[str] = None
    created_at: Optional[str] = None


class SupplierResponse(BaseModel):
    id: str
    gstin: str
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    taxpayer_type: Optional[str] = None
    registration_date: Optional[str] = None
    business_category: Optional[str] = None
    is_einvoice_mandated: bool = False
    health_score: int = 100
    last_verified_at: Optional[str] = None
    flags: list[str] = Field(default_factory=list)


class SupplierFlag(BaseModel):
    supplier_id: str
    flag_type: SupplierFlagType
    metadata: dict = Field(default_factory=dict)
    is_active: bool = True


class SupplierHealthUpdate(BaseModel):
    supplier_id: str
    health_score: int
    flags: list[SupplierFlagType] = Field(default_factory=list)


# --- Dashboard Models ---

class ITCBucket(BaseModel):
    confirmed: float = 0.0
    fixable_blocked: float = 0.0
    at_risk: float = 0.0
    missed: float = 0.0
    ineligible: float = 0.0


class DashboardSummary(BaseModel):
    trader_id: str
    month: int
    year: int
    itc_buckets: ITCBucket
    invoices_processed: int = 0
    suppliers_monitored: int = 0
    issues_open: int = 0
    total_recovery_possible: float = 0.0


class ActionItem(BaseModel):
    id: str
    invoice_id: Optional[str] = None
    supplier_name: Optional[str] = None
    issue: str
    impact_amount: float
    fix_action: str
    deadline: Optional[str] = None
    priority: int = 0  # lower = higher priority
