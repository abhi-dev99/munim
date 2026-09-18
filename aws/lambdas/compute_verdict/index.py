"""
munim-compute-verdict — Step Functions task Lambda.

Ports backend/app/domain/itc_engine.py and fraud.py verbatim (same rule
logic, same section citations, same thresholds) into a dependency-free
Lambda: no pydantic, no app.config, no Supabase. Plain dataclasses stand
in for the real Pydantic models purely so attribute access
(`invoice.total_tax_amount`, `item.hsn_code`, ...) still works exactly as
written in the original engine -- the actual GST logic below is
unmodified.

Deliberately NOT ported yet, because the supporting data doesn't exist in
DynamoDB: HSN rate-mismatch validation (needs the 21,934-row HSN master),
GSTIN registration/business-category lookup (needs the deepvue.tech
integration), and GSTR-2B reconciliation (needs 2B upload data). Each is
passed as an honest empty/None rather than faked -- the engine already
handles "no data" gracefully (e.g. an unverified GSTIN just skips that
check) because it has to for a real invoice with incomplete data anyway.
"""

import math
import os
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional


# ---- Minimal stand-ins for backend/app/models/invoice.py ----

@dataclass
class LineItem:
    description: str = ""
    hsn_code: Optional[str] = None
    igst_amount: Optional[float] = 0.0


@dataclass
class InvoiceJSON:
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    gstin_supplier: Optional[str] = None
    gstin_buyer: Optional[str] = None
    supplier_name: Optional[str] = None
    line_items: list = field(default_factory=list)
    total_tax_amount: Optional[float] = None
    total_amount: Optional[float] = None
    is_paid: bool = True


@dataclass
class ITCVerdict:
    status: str = "CONFIRMED"
    itc_amount: float = 0.0
    itc_blocked: float = 0.0
    reason: str = ""
    legal_section: Optional[str] = None
    fix_action: Optional[str] = None


@dataclass
class FraudSignal:
    signal_name: str
    triggered: bool = False
    score_contribution: int = 0
    detail: str = ""


@dataclass
class FraudResult:
    total_score: int = 0
    signals: list = field(default_factory=list)
    is_hard_flag: bool = False
    is_soft_flag: bool = False


# ---- Verbatim from backend/app/domain/itc_engine.py ----

