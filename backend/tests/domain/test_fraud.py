"""
Regression tests for app.domain.fraud.FraudScorer — the six-signal fraud
scorer (GSTIN age, Benford's Law, sequential invoices, business-type
mismatch, geographic mismatch, velocity anomaly). Pure statistical/rule
logic, no LLM and no network calls.
"""

from datetime import date, timedelta

import pytest

from app.domain.fraud import FraudScorer
from app.models.invoice import GSTINValidation, InvoiceJSON, LineItem


@pytest.fixture
def scorer():
    return FraudScorer()


def make_gstin_validation(**overrides) -> GSTINValidation:
    defaults = dict(gstin="27AAAPZ1234C1Z5")
    defaults.update(overrides)
    return GSTINValidation(**defaults)


# --- Signal 1: GSTIN age -----------------------------------------------


def test_score_gstin_age_old_gstin_does_not_trigger(scorer):
    """A GSTIN registered years ago, even for a high-value invoice, is clean."""
    old_registration = (date.today() - timedelta(days=365 * 5)).isoformat()
    gstin_validation = make_gstin_validation(registration_date=old_registration)

    signal = scorer.score_gstin_age(gstin_validation, invoice_amount=200000.0)

    assert signal.triggered is False
    assert signal.score_contribution == 0


def test_score_gstin_age_new_gstin_with_high_value_triggers(scorer):
    """A GSTIN registered 10 days ago issuing a high-value invoice is suspicious."""
    new_registration = (date.today() - timedelta(days=10)).isoformat()
    gstin_validation = make_gstin_validation(registration_date=new_registration)

    signal = scorer.score_gstin_age(gstin_validation, invoice_amount=200000.0)

    assert signal.triggered is True
    assert 0 < signal.score_contribution <= FraudScorer.WEIGHTS["gstin_age"]


def test_score_gstin_age_no_registration_date_does_not_trigger(scorer):
    """Missing registration date data can't be scored — must not raise or trigger."""
    gstin_validation = make_gstin_validation(registration_date=None)
    signal = scorer.score_gstin_age(gstin_validation, invoice_amount=200000.0)
    assert signal.triggered is False


# --- Signal 2: Benford's Law --------------------------------------------


def test_score_benfords_law_insufficient_sample_does_not_trigger(scorer):
    """Fewer than min_sample_size amounts is not enough data to run the test."""
    signal = scorer.score_benfords_law([100.0, 200.0, 300.0])
    assert signal.triggered is False
    assert signal.score_contribution == 0


def test_score_benfords_law_skewed_distribution_triggers(scorer):
    """
    A set of amounts whose leading digit is overwhelmingly 9 is a strong
    Benford's Law violation (natural data should be ~4.6% leading-9s).
    """
    skewed_amounts = [900.0 + i for i in range(30)]  # all lead with digit 9
    signal = scorer.score_benfords_law(skewed_amounts)

    assert signal.triggered is True
    assert 0 < signal.score_contribution <= FraudScorer.WEIGHTS["benfords_law"]


# --- Signal 3: Sequential invoices ---------------------------------------


def test_score_sequential_invoices_random_numbers_do_not_trigger(scorer):
    signal = scorer.score_sequential_invoices(
        ["INV-104", "INV-233", "INV-587"], supplier_gstin="27AAAPZ1234C1Z5"
    )
    assert signal.triggered is False
    assert signal.score_contribution == 0


def test_score_sequential_invoices_consecutive_numbers_trigger(scorer):
    """Four strictly-consecutive invoice numbers from one supplier is a classic fake-invoicing pattern."""
    signal = scorer.score_sequential_invoices(
        ["INV-101", "INV-102", "INV-103", "INV-104"], supplier_gstin="27AAAPZ1234C1Z5"
    )
    assert signal.triggered is True
    assert signal.score_contribution == FraudScorer.WEIGHTS["sequential_invoices"]


def test_score_sequential_invoices_below_min_invoices_does_not_trigger(scorer):
    signal = scorer.score_sequential_invoices(
        ["INV-101", "INV-102"], supplier_gstin="27AAAPZ1234C1Z5"
    )
    assert signal.triggered is False


# --- Signal 4: Business type mismatch ------------------------------------


def test_score_business_mismatch_matching_category_does_not_trigger(scorer):
    gstin_validation = make_gstin_validation(business_category="Consulting Services")
    line_items = [LineItem(description="Management consulting retainer")]
    signal = scorer.score_business_mismatch(gstin_validation, line_items)
    assert signal.triggered is False


