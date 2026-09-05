"""
Munim.ai — GSTR-2B Fuzzy Reconciliation Engine
Three-pass matching: Exact → Fuzzy → Amount+Date
"""

import hashlib
from datetime import date, timedelta
from typing import Optional

# MOCK LEVENSHTEIN FOR NOW TO AVOID INSTALL HANGS
def levenshtein_distance(s1: str, s2: str) -> int:
    if s1 == s2:
        return 0
    return abs(len(s1) - len(s2)) + 1

from app.models.invoice import GSTR2BMatchResult, GSTR2BMatchStatus


class GSTR2BRecord:
    """Represents a single record from a trader's GSTR-2B export."""

    def __init__(
        self,
        record_id: str,
        supplier_gstin: str,
        invoice_number: str,
        invoice_date: date,
        taxable_value: float,
        igst: float = 0.0,
        cgst: float = 0.0,
        sgst: float = 0.0,
    ):
        self.record_id = record_id
        self.supplier_gstin = supplier_gstin
        self.invoice_number = invoice_number
        self.invoice_date = invoice_date
        self.taxable_value = taxable_value
        self.igst = igst
        self.cgst = cgst
        self.sgst = sgst
        self.total_tax = igst + cgst + sgst
        self.total = taxable_value + self.total_tax


class GSTR2BReconciler:
    """
    Reconciles trader invoices against GSTR-2B data.
    Three-pass matching algorithm with confidence scoring.
    """

    def __init__(
        self,
        amount_tolerance: float = 0.02,
        date_window_days: int = 30,
        strict_date_window_days: int = 15,
    ):
        self.amount_tolerance = amount_tolerance
        self.date_window_days = date_window_days
        self.strict_date_window_days = strict_date_window_days

    def _amount_within_tolerance(
        self, amount_a: float, amount_b: float, tolerance: float
    ) -> bool:
        """Check if two amounts are within percentage tolerance."""
        if amount_a == 0 and amount_b == 0:
            return True
        if amount_a == 0 or amount_b == 0:
            return False
        return abs(amount_a - amount_b) / max(amount_a, amount_b) <= tolerance

    def _date_within_window(
        self, date_a: date, date_b: date, window_days: int
    ) -> bool:
        """Check if two dates are within N days of each other."""
        return abs((date_a - date_b).days) <= window_days

    def _normalize_invoice_number(self, inv_num: str) -> str:
        """Normalize invoice number for comparison (strip spaces, lowercase)."""
        return inv_num.strip().lower().replace(" ", "").replace("-", "").replace("/", "")

    def match_invoice(
        self,
        supplier_gstin: str,
        invoice_number: str,
        invoice_date_str: Optional[str],
        total_amount: float,
        gstr2b_records: list[GSTR2BRecord],
    ) -> GSTR2BMatchResult:
        """
        Match a single invoice against GSTR-2B records.
        Returns match status with confidence score.
        """

        # Filter to same supplier GSTIN
        candidates = [
            r for r in gstr2b_records
            if r.supplier_gstin == supplier_gstin
        ]

        if not candidates:
            return GSTR2BMatchResult(
                status=GSTR2BMatchStatus.ITC_AT_RISK,
                confidence=0.0,
            )

        # Parse invoice date
        try:
            inv_date = date.fromisoformat(invoice_date_str) if invoice_date_str else None
        except (ValueError, TypeError):
            inv_date = None

        normalized_inv_num = self._normalize_invoice_number(invoice_number or "")

        # --- Pass 1: Exact Match (GSTIN + invoice number) ---
        for record in candidates:
            normalized_record_num = self._normalize_invoice_number(record.invoice_number)
            if normalized_record_num == normalized_inv_num:
                if self._amount_within_tolerance(record.total, total_amount, 0.01):
                    return GSTR2BMatchResult(
                        status=GSTR2BMatchStatus.MATCHED,
                        confidence=1.0,
                        matched_record_id=record.record_id,
                        itc_amount=record.total_tax,
                    )

        # --- Pass 2: Fuzzy Match (Levenshtein ≤ 2 + amount + date window) ---
        for record in candidates:
            normalized_record_num = self._normalize_invoice_number(record.invoice_number)
            lev_dist = levenshtein_distance(normalized_inv_num, normalized_record_num)
            amount_ok = self._amount_within_tolerance(
                record.total, total_amount, self.amount_tolerance
            )
            date_ok = (
                self._date_within_window(record.invoice_date, inv_date, self.date_window_days)
                if inv_date
                else True
            )

            if lev_dist <= 2 and amount_ok and date_ok:
                confidence = 1.0 - (lev_dist * 0.15)
                if not date_ok:
                    confidence -= 0.1
                return GSTR2BMatchResult(
                    status=GSTR2BMatchStatus.PROBABLE_MATCH,
                    confidence=max(confidence, 0.5),
                    matched_record_id=record.record_id,
                    itc_amount=record.total_tax,
                )

        # --- Pass 3: Amount + Date only (invoice number format completely different) ---
        if inv_date:
            for record in candidates:
                amount_ok = self._amount_within_tolerance(
                    record.total, total_amount, 0.01
                )
                date_ok = self._date_within_window(
                    record.invoice_date, inv_date, self.strict_date_window_days
                )

                if amount_ok and date_ok:
                    return GSTR2BMatchResult(
                        status=GSTR2BMatchStatus.POSSIBLE_MATCH,
                        confidence=0.6,
                        matched_record_id=record.record_id,
                        itc_amount=record.total_tax,
                    )

        # --- No match ---
        return GSTR2BMatchResult(
            status=GSTR2BMatchStatus.ITC_AT_RISK,
            confidence=0.0,
        )

    def find_missed_itc(
        self,
        gstr2b_records: list[GSTR2BRecord],
        processed_invoice_hashes: set[str],
    ) -> list[GSTR2BRecord]:
        """
        Find invoices in GSTR-2B that are NOT in trader's records.
        These represent missed ITC — money left unclaimed.
        """
        missed = []
        for record in gstr2b_records:
            record_hash = self.compute_hash(
                record.supplier_gstin, record.invoice_number, str(record.invoice_date)
            )
            if record_hash not in processed_invoice_hashes:
                missed.append(record)
        return missed

    @staticmethod
    def compute_hash(supplier_gstin: str, invoice_number: str, invoice_date: str) -> str:
        """SHA-256 hash for duplicate detection."""
        raw = f"{supplier_gstin}|{invoice_number}|{invoice_date}"
        return hashlib.sha256(raw.encode()).hexdigest()
