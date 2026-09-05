"""
Regression tests for app.domain.reconciler.GSTR2BReconciler.

Of particular importance: match_invoice's `consumed_ids` parameter has no
default. A prior real bug had a caller invoking match_invoke without it,
which crashed every reconciliation call. These tests pin that contract
down so it cannot silently regress, and exercise the three-pass matching
(exact -> fuzzy Levenshtein -> amount+date) plus match-exclusivity.
"""

from datetime import date

import pytest

from app.domain.reconciler import GSTR2BReconciler, GSTR2BRecord
from app.models.invoice import GSTR2BMatchStatus


@pytest.fixture
def reconciler():
    return GSTR2BReconciler()


def make_record(**overrides) -> GSTR2BRecord:
    defaults = dict(
        record_id="r1",
        supplier_gstin="27AAAPZ1234C1Z5",
        invoice_number="INV1042",
        invoice_date=date(2026, 1, 10),
        taxable_value=1000.0,
        igst=0.0,
        cgst=90.0,
        sgst=90.0,
        record_type="B2B",
    )
    defaults.update(overrides)
    return GSTR2BRecord(**defaults)


# --- Exact match (Pass 1) -------------------------------------------------


def test_match_invoice_exact_match_returns_matched(reconciler):
    record = make_record()
    consumed_ids: set[str] = set()

    result = reconciler.match_invoice(
        supplier_gstin="27AAAPZ1234C1Z5",
        invoice_number="INV1042",
        invoice_date_str="2026-01-10",
        total_amount=1180.0,  # 1000 taxable + 90 cgst + 90 sgst
        gstr2b_records=[record],
        consumed_ids=consumed_ids,
    )

    assert result.status == GSTR2BMatchStatus.MATCHED
    assert result.confidence == 1.0
    assert result.matched_record_id == "r1"
    assert "r1" in consumed_ids


# --- consumed_ids has no default: this must fail loudly, not silently ----


def test_match_invoice_requires_consumed_ids_argument(reconciler):
    """
    Regression test: match_invoice's consumed_ids parameter has no default.
    A caller that drops the argument (as happened before) must get a loud
    TypeError, not a silent crash swallowed somewhere upstream.
    """
    record = make_record()
    with pytest.raises(TypeError):
        reconciler.match_invoice(
            supplier_gstin="27AAAPZ1234C1Z5",
            invoice_number="INV1042",
            invoice_date_str="2026-01-10",
            total_amount=1180.0,
            gstr2b_records=[record],
        )


# --- Match exclusivity ----------------------------------------------------


def test_match_invoice_exclusivity_prevents_double_matching(reconciler):
    """
    The same GSTR-2B record must not be matched twice. Threading the same
    consumed_ids set through two calls against a single record: the first
    call consumes it, the second must fall through to ITC_AT_RISK (no
    remaining candidates) rather than re-matching the same record.
    """
    record = make_record()
    consumed_ids: set[str] = set()

    first = reconciler.match_invoice(
        supplier_gstin="27AAAPZ1234C1Z5",
        invoice_number="INV1042",
        invoice_date_str="2026-01-10",
        total_amount=1180.0,
        gstr2b_records=[record],
        consumed_ids=consumed_ids,
    )
    assert first.status == GSTR2BMatchStatus.MATCHED

    second = reconciler.match_invoice(
        supplier_gstin="27AAAPZ1234C1Z5",
        invoice_number="INV1042",
        invoice_date_str="2026-01-10",
        total_amount=1180.0,
        gstr2b_records=[record],  # same single record
        consumed_ids=consumed_ids,  # same set, already contains "r1"
    )

    assert second.status == GSTR2BMatchStatus.ITC_AT_RISK
    assert second.confidence == 0.0
    assert second.matched_record_id is None


# --- Fuzzy match (Pass 2) --------------------------------------------------


def test_match_invoice_fuzzy_match_within_levenshtein_tolerance(reconciler):
    """
    Invoice number off by one digit (Levenshtein distance 1) with amount and
    date otherwise matching should still resolve via the fuzzy pass.
    """
    record = make_record(invoice_number="INV1042")
    consumed_ids: set[str] = set()

    result = reconciler.match_invoice(
        supplier_gstin="27AAAPZ1234C1Z5",
        invoice_number="INV1043",  # distance 1 from "INV1042" after normalization
        invoice_date_str="2026-01-15",  # within the 30-day window
        total_amount=1180.0,
        gstr2b_records=[record],
        consumed_ids=consumed_ids,
    )

    assert result.status == GSTR2BMatchStatus.PROBABLE_MATCH
    assert result.confidence == pytest.approx(0.89)
    assert result.matched_record_id == "r1"


def test_match_invoice_fuzzy_match_too_far_falls_through(reconciler):
    """An invoice number too different (distance > 2) must not fuzzy-match."""
    record = make_record(invoice_number="INV1042")
    consumed_ids: set[str] = set()

    result = reconciler.match_invoice(
        supplier_gstin="27AAAPZ1234C1Z5",
        invoice_number="COMPLETELYDIFFERENT",
        invoice_date_str="2026-01-15",
        total_amount=1180.0,
        gstr2b_records=[record],
        consumed_ids=consumed_ids,
    )

    # No exact/fuzzy match and Pass 3 also needs amount+date -- here amount
    # matches and date is close, so Pass 3 (amount+date only) picks it up.
    assert result.status == GSTR2BMatchStatus.POSSIBLE_MATCH
    assert result.confidence == 0.6


def test_match_invoice_no_candidates_for_different_supplier_is_at_risk(reconciler):
    """A record from a different supplier GSTIN must never be considered a candidate."""
    record = make_record(supplier_gstin="29BBBPZ5678D1Z1")
    consumed_ids: set[str] = set()

    result = reconciler.match_invoice(
        supplier_gstin="27AAAPZ1234C1Z5",
        invoice_number="INV1042",
        invoice_date_str="2026-01-10",
        total_amount=1180.0,
        gstr2b_records=[record],
        consumed_ids=consumed_ids,
    )

    assert result.status == GSTR2BMatchStatus.ITC_AT_RISK
    assert result.confidence == 0.0