def test_score_business_mismatch_services_supplier_billing_goods_triggers(scorer):
    """A registered 'services' supplier invoicing for steel is a business-type contradiction."""
    gstin_validation = make_gstin_validation(business_category="IT Services")
    line_items = [LineItem(description="Steel rods, 10mm, 500kg")]
    signal = scorer.score_business_mismatch(gstin_validation, line_items)
    assert signal.triggered is True
    assert signal.score_contribution == FraudScorer.WEIGHTS["business_mismatch"]


# --- Signal 5: Geographic mismatch ---------------------------------------


def test_score_geographic_mismatch_same_state_does_not_trigger(scorer):
    signal = scorer.score_geographic_mismatch("27AAAPZ1234C1Z5", "27AAAPZ9999C1Z5")
    assert signal.triggered is False


def test_score_geographic_mismatch_different_state_without_igst_triggers(scorer):
    """Supplier in Maharashtra (27), buyer in Delhi (07), no interstate flag — should trigger."""
    signal = scorer.score_geographic_mismatch(
        "27AAAPZ1234C1Z5", "07AAAPZ9999C1Z5", is_interstate=False
    )
    assert signal.triggered is True
    assert signal.score_contribution == FraudScorer.WEIGHTS["geographic_mismatch"]


def test_score_geographic_mismatch_different_state_with_igst_does_not_trigger(scorer):
    """A genuinely interstate transaction (IGST charged) should not be flagged."""
    signal = scorer.score_geographic_mismatch(
        "27AAAPZ1234C1Z5", "07AAAPZ9999C1Z5", is_interstate=True
    )
    assert signal.triggered is False


# --- Signal 6: Velocity anomaly ------------------------------------------


def test_score_velocity_anomaly_typical_amount_does_not_trigger(scorer):
    signal = scorer.score_velocity_anomaly(
        current_amount=12000.0, historical_amounts=[10000.0, 11000.0, 9500.0, 10500.0]
    )
    assert signal.triggered is False


def test_score_velocity_anomaly_spike_triggers(scorer):
    """An invoice 10x the supplier's historical average is a velocity spike."""
    signal = scorer.score_velocity_anomaly(
        current_amount=100000.0, historical_amounts=[10000.0, 9500.0, 10500.0]
    )
    assert signal.triggered is True
    assert 0 < signal.score_contribution <= FraudScorer.WEIGHTS["velocity_anomaly"]


# --- compute_fraud_score integration -------------------------------------


def test_compute_fraud_score_zero_tax_invoice_is_skipped(scorer):
    """Composition/Bill-of-Supply invoices (zero tax) are exempt from fraud scoring."""
    invoice = InvoiceJSON(
        invoice_number="INV-1",
        invoice_date=date.today().isoformat(),
        gstin_supplier="27AAAPZ1234C1Z5",
        total_tax_amount=0.0,
        total_amount=1000.0,
    )
    result = scorer.compute_fraud_score(invoice)
    assert result.total_score == 0
    assert result.signals == []
    assert result.is_hard_flag is False


def test_compute_fraud_score_multiple_triggers_raises_hard_flag(scorer):
    """Stacking several anomalous signals should push the composite score past the hard threshold."""
    new_registration = (date.today() - timedelta(days=5)).isoformat()
    gstin_validation = make_gstin_validation(
        registration_date=new_registration, business_category="IT Services"
    )
    invoice = InvoiceJSON(
        invoice_number="INV-104",
        invoice_date=date.today().isoformat(),
        gstin_supplier="27AAAPZ1234C1Z5",
        gstin_buyer="07AAAPZ9999C1Z5",  # different state, no IGST -> geographic mismatch
        total_tax_amount=18000.0,
        total_amount=300000.0,  # high value, new GSTIN -> gstin_age trigger
        line_items=[LineItem(description="Steel rods", igst_amount=0.0)],
    )
    result = scorer.compute_fraud_score(
        invoice,
        gstin_validation=gstin_validation,
        historical_amounts=[10000.0, 9500.0, 10500.0],  # velocity spike too
        supplier_invoice_numbers=["INV-101", "INV-102", "INV-103", "INV-104"],
    )

    assert result.total_score > 0
    assert any(s.triggered for s in result.signals)
    assert result.is_hard_flag is True
