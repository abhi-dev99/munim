"""
Munim.ai — GSTR-2B Fuzzy Reconciliation Engine
Three-pass matching: Exact → Fuzzy → Amount+Date
Match-exclusivity enforced: each GSTR-2B record can only be consumed once.
Credit/Debit notes (CDNR) are handled via net_credit_notes().
"""

from difflib import SequenceMatcher
from datetime import date
from typing import Optional

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
        record_type: str = "B2B",  # B2B | CDNR | CDNA | B2BA
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
        self.record_type = record_type
        self.matched_invoice_id = None


class GSTR2BReconciler:
    """
    Reconciles trader invoices against GSTR-2B data.
    Three-pass matching algorithm with confidence scoring.
    Match-exclusivity: a GSTR-2B record can only be matched once across all invoices.
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

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate the Levenshtein distance between two strings using DP."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
            
        return previous_row[-1]

    def match_invoice(
        self,
        supplier_gstin: str,
        invoice_number: str,
        invoice_date_str: Optional[str],
        total_amount: float,
        gstr2b_records: list[GSTR2BRecord],
        consumed_ids: set[str],  # ← enforces match-exclusivity across all invoices
    ) -> GSTR2BMatchResult:
        """
        Match a single invoice against GSTR-2B records.
        consumed_ids is mutated in place when a match is found — caller must
        pre-allocate a single set and pass it to every call in the batch.
        Returns match status with confidence score.
        """

        # Filter to same supplier GSTIN, only B2B records, only not yet consumed
        candidates = [
            r for r in gstr2b_records
            if r.supplier_gstin == supplier_gstin
            and r.record_type in ("B2B", "B2BA")
            and r.record_id not in consumed_ids
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

        # --- Pass 1: Exact Match (GSTIN + invoice number + amount within 1%) ---
        for record in candidates:
            normalized_record_num = self._normalize_invoice_number(record.invoice_number)
            if normalized_record_num == normalized_inv_num:
                if self._amount_within_tolerance(record.total, total_amount, 0.01):
                    consumed_ids.add(record.record_id)
                    return GSTR2BMatchResult(
                        status=GSTR2BMatchStatus.MATCHED,
                        confidence=1.0,
                        matched_record_id=record.record_id,
                        itc_amount=record.total_tax,
                    )

        # --- Pass 2: Fuzzy Match (Levenshtein distance <= 2 + amount + date window) ---
        for record in candidates:
            normalized_record_num = self._normalize_invoice_number(record.invoice_number)
            distance = self._levenshtein_distance(normalized_inv_num, normalized_record_num)
            amount_ok = self._amount_within_tolerance(
                record.total, total_amount, self.amount_tolerance
            )
            date_ok = (
                self._date_within_window(record.invoice_date, inv_date, self.date_window_days)
                if inv_date and record.invoice_date
                else True
            )

            if distance <= 2 and amount_ok and date_ok:
                confidence = max(0.70, 0.99 - (distance * 0.1))  # 0.99 for 0, 0.89 for 1, 0.79 for 2
                consumed_ids.add(record.record_id)
                return GSTR2BMatchResult(
                    status=GSTR2BMatchStatus.PROBABLE_MATCH,
                    confidence=round(confidence, 2),
                    matched_record_id=record.record_id,
                    itc_amount=record.total_tax,
                )

        # --- Pass 3: Amount + Date only (invoice number format completely different) ---
        if inv_date:
            for record in candidates:
                if record.invoice_date is None:
                    continue
                amount_ok = self._amount_within_tolerance(
                    record.total, total_amount, 0.01
                )
                date_ok = self._date_within_window(
                    record.invoice_date, inv_date, self.strict_date_window_days
                )

                if amount_ok and date_ok:
                    consumed_ids.add(record.record_id)
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

    def net_credit_notes(
        self,
        gstr2b_records: list[GSTR2BRecord],
        matched_invoices: list[dict],
    ) -> list[dict]:
        """
        Apply CDNR (credit/debit notes) against matched invoices.
        For each CDNR record, find the corresponding supplier's confirmed invoices
        and reduce their ITC by the credit note amount.

        Returns a list of update dicts: {"invoice_id": ..., "itc_delta": ..., "note": ...}
        """
        updates = []
        cdnr_records = [r for r in gstr2b_records if r.record_type == "CDNR"]
        if not cdnr_records:
            return updates

        # Build an index of matched invoices by supplier GSTIN
        supplier_index: dict[str, list[dict]] = {}
        for inv in matched_invoices:
            gstin = inv.get("gstin_supplier", "")
            if gstin:
                supplier_index.setdefault(gstin, []).append(inv)

        for note in cdnr_records:
            affected = supplier_index.get(note.supplier_gstin, [])
            if not affected:
                continue
            # Apply to the largest confirmed invoice from that supplier first
            confirmed = [
                i for i in affected
                if i.get("itc_status") in ("CONFIRMED", "PROBABLE_MATCH", "POSSIBLE_MATCH")
            ]
            if not confirmed:
                continue
            confirmed.sort(key=lambda i: i.get("itc_amount_eligible", 0), reverse=True)
            target = confirmed[0]
            updates.append({
                "invoice_id": target["id"],
                "itc_delta": -abs(note.total_tax),  # negative = reduction
                "reason": f"Credit note {note.invoice_number} from supplier {note.supplier_gstin} — ITC reduced by ₹{abs(note.total_tax):.2f}",
            })

        return updates

    def find_missed_itc(
        self,
        gstr2b_records: list[GSTR2BRecord],
        consumed_ids: set[str],
    ) -> list[GSTR2BRecord]:
        """
        Find B2B records in GSTR-2B that were never matched to any trader invoice.
        These represent missed ITC — money left unclaimed.
        """
        orphaned = [
            r for r in gstr2b_records
            if r.record_type in ("B2B", "B2BA")
            and r.record_id not in consumed_ids
            and r.matched_invoice_id is None
        ]
        
        grouped = {}
        for r in orphaned:
            key = f"{r.supplier_gstin}_{r.invoice_number}"
            if key not in grouped:
                grouped[key] = r
            else:
                # If there's already a record, prefer B2BA
                if r.record_type == "B2BA":
                    grouped[key] = r
                    
        return list(grouped.values())
