"""
Regression tests for app.domain.itc_engine.ITCRulesEngine.

These cover the pure Section 16/17(5) rule logic — no LLM, no network,
no database. Dates are computed relative to date.today() wherever the
assertion depends on "now" so the suite keeps passing as time passes.
"""

from datetime import date, timedelta

import pytest

from app.domain.itc_engine import ITCRulesEngine
from app.models.invoice import InvoiceJSON


@pytest.fixture
def engine():
    return ITCRulesEngine()


def make_invoice(**overrides) -> InvoiceJSON:
    """A minimally-valid InvoiceJSON, with fields overridable per test."""
    defaults = dict(
        invoice_number="INV-001",
        invoice_date=date.today().isoformat(),
        gstin_supplier="27AAAPZ1234C1Z5",
        gstin_buyer="27AAAPZ9999C1Z5",
        supplier_name="Test Supplier",
        total_taxable_amount=1000.0,
        total_tax_amount=180.0,
        total_amount=1180.0,
    )
    defaults.update(overrides)
    return InvoiceJSON(**defaults)


# --- is_blocked_category ---------------------------------------------------


def test_is_blocked_category_known_blocked_hsn_prefix(engine):
    """8703 (passenger motor vehicles) is a Section 17(5) hard block."""
    blocked, reason = engine.is_blocked_category("87032090", "Sedan car purchase")
    assert blocked is True
    assert "17(5)" in reason


def test_is_blocked_category_normal_hsn_is_not_blocked(engine):
    """An ordinary HSN code (e.g. rice, 1006) must not be flagged as blocked."""
    blocked, reason = engine.is_blocked_category("1006", "Basmati rice")
    assert blocked is False
    assert reason == ""


def test_is_blocked_category_keyword_match(engine):
    """A description containing a BLOCKED_KEYWORDS entry is blocked even with a clean HSN."""
    blocked, reason = engine.is_blocked_category("9999", "Diwali gift hamper for client")
    assert blocked is True
    assert "gift" in reason.lower()


def test_is_blocked_category_no_hsn_no_keyword(engine):
    """No HSN code and a clean description should not be blocked."""
    blocked, reason = engine.is_blocked_category(None, "Office stationery")
    assert blocked is False
    assert reason == ""


# --- is_valid_tax_invoice ---------------------------------------------------


def test_is_valid_tax_invoice_complete_invoice_is_valid(engine):
    invoice = make_invoice()
    assert engine.is_valid_tax_invoice(invoice) is True


@pytest.mark.parametrize(
    "field",
    ["invoice_number", "invoice_date", "gstin_supplier", "total_amount"],
)
def test_is_valid_tax_invoice_missing_required_field_is_invalid(engine, field):
    invoice = make_invoice(**{field: None})
    assert engine.is_valid_tax_invoice(invoice) is False


def test_is_valid_tax_invoice_zero_total_amount_is_invalid(engine):
    invoice = make_invoice(total_amount=0.0)
    assert engine.is_valid_tax_invoice(invoice) is False


def test_is_valid_tax_invoice_future_dated_invoice_is_invalid(engine):
    """
    Regression test: a future-dated invoice must be rejected.
    date.fromisoformat(invoice.invoice_date) > date.today() is the guard
    that was added to itc_engine.is_valid_tax_invoice — make sure it can't
    silently regress.
    """
    future_date = (date.today() + timedelta(days=30)).isoformat()
    invoice = make_invoice(invoice_date=future_date)
    assert engine.is_valid_tax_invoice(invoice) is False


def test_is_valid_tax_invoice_todays_date_is_valid(engine):
    """An invoice dated exactly today (not in the future) should still pass."""
    invoice = make_invoice(invoice_date=date.today().isoformat())
    assert engine.is_valid_tax_invoice(invoice) is True


def test_is_valid_tax_invoice_malformed_date_does_not_crash(engine):
    """A non-ISO date string should be tolerated (ValueError swallowed), not raise."""
    invoice = make_invoice(invoice_date="not-a-date")
    # The malformed-date guard only ever returns early on a successful parse;
    # validity here is decided purely by the "all required fields present" check.
    assert engine.is_valid_tax_invoice(invoice) is True


# --- is_within_time_limit ---------------------------------------------------


def test_is_within_time_limit_recent_invoice_passes(engine):
    """An invoice dated today is always within the Section 16(4) deadline."""
    assert engine.is_within_time_limit(date.today().isoformat()) is True


def test_is_within_time_limit_old_invoice_fails_deadline(engine):
    """
    An invoice from FY 2014-15 (statutory deadline 30 Nov 2015) is long past
    its Section 16(4) claim deadline by the time this suite runs.
    """
    assert engine.is_within_time_limit("2015-01-15") is False


def test_is_within_time_limit_none_date_assumes_valid(engine):
    """Unknown invoice date should not itself block ITC (assume valid)."""
    assert engine.is_within_time_limit(None) is True


def test_is_within_time_limit_boundary_deadline_exact_day(engine):
    """
    An invoice issued in Jan-March has its FY end in the same calendar year,
    so the deadline is 30 Nov of that same year — also long past by now.
    """
    assert engine.is_within_time_limit("2016-02-01") is False