class ITCRulesEngine:
    BLOCKED_HSN_PREFIXES = {
        "8703": "Motor vehicles (passenger, <=13 persons)",
        "8802": "Aircraft",
        "8901": "Vessels",
        "2101": "Food & beverages (outdoor catering)",
        "2106": "Food preparations",
        "3304": "Beauty/skin care products",
        "3305": "Hair care products",
        "9963": "Health/fitness services (gyms, clubs, spa)",
        "9964": "Accommodation services (hotels, personal stay)",
        "9971": "Insurance services (non-employee)",
        "9972": "Real estate services",
        "9996": "Club/membership services",
    }

    BLOCKED_KEYWORDS = [
        "motor vehicle", "passenger car", "beauty treatment", "health club",
        "membership fee", "outdoor catering", "personal consumption",
        "gift", "free sample",
    ]

    GSTR2B_AVAILABILITY_DAY = 14
    ITC_CLAIM_DEADLINE_MONTHS = 18
    PAYMENT_RULE_DAYS = 180
    NON_GSTR1_FILER_TYPES = {"composition", "uin holders", "non resident"}

    def is_blocked_category(self, hsn_code, description=""):
        if hsn_code:
            for prefix, reason in self.BLOCKED_HSN_PREFIXES.items():
                if hsn_code.startswith(prefix):
                    return True, f"Section 17(5): {reason}"
        description_lower = description.lower()
        for keyword in self.BLOCKED_KEYWORDS:
            if keyword in description_lower:
                return True, f"Section 17(5): Contains blocked category keyword '{keyword}'"
        return False, ""

    def is_valid_tax_invoice(self, invoice):
        if not all([
            invoice.invoice_number, invoice.invoice_date,
            invoice.gstin_supplier, invoice.total_amount and invoice.total_amount > 0,
        ]):
            return False
        try:
            if date.fromisoformat(invoice.invoice_date) > date.today():
                return False
        except (ValueError, TypeError):
            pass
        return True

    def is_within_time_limit(self, invoice_date_str):
        if not invoice_date_str:
            return True
        try:
            inv_date = date.fromisoformat(invoice_date_str)
            fy_end_year = inv_date.year + 1 if inv_date.month >= 4 else inv_date.year
            statutory_deadline = date(fy_end_year, 11, 30)
            return date.today() <= statutory_deadline
        except (ValueError, TypeError):
            return True

    def is_within_payment_window(self, invoice_date_str, is_paid=True):
        if not invoice_date_str or is_paid:
            return True
        try:
            inv_date = date.fromisoformat(invoice_date_str)
            cutoff = inv_date + timedelta(days=self.PAYMENT_RULE_DAYS)
            return date.today() <= cutoff
        except (ValueError, TypeError):
            return True

    def compute_verdict(self, invoice, is_rcm=False):
        total_tax = invoice.total_tax_amount or 0.0

        if not invoice.gstin_supplier or invoice.gstin_supplier.strip().upper() == "URD":
            if invoice.total_tax_amount and invoice.total_tax_amount > 0:
                return ITCVerdict(
                    status="FIXABLE_BLOCKED", itc_amount=0.0, itc_blocked=total_tax,
                    reason="Defective Invoice: GST charged but supplier GSTIN is missing.",
                    legal_section="16(2)(a)",
                    fix_action="Ask supplier for a revised invoice containing their GSTIN.",
                )
            return ITCVerdict(
                status="INELIGIBLE", itc_amount=0.0, itc_blocked=0.0,
                reason="Unregistered Dealer (URD) Purchase: Exempt/Non-GST.",
                legal_section="Exempt", fix_action="No action needed. Logged as URD expense.",
            )

        for item in invoice.line_items:
            blocked, reason = self.is_blocked_category(item.hsn_code, item.description)
            if blocked:
                return ITCVerdict(status="INELIGIBLE", itc_amount=0.0, itc_blocked=total_tax, reason=reason, legal_section="17(5)")

        if not self.is_valid_tax_invoice(invoice):
            return ITCVerdict(
                status="FIXABLE_BLOCKED", itc_amount=0.0, itc_blocked=total_tax,
                reason="Invalid tax invoice — missing required fields", legal_section="16(2)(a)",
                fix_action="Get a corrected invoice from the supplier with all mandatory fields",
            )

        if not self.is_within_time_limit(invoice.invoice_date):
            return ITCVerdict(status="INELIGIBLE", itc_amount=0.0, itc_blocked=total_tax, reason="ITC claim time limit expired (Section 16(4))", legal_section="16(4)")

        is_paid = getattr(invoice, "is_paid", True)
        if not self.is_within_payment_window(invoice.invoice_date, is_paid=is_paid):
            return ITCVerdict(
                status="AT_RISK", itc_amount=total_tax, itc_blocked=0.0,
                reason="Invoice >180 days old: verify supplier payment status (Section 16(2) 2nd Proviso)",
                legal_section="16(2)",
                fix_action="If unpaid >180 days, ITC reversal with interest is statutory; confirm payment status to clear warning.",
            )

        # HSN rate-mismatch (Check 10), GSTIN-validity (Check 3), GSTR-2B
        # reconciliation (Checks 5-8) intentionally omitted -- no HSN
        # master, GSTIN API, or 2B data wired up yet. See module docstring.

        return ITCVerdict(status="CONFIRMED", itc_amount=total_tax, itc_blocked=0.0, reason="All Section 16 conditions met — ITC eligible", legal_section="16(2)")


# ---- Verbatim from backend/app/domain/fraud.py ----

