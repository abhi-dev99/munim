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
    - Section 16(2) second proviso: 180-day payment rule
    - HSN rate mismatch: Fixable blocks
    - Supplier compliance: At-risk flags
    - Composition scheme & RCM gates: Prevent false positives
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
        "9963": "Health/fitness services (gyms, clubs, spa)",
        "9964": "Accommodation services (hotels, personal stay)",
        "9971": "Insurance services (non-employee)",
        "9972": "Real estate services",
        "9996": "Club/membership services",
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

    # GSTR-2B is published after the 14th of each month
    GSTR2B_AVAILABILITY_DAY = 14

    # Section 16(4) — 18-month approximate deadline
    ITC_CLAIM_DEADLINE_MONTHS = 18

    # Section 16(2) second proviso — 180-day payment rule
    PAYMENT_RULE_DAYS = 180

    # Taxpayer types that DO NOT file GSTR-1 (safe to exclude from AT_RISK nag)
    NON_GSTR1_FILER_TYPES = {
        "composition",
        "uin holders",      # UN/embassy-type registrations
        "non resident",
    }

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
        """Check if ITC claim is within the statutory time limit (Section 16(4))."""
        if not invoice_date_str:
            return True  # Assume valid if date unknown

        try:
            inv_date = date.fromisoformat(invoice_date_str)
            deadline = inv_date + timedelta(days=self.ITC_CLAIM_DEADLINE_MONTHS * 30)
            return date.today() <= deadline
        except (ValueError, TypeError):
            return True

    def is_within_payment_window(self, invoice_date_str: Optional[str]) -> bool:
        """
        Section 16(2) second proviso: ITC is not claimable if the supplier
        has not been paid within 180 days of the invoice date.
        Returns True if still within the payment window (ITC is safe),
        False if 180 days have elapsed (ITC must be reversed).
        """
        if not invoice_date_str:
            return True  # Can't determine — don't block

        try:
            inv_date = date.fromisoformat(invoice_date_str)
            cutoff = inv_date + timedelta(days=self.PAYMENT_RULE_DAYS)
            return date.today() <= cutoff
        except (ValueError, TypeError):
            return True

    def is_gstr2b_available_for_period(self, invoice_date_str: Optional[str]) -> bool:
        """
        GSTR-2B for a given invoice period is only published after the 14th
        of the following month. Before that date, absence of the invoice in
        GSTR-2B does NOT mean the supplier hasn't filed — it means the portal
        hasn't published the data yet.
        Returns True if GSTR-2B is available (safe to conclude non-filing),
        False if it's too early to conclude anything.
        """
        if not invoice_date_str:
            return True

        try:
            inv_date = date.fromisoformat(invoice_date_str)
            # GSTR-2B for month M is available after the 14th of month M+1
            if inv_date.month == 12:
                gstr2b_available_from = date(inv_date.year + 1, 1, self.GSTR2B_AVAILABILITY_DAY + 1)
            else:
                gstr2b_available_from = date(inv_date.year, inv_date.month + 1, self.GSTR2B_AVAILABILITY_DAY + 1)
            return date.today() >= gstr2b_available_from
        except (ValueError, TypeError):
            return True

    def supplier_is_composition_dealer(self, gstin_validation: Optional[GSTINValidation]) -> bool:
        """
        Composition scheme dealers (and UIN holders) file quarterly CMP-08,
        not GSTR-1. Their invoices will never appear in GSTR-2B under normal
        circumstances — flagging them as AT_RISK is factually wrong.
        """
        if not gstin_validation or not gstin_validation.taxpayer_type:
            return False
        return gstin_validation.taxpayer_type.lower() in self.NON_GSTR1_FILER_TYPES

    def compute_verdict(
        self,
        invoice: InvoiceJSON,
        hsn_validations: list[HSNValidationResult],
        gstin_validation: Optional[GSTINValidation],
        gstr2b_match: Optional[GSTR2BMatchResult],
        is_rcm: bool = False,
    ) -> ITCVerdict:
        """
        Master ITC computation. Returns a single verdict for the invoice.

        Order of checks:
          17(5) blocked → invoice validity → GSTIN → time limit →
          RCM gate → composition gate → GSTR-2B timing → 2B match →
          180-day rule → HSN mismatches → CONFIRMED
        """

        total_tax = invoice.total_tax_amount or 0.0

        # --- Check 1: Section 17(5) hard blocks ---
        for item in invoice.line_items:
            blocked, reason = self.is_blocked_category(item.hsn_code, item.description)
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

        # --- Check 5: RCM gate ---
        # Under RCM, the buyer self-assesses and pays GST directly.
        # The supplier does not file any GSTR-1 entry for this — absence in GSTR-2B is expected.
        if is_rcm:
            # Skip GSTR-2B reconciliation — RCM invoices self-declare
            pass

        # --- Check 6: Composition dealer gate ---
        # Composition scheme suppliers file quarterly CMP-08, never GSTR-1.
        # Their invoices legitimately never appear in GSTR-2B. Do not flag as AT_RISK.
        elif self.supplier_is_composition_dealer(gstin_validation):
            # Skip GSTR-2B check — this supplier type doesn't file GSTR-1
            pass

        # --- Check 7 & 8: GSTR-2B reconciliation (only for regular taxpayers) ---
        elif gstr2b_match:
            if gstr2b_match.status == GSTR2BMatchStatus.ITC_AT_RISK:
                # Gate: is GSTR-2B even available yet for this invoice period?
                if not self.is_gstr2b_available_for_period(invoice.invoice_date):
                    # Too early to conclude non-filing — data not yet published by portal
                    return ITCVerdict(
                        status=ITCStatus.AT_RISK,
                        itc_amount=total_tax,
                        itc_blocked=0.0,
                        reason="Invoice not yet reflected in GSTR-2B — portal data is pending (published after 14th of next month)",
                        legal_section="16(2)(c)",
                        fix_action="Check again after the 14th. If still missing, contact supplier to file their GSTR-1.",
                    )
                return ITCVerdict(
                    status=ITCStatus.AT_RISK,
                    itc_amount=total_tax,
                    itc_blocked=0.0,
                    reason="Invoice not found in GSTR-2B — supplier may not have filed GSTR-1",
                    legal_section="16(2)(c)",
                    fix_action="Contact supplier and ask them to file their GSTR-1",
                )

        # --- Check 9: 180-day payment rule (Section 16(2) second proviso) ---
        if not self.is_within_payment_window(invoice.invoice_date):
            return ITCVerdict(
                status=ITCStatus.FIXABLE_BLOCKED,
                itc_amount=0.0,
                itc_blocked=total_tax,
                reason="ITC reversal required — invoice unpaid beyond 180 days (Section 16(2) second proviso)",
                legal_section="16(2)",
                fix_action="Pay the supplier and re-claim ITC in the return for the month of payment. Interest is applicable on reversed ITC.",
            )

        # --- Check 10: HSN rate mismatches (fixable blocks) ---
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
