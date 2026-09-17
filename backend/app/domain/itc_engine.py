"""
Munim.ai — ITC Rules Engine
Deterministic ITC eligibility computation per GST Act Sections 16 & 17(5).
NO LLM involvement — pure rule-based logic.
"""

from datetime import date, timedelta
from typing import Optional

from app.models.invoice import (
    ITCVerdict,
    ITCStatus,
    InvoiceJSON,
    HSNValidationResult,
    GSTINValidation,
    GSTR2BMatchResult,
    GSTR2BMatchStatus,
)


class ITCRulesEngine:
    """
    Computes ITC eligibility for an invoice based on:
    - Section 17(5): Blocked categories (hard blocks)
    - Section 16(2): Conditions for ITC eligibility
    - HSN rate mismatch: Fixable blocks
    - Supplier compliance: At-risk flags
    """

    # Section 17(5) — Blocked ITC categories by HSN prefix
    BLOCKED_HSN_PREFIXES = {
        "8703": "Motor vehicles (passenger, ≤13 persons)",
        "8802": "Aircraft",
        "8901": "Vessels",
        "2101": "Food & beverages (outdoor catering)",
        "2106": "Food preparations",
        "3304": "Beauty/skin care products",
        "3305": "Hair care products",
        "9963": "Health/fitness services",
        "9971": "Insurance services (non-employee)",
        "9972": "Real estate services",
        "9996": "Club/membership services",
        "9963": "Accommodation services (personal)",
    }

    # Section 17(5) — Blocked categories by description keywords
    BLOCKED_KEYWORDS = [
        "motor vehicle",
        "passenger car",
        "beauty treatment",
        "health club",
        "membership fee",
        "outdoor catering",
        "personal consumption",
        "gift",
        "free sample",
    ]

    # Filing time limit: ITC must be claimed before due date of September
    # return following the end of the FY, or the annual return, whichever is earlier
    ITC_CLAIM_DEADLINE_MONTHS = 18  # ~18 months from invoice date (simplified)

    def is_blocked_category(self, hsn_code: Optional[str], description: str = "") -> tuple[bool, str]:
        """Check if HSN code or description falls under Section 17(5) blocked categories."""
        if hsn_code:
            for prefix, reason in self.BLOCKED_HSN_PREFIXES.items():
                if hsn_code.startswith(prefix):
                    return True, f"Section 17(5): {reason}"

        description_lower = description.lower()
        for keyword in self.BLOCKED_KEYWORDS:
            if keyword in description_lower:
                return True, f"Section 17(5): Contains blocked category keyword '{keyword}'"

        return False, ""

    def is_valid_tax_invoice(self, invoice: InvoiceJSON) -> bool:
        """Check basic validity of the tax invoice."""
        return all([
            invoice.invoice_number,
            invoice.invoice_date,
            invoice.gstin_supplier,
            invoice.total_amount and invoice.total_amount > 0,
        ])

    def is_within_time_limit(self, invoice_date_str: Optional[str]) -> bool:
        """Check if ITC claim is within the statutory time limit."""
        if not invoice_date_str:
            return True  # Assume valid if date unknown

        try:
            inv_date = date.fromisoformat(invoice_date_str)
            deadline = inv_date + timedelta(days=self.ITC_CLAIM_DEADLINE_MONTHS * 30)
            return date.today() <= deadline
        except (ValueError, TypeError):
            return True

    def compute_verdict(
        self,
        invoice: InvoiceJSON,
        hsn_validations: list[HSNValidationResult],
        gstin_validation: Optional[GSTINValidation],
        gstr2b_match: Optional[GSTR2BMatchResult],
    ) -> ITCVerdict:
        """
        Master ITC computation. Returns a single verdict for the invoice.
        Order of checks: Section 17(5) → Invoice validity → GSTIN → Time limit → 2B match → HSN
        """

        total_tax = invoice.total_tax_amount or 0.0

        # --- Check 1: Section 17(5) hard blocks ---
        for item in invoice.line_items:
            blocked, reason = self.is_blocked_category(
                item.hsn_code, item.description
            )
            if blocked:
                return ITCVerdict(
                    status=ITCStatus.INELIGIBLE,
                    itc_amount=0.0,
                    itc_blocked=total_tax,
                    reason=reason,
                    legal_section="17(5)",
                )

        # --- Check 2: Valid tax invoice (Section 16(2)(a)) ---
        if not self.is_valid_tax_invoice(invoice):
            return ITCVerdict(
                status=ITCStatus.FIXABLE_BLOCKED,
                itc_amount=0.0,
                itc_blocked=total_tax,
                reason="Invalid tax invoice — missing required fields",
                legal_section="16(2)(a)",
                fix_action="Get a corrected invoice from the supplier with all mandatory fields",
            )

        # --- Check 3: GSTIN validity ---
        if gstin_validation and not gstin_validation.is_valid:
            return ITCVerdict(
                status=ITCStatus.INELIGIBLE,
                itc_amount=0.0,
                itc_blocked=total_tax,
                reason=f"Supplier GSTIN {invoice.gstin_supplier} is invalid or cancelled",
                legal_section="16(2)",
            )

        if gstin_validation and not gstin_validation.is_active:
            return ITCVerdict(
                status=ITCStatus.INELIGIBLE,
                itc_amount=0.0,
                itc_blocked=total_tax,
                reason=f"Supplier GSTIN {invoice.gstin_supplier} is cancelled/suspended",
                legal_section="16(2)",
            )

        # --- Check 4: Time limit (Section 16(4)) ---
        if not self.is_within_time_limit(invoice.invoice_date):
            return ITCVerdict(
                status=ITCStatus.INELIGIBLE,
                itc_amount=0.0,
                itc_blocked=total_tax,
                reason="ITC claim time limit expired (Section 16(4))",
                legal_section="16(4)",
            )

        # --- Check 5: GSTR-2B reconciliation ---
        if gstr2b_match:
            if gstr2b_match.status == GSTR2BMatchStatus.ITC_AT_RISK:
                return ITCVerdict(
                    status=ITCStatus.AT_RISK,
                    itc_amount=total_tax,
                    itc_blocked=0.0,
                    reason="Invoice not found in GSTR-2B — supplier may not have filed",
                    legal_section="16(2)(c)",
                    fix_action="Contact supplier and ask them to file their GSTR-1",
                )
            elif gstr2b_match.status == GSTR2BMatchStatus.PROBABLE_MATCH:
                # Proceed but flag
                pass  # Will check HSN next
            elif gstr2b_match.status == GSTR2BMatchStatus.POSSIBLE_MATCH:
                pass  # Proceed with caution

        # --- Check 6: HSN rate mismatches (fixable blocks) ---
        total_itc_delta = 0.0
        mismatched_items = []
        for hsn_val in hsn_validations:
            if hsn_val.rate_mismatch and hsn_val.itc_delta:
                total_itc_delta += abs(hsn_val.itc_delta)
                mismatched_items.append(hsn_val)

        if mismatched_items:
            descriptions = "; ".join(
                f"HSN {v.hsn_code_extracted} → should be {v.hsn_code_validated or v.suggestion} "
                f"(rate {v.tax_rate_applied}% → {v.tax_rate_correct}%)"
                for v in mismatched_items
            )
            return ITCVerdict(
                status=ITCStatus.FIXABLE_BLOCKED,
                itc_amount=total_tax - total_itc_delta,
                itc_blocked=total_itc_delta,
                reason=f"HSN code/rate mismatch: {descriptions}",
                legal_section="16(2)",
                fix_action="Ask CA to correct HSN codes before filing",
            )

        # --- All checks passed ---
        return ITCVerdict(
            status=ITCStatus.CONFIRMED,
            itc_amount=total_tax,
            itc_blocked=0.0,
            reason="All Section 16 conditions met — ITC eligible",
            legal_section="16(2)",
        )