class FraudScorer:
    WEIGHTS = {
        "gstin_age": 20, "benfords_law": 15, "sequential_invoices": 15,
        "business_mismatch": 15, "geographic_mismatch": 15, "velocity_anomaly": 20,
    }
    BENFORD_EXPECTED = {1: 0.301, 2: 0.176, 3: 0.125, 4: 0.097, 5: 0.079, 6: 0.067, 7: 0.058, 8: 0.051, 9: 0.046}
    BENFORD_CHI2_CRITICAL = 15.507
    BENFORD_EFFECT_SMALL = 0.1
    BENFORD_EFFECT_LARGE = 0.5

    def score_benfords_law(self, historical_amounts, min_sample_size=20):
        signal = FraudSignal(signal_name="benfords_law", detail="Insufficient data for Benford's test" if len(historical_amounts) < min_sample_size else "Benford's distribution normal")
        if len(historical_amounts) < min_sample_size:
            return signal
        leading_digits = []
        for amount in historical_amounts:
            if amount > 0:
                d = str(abs(amount)).lstrip("0").replace(".", "")
                if d and 1 <= int(d[0]) <= 9:
                    leading_digits.append(int(d[0]))
        if len(leading_digits) < min_sample_size:
            return signal
        counter = Counter(leading_digits)
        total = len(leading_digits)
        observed = {d: counter.get(d, 0) / total for d in range(1, 10)}
        chi_sq = total * sum(((observed.get(d, 0) - self.BENFORD_EXPECTED[d]) ** 2) / self.BENFORD_EXPECTED[d] for d in range(1, 10))
        if chi_sq > self.BENFORD_CHI2_CRITICAL:
            effect_size = math.sqrt(chi_sq / total)
            band = (effect_size - self.BENFORD_EFFECT_SMALL) / (self.BENFORD_EFFECT_LARGE - self.BENFORD_EFFECT_SMALL)
            weight = self.WEIGHTS["benfords_law"]
            severity = int(round(weight * min(1.0, max(0.0, band))))
            signal.triggered = True
            signal.score_contribution = max(1, min(severity, weight))
            signal.detail = f"Benford's Law violation detected (chi2={chi_sq:.2f} over n={total}, effect size w={effect_size:.2f})"
        return signal

    def score_sequential_invoices(self, invoice_numbers, supplier_gstin, min_invoices=3):
        signal = FraudSignal(signal_name="sequential_invoices", detail="Invoice number sequence check passed")
        if len(invoice_numbers) < min_invoices:
            return signal
        numeric_parts = sorted(int("".join(c for c in n if c.isdigit())) for n in invoice_numbers if any(c.isdigit() for c in n))
        if len(numeric_parts) < min_invoices:
            return signal
        consecutive_count = max_consecutive = 0
        for i in range(1, len(numeric_parts)):
            if numeric_parts[i] - numeric_parts[i - 1] == 1:
                consecutive_count += 1
                max_consecutive = max(max_consecutive, consecutive_count)
            else:
                consecutive_count = 0
        if max_consecutive >= min_invoices - 1:
            signal.triggered = True
            signal.score_contribution = self.WEIGHTS["sequential_invoices"]
            signal.detail = f"Found {max_consecutive + 1} strictly sequential invoice numbers from supplier {supplier_gstin}"
        return signal

    def score_velocity_anomaly(self, current_amount, historical_amounts, spike_multiplier=5.0):
        signal = FraudSignal(signal_name="velocity_anomaly", detail="Velocity check passed")
        if not historical_amounts:
            return signal
        avg = sum(historical_amounts) / len(historical_amounts)
        if avg == 0:
            return signal
        ratio = current_amount / avg
        if ratio > spike_multiplier:
            severity = min(100, int((ratio / 10) * 100))
            signal.triggered = True
            signal.score_contribution = min(severity, self.WEIGHTS["velocity_anomaly"])
            signal.detail = f"Invoice Rs.{current_amount:,.0f} is {ratio:.1f}x the historical average Rs.{avg:,.0f} from this supplier"
        return signal

    def compute_fraud_score(self, invoice, historical_amounts=None, supplier_invoice_numbers=None, hard_threshold=None, soft_threshold=None):
        hard_threshold = hard_threshold if hard_threshold is not None else int(os.environ.get("FRAUD_HARD_THRESHOLD", 70))
        soft_threshold = soft_threshold if soft_threshold is not None else int(os.environ.get("FRAUD_SOFT_THRESHOLD", 40))

        if not invoice.total_tax_amount or invoice.total_tax_amount == 0.0:
            return FraudResult(total_score=0, signals=[], is_hard_flag=False, is_soft_flag=False)

        total_amount = invoice.total_amount or 0.0
        signals = [
            # GSTIN-age and business-mismatch signals need the deepvue.tech
            # GSTIN API, not wired up yet -- an untriggered placeholder is
            # honest here; a fabricated score would not be.
            FraudSignal(signal_name="gstin_age", detail="No GSTIN registration data available yet"),
            self.score_benfords_law(historical_amounts or []),
            self.score_sequential_invoices(supplier_invoice_numbers or [], invoice.gstin_supplier or ""),
            FraudSignal(signal_name="business_mismatch", detail="No GSTIN business-category data available yet"),
            FraudSignal(signal_name="geographic_mismatch", detail="No buyer GSTIN available yet"),
            self.score_velocity_anomaly(total_amount, historical_amounts or []),
        ]
        total_score = min(sum(s.score_contribution for s in signals), 100)
        return FraudResult(
            total_score=total_score, signals=signals,
            is_hard_flag=total_score >= hard_threshold,
            is_soft_flag=soft_threshold <= total_score < hard_threshold,
        )


