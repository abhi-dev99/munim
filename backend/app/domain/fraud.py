"""
Munim.ai — Multi-Variate Fraud Scoring Engine
Six independent signals weighted into a composite fraud score (0-100).
Pure statistical/rule-based — NO LLM.
"""

import math
import logging
from collections import Counter
from datetime import date, timedelta
from typing import Optional

from app.models.invoice import FraudResult, FraudSignal, InvoiceJSON, GSTINValidation

logger = logging.getLogger(__name__)


class FraudScorer:
    """
    Computes fraud score for an inbound invoice using six signals:
    1. GSTIN Age (new GSTIN + high value)
    2. Benford's Law (digit distribution anomaly)
    3. Sequential Invoice Numbers
    4. Business Type Mismatch (requires GSTIN API data)
    5. Geographic Mismatch (state code from GSTIN)
    6. Velocity Anomaly (sudden amount spike)
    """

    # Signal weights (must sum to 100)
    WEIGHTS = {
        "gstin_age": 20,
        "benfords_law": 15,
        "sequential_invoices": 15,
        "business_mismatch": 15,
        "geographic_mismatch": 15,
        "velocity_anomaly": 20,
    }

    # Benford's Law expected distribution for leading digits 1-9
    BENFORD_EXPECTED = {
        1: 0.301, 2: 0.176, 3: 0.125, 4: 0.097, 5: 0.079,
        6: 0.067, 7: 0.058, 8: 0.051, 9: 0.046,
    }

    # High-fraud sectors (by NIC/business category keywords)
    HIGH_FRAUD_SECTORS = [
        "iron", "steel", "scrap", "textile", "chemical",
        "construction", "real estate", "pan masala", "gutkha",
    ]

    def score_gstin_age(
        self,
        gstin_validation: Optional[GSTINValidation],
        invoice_amount: float,
        high_value_threshold: float = 50000.0,
        new_gstin_days: int = 180,
    ) -> FraudSignal:
        """Signal 1: New GSTIN issuing high-value invoices."""
        signal = FraudSignal(
            signal_name="gstin_age",
            triggered=False,
            score_contribution=0,
            detail="GSTIN age check passed",
        )

        if not gstin_validation or not gstin_validation.registration_date:
            return signal

        try:
            reg_date = date.fromisoformat(gstin_validation.registration_date)
            age_days = (date.today() - reg_date).days
        except (ValueError, TypeError):
            return signal

        if age_days < new_gstin_days and invoice_amount > high_value_threshold:
            score = min(100, int((high_value_threshold / max(invoice_amount, 1)) * 100))
            score = 100 - score  # Invert: higher amount relative to threshold = higher risk
            signal.triggered = True
            signal.score_contribution = min(score, self.WEIGHTS["gstin_age"])
            signal.detail = (
                f"GSTIN is only {age_days} days old with invoice value ₹{invoice_amount:,.0f} "
                f"(threshold: ₹{high_value_threshold:,.0f})"
            )

        return signal

    def score_benfords_law(
        self,
        historical_amounts: list[float],
        min_sample_size: int = 20,
    ) -> FraudSignal:
        """Signal 2: Benford's Law — non-natural leading digit distribution."""
        signal = FraudSignal(
            signal_name="benfords_law",
            triggered=False,
            score_contribution=0,
            detail="Insufficient data for Benford's test" if len(historical_amounts) < min_sample_size else "Benford's distribution normal",
        )

        if len(historical_amounts) < min_sample_size:
            return signal

        # Extract leading digits
        leading_digits = []
        for amount in historical_amounts:
            if amount > 0:
                leading_digit = int(str(abs(amount)).lstrip("0").replace(".", "")[0])
                if 1 <= leading_digit <= 9:
                    leading_digits.append(leading_digit)

        if len(leading_digits) < min_sample_size:
            return signal

        # Compute observed distribution
        counter = Counter(leading_digits)
        total = len(leading_digits)
        observed = {d: counter.get(d, 0) / total for d in range(1, 10)}

        # Chi-squared statistic
        chi_sq = sum(
            ((observed.get(d, 0) - self.BENFORD_EXPECTED[d]) ** 2) / self.BENFORD_EXPECTED[d]
            for d in range(1, 10)
        )

        # Critical value for 8 df, p=0.05 is 15.507
        if chi_sq > 15.507:
            severity = min(100, int(chi_sq / 30 * 100))
            signal.triggered = True
            signal.score_contribution = min(severity, self.WEIGHTS["benfords_law"])
            signal.detail = f"Benford's Law violation detected (χ²={chi_sq:.2f}, critical=15.507)"

        return signal

    def score_sequential_invoices(
        self,
        invoice_numbers: list[str],
        supplier_gstin: str,
        min_invoices: int = 3,
    ) -> FraudSignal:
        """Signal 3: Sequential invoice numbers from same supplier suggest fake invoices."""
        signal = FraudSignal(
            signal_name="sequential_invoices",
            triggered=False,
            score_contribution=0,
            detail="Invoice number sequence check passed",
        )

        if len(invoice_numbers) < min_invoices:
            return signal

        # Extract numeric portions of invoice numbers
        numeric_parts = []
        for inv_num in invoice_numbers:
            digits = "".join(c for c in inv_num if c.isdigit())
            if digits:
                numeric_parts.append(int(digits))

        if len(numeric_parts) < min_invoices:
            return signal

        numeric_parts.sort()

        # Check for consecutive sequences
        consecutive_count = 0
        max_consecutive = 0
        for i in range(1, len(numeric_parts)):
            if numeric_parts[i] - numeric_parts[i - 1] == 1:
                consecutive_count += 1
                max_consecutive = max(max_consecutive, consecutive_count)
            else:
                consecutive_count = 0

        if max_consecutive >= min_invoices - 1:
            signal.triggered = True
            signal.score_contribution = self.WEIGHTS["sequential_invoices"]
            signal.detail = (
                f"Found {max_consecutive + 1} strictly sequential invoice numbers from "
                f"supplier {supplier_gstin}"
            )

        return signal

    def score_business_mismatch(
        self,
        gstin_validation: Optional[GSTINValidation],
        line_items: list,
    ) -> FraudSignal:
        """Signal 4: Supplier business category contradicts invoice line items."""
        signal = FraudSignal(
            signal_name="business_mismatch",
            triggered=False,
            score_contribution=0,
            detail="Business type check passed",
        )

        if not gstin_validation or not gstin_validation.business_category:
            return signal

        category_lower = gstin_validation.business_category.lower()
        
        mismatch_found = False
        mismatch_reason = ""
        
        for item in line_items:
            desc = item.description.lower()
            if "service" in category_lower and any(hw in desc for hw in ["steel", "iron", "cement", "hardware", "machinery", "fabric", "oil"]):
                mismatch_found = True
                mismatch_reason = f"Supplier is registered as '{gstin_validation.business_category}' but invoicing for goods ({item.description})"
                break
            if "manufacturing" in category_lower and "consulting" in desc:
                mismatch_found = True
                mismatch_reason = f"Supplier is registered as '{gstin_validation.business_category}' but invoicing for services ({item.description})"
                break

        if mismatch_found:
            signal.triggered = True
            signal.score_contribution = self.WEIGHTS["business_mismatch"]
            signal.detail = mismatch_reason

        return signal

    def score_geographic_mismatch(
        self,
        supplier_gstin: Optional[str],
        buyer_gstin: Optional[str],
        is_interstate: bool = False,
    ) -> FraudSignal:
        """Signal 5: Supplier GSTIN state ≠ buyer state without interstate flag."""
        signal = FraudSignal(
            signal_name="geographic_mismatch",
            triggered=False,
            score_contribution=0,
            detail="Geographic check passed",
        )

        if not supplier_gstin or not buyer_gstin:
            return signal

        # GSTIN first 2 chars = state code
        supplier_state = supplier_gstin[:2]
        buyer_state = buyer_gstin[:2]

        if supplier_state != buyer_state and not is_interstate:
            signal.triggered = True
            signal.score_contribution = self.WEIGHTS["geographic_mismatch"]
            signal.detail = (
                f"Supplier state ({supplier_state}) ≠ buyer state ({buyer_state}) "
                f"but no IGST charged (interstate flag missing)"
            )

        return signal

    def score_velocity_anomaly(
        self,
        current_amount: float,
        historical_amounts: list[float],
        spike_multiplier: float = 5.0,
    ) -> FraudSignal:
        """Signal 6: Invoice amount significantly exceeds supplier's historical average."""
        signal = FraudSignal(
            signal_name="velocity_anomaly",
            triggered=False,
            score_contribution=0,
            detail="Velocity check passed",
        )

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
            signal.detail = (
                f"Invoice ₹{current_amount:,.0f} is {ratio:.1f}x the historical average "
                f"₹{avg:,.0f} from this supplier"
            )

        return signal

    def compute_fraud_score(
        self,
        invoice: InvoiceJSON,
        gstin_validation: Optional[GSTINValidation] = None,
        historical_amounts: Optional[list[float]] = None,
        supplier_invoice_numbers: Optional[list[str]] = None,
        hard_threshold: int = 70,
        soft_threshold: int = 40,
    ) -> FraudResult:
        """
        Compute composite fraud score from all available signals.
        Returns FraudResult with individual signal breakdowns.
        """
        # Skip fraud scoring for Composition Scheme / Bill of Supply (Zero Tax)
        if not invoice.total_tax_amount or invoice.total_tax_amount == 0.0:
            return FraudResult(
                total_score=0,
                signals=[],
                is_hard_flag=False,
                is_soft_flag=False,
            )

        signals = []
        total_amount = invoice.total_amount or 0.0

        # Signal 1: GSTIN Age
        signals.append(
            self.score_gstin_age(gstin_validation, total_amount)
        )

        # Signal 2: Benford's Law
        signals.append(
            self.score_benfords_law(historical_amounts or [])
        )

        # Signal 3: Sequential Invoices
        signals.append(
            self.score_sequential_invoices(
                supplier_invoice_numbers or [],
                invoice.gstin_supplier or "",
            )
        )

        # Signal 4: Business Type Mismatch
        signals.append(
            self.score_business_mismatch(
                gstin_validation,
                invoice.line_items,
            )
        )

        # Signal 5: Geographic Mismatch
        has_igst = any(
            (item.igst_amount or 0) > 0 for item in invoice.line_items
        )
        signals.append(
            self.score_geographic_mismatch(
                invoice.gstin_supplier,
                invoice.gstin_buyer,
                is_interstate=has_igst,
            )
        )

        # Signal 6: Velocity Anomaly
        signals.append(
            self.score_velocity_anomaly(
                total_amount,
                historical_amounts or [],
            )
        )

        # Compute total
        total_score = sum(s.score_contribution for s in signals)
        total_score = min(total_score, 100)

        return FraudResult(
            total_score=total_score,
            signals=signals,
            is_hard_flag=total_score >= hard_threshold,
            is_soft_flag=soft_threshold <= total_score < hard_threshold,
        )
