"""
Munim.ai — Pydantic Models for Invoice Processing
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from enum import Enum


class ITCStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    FIXABLE_BLOCKED = "FIXABLE_BLOCKED"
    AT_RISK = "AT_RISK"
    MISSED = "MISSED"
    INELIGIBLE = "INELIGIBLE"
    FRAUD_FLAGGED = "FRAUD_FLAGGED"
    DUPLICATE = "DUPLICATE"


class GSTR2BMatchStatus(str, Enum):
    MATCHED = "MATCHED"
    PROBABLE_MATCH = "PROBABLE_MATCH"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    ITC_AT_RISK = "ITC_AT_RISK"
    MISSED_ITC = "MISSED_ITC"
    UNRECONCILED = "UNRECONCILED"


class InvoiceStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    VALIDATED = "validated"
    FLAGGED = "flagged"
    ERROR = "error"


class LineItem(BaseModel):
    description: str = ""
    hsn_code: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    taxable_value: Optional[float] = None
    cgst_rate: Optional[float] = 0.0
    sgst_rate: Optional[float] = 0.0
    igst_rate: Optional[float] = 0.0
    cgst_amount: Optional[float] = 0.0
    sgst_amount: Optional[float] = 0.0
    igst_amount: Optional[float] = 0.0


class InvoiceJSON(BaseModel):
    """Structured invoice data extracted by Gemini Vision."""
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None  # YYYY-MM-DD
    gstin_supplier: Optional[str] = None
    gstin_buyer: Optional[str] = None
    supplier_name: Optional[str] = None
    line_items: list[LineItem] = Field(default_factory=list)
    total_taxable_amount: Optional[float] = None
    total_tax_amount: Optional[float] = None
    total_amount: Optional[float] = None
    confidence: Optional[float] = None


class HSNValidationResult(BaseModel):
    hsn_code_extracted: str
    hsn_code_validated: Optional[str] = None
    is_valid: bool = False
    suggestion: Optional[str] = None
    suggestion_description: Optional[str] = None
    confidence: Optional[float] = None
    tax_rate_applied: Optional[float] = None
    tax_rate_correct: Optional[float] = None
    rate_mismatch: bool = False
    itc_delta: Optional[float] = None  # ₹ impact


class GSTINValidation(BaseModel):
    gstin: str
    is_valid: bool = False
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    taxpayer_type: Optional[str] = None
    registration_date: Optional[str] = None
    business_category: Optional[str] = None
    is_active: bool = False
    is_einvoice_mandated: bool = False
    filing_status: Optional[str] = None
    cached: bool = False


class GSTR2BMatchResult(BaseModel):
    status: GSTR2BMatchStatus = GSTR2BMatchStatus.UNRECONCILED
    confidence: float = 0.0
    matched_record_id: Optional[str] = None
    itc_amount: Optional[float] = None


class FraudSignal(BaseModel):
    signal_name: str
    triggered: bool = False
    score_contribution: int = 0
    detail: str = ""


class FraudResult(BaseModel):
    total_score: int = 0  # 0-100
    signals: list[FraudSignal] = Field(default_factory=list)
    is_hard_flag: bool = False
    is_soft_flag: bool = False


class ITCVerdict(BaseModel):
    status: ITCStatus = ITCStatus.CONFIRMED
    itc_amount: float = 0.0
    itc_blocked: float = 0.0
    reason: str = ""
    legal_section: Optional[str] = None
    fix_action: Optional[str] = None


class InvoiceDiagnosis(BaseModel):
    """Final diagnosis sent back to trader."""
    invoice_id: Optional[str] = None
    trader_id: str
    supplier_name: Optional[str] = None
    total_amount: Optional[float] = None
    invoice_json: Optional["InvoiceJSON"] = None  # Raw extracted data
    itc_verdict: ITCVerdict
    hsn_validations: list[HSNValidationResult] = Field(default_factory=list)
    gstin_validation: Optional[GSTINValidation] = None
    gstr2b_match: Optional[GSTR2BMatchResult] = None
    fraud_result: Optional[FraudResult] = None
    diagnosis_hi: str = ""
    diagnosis_en: str = ""
    action_items: list[str] = Field(default_factory=list)
    processing_duration_ms: int = 0