itc_engine = ITCRulesEngine()
fraud_scorer = FraudScorer()


def handler(event, context):
    """event: the extracted-fields payload from munim-extract-invoice."""
    fields = event.get("extracted_fields", {})

    def field_value(name):
        return fields.get(name, {}).get("value")

    line_items = [
        LineItem(description=item.get("description", ""), hsn_code=item.get("hsn_code"))
        for item in event.get("line_items", [])
    ] or [LineItem(description="")]

    total_amount = _to_float(field_value("TOTAL"))
    total_tax = _to_float(field_value("TAX"))

    invoice = InvoiceJSON(
        invoice_number=field_value("INVOICE_RECEIPT_ID"),
        invoice_date=event.get("invoice_date_iso"),
        gstin_supplier=event.get("gstin_supplier"),
        supplier_name=field_value("VENDOR_NAME"),
        line_items=line_items,
        total_tax_amount=total_tax,
        total_amount=total_amount,
    )

    verdict = itc_engine.compute_verdict(invoice)
    fraud_result = fraud_scorer.compute_fraud_score(invoice)

    # A hard fraud flag overrides an otherwise-CONFIRMED verdict -- matches
    # the real product's ITCStatus.FRAUD_FLAGGED semantics.
    final_status = "FRAUD_FLAGGED" if fraud_result.is_hard_flag else verdict.status

    return {
        **event,
        "itc_verdict": {
            "status": final_status,
            "itc_amount": verdict.itc_amount,
            "itc_blocked": verdict.itc_blocked,
            "reason": verdict.reason,
            "legal_section": verdict.legal_section,
            "fix_action": verdict.fix_action,
        },
        "fraud_result": {
            "total_score": fraud_result.total_score,
            "is_hard_flag": fraud_result.is_hard_flag,
            "is_soft_flag": fraud_result.is_soft_flag,
            "signals": [
                {"signal_name": s.signal_name, "triggered": s.triggered, "score_contribution": s.score_contribution, "detail": s.detail}
                for s in fraud_result.signals
            ],
        },
    }


def _to_float(value):
    if not value:
        return None
    try:
        return float(str(value).replace(",", "").replace("Rs.", "").replace("$", "").strip())
    except ValueError:
        return None
