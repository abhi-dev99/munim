"""
Phone normalisation is small, boring, and gates two things that are neither:
which trader an inbound WhatsApp message belongs to, and whether a CA may read
another trader's books (`deps.verify_trader_access` matches on these variants).

So the cases that matter most here are the false-positive ones.
"""

import pytest

from app.services.phone import (
    digits_only,
    local_msisdn,
    match_variants,
    normalize_msisdn,
    same_number,
)


class TestNormalize:
    @pytest.mark.parametrize("raw", [
        "9136875481",          # bare ten digits, as a CA would type it
        "919136875481",        # as Meta delivers it
        "+919136875481",
        "+91 91368 75481",
        "091-3687-5481",
        "09136875481",         # trunk-dialled
    ])
    def test_every_spelling_reaches_one_canonical_form(self, raw):
        assert normalize_msisdn(raw) == "919136875481"

    def test_blank_input_is_blank_not_a_country_code(self):
        # Returning "91" for an empty field would make every trader with no
        # number on file look like the same trader.
        assert normalize_msisdn("") == ""
        assert normalize_msisdn(None) == ""
        assert normalize_msisdn("   ") == ""

    def test_non_indian_numbers_are_left_alone(self):
        assert normalize_msisdn("+1 415 555 0123") == "14155550123"

    def test_landline_style_input_is_not_guessed_at(self):
        # Ten digits starting 2-5 is not a mobile; prefixing it would invent a
        # number. Pass it through rather than fabricate.
        assert normalize_msisdn("2212345678") == "2212345678"


class TestLocal:
    def test_strips_country_code(self):
        assert local_msisdn("918265081641") == "8265081641"

    def test_does_not_strip_when_the_subscriber_number_starts_with_91(self):
        # The regression this test exists for: naive stripping turned the real
        # number 9136875481 into 36875481, an eight-digit string belonging to
        # nobody, which then went into an `in_(...)` tenant-isolation lookup.
        assert local_msisdn("9136875481") == "9136875481"

    def test_does_not_strip_into_something_too_short(self):
        assert local_msisdn("91123") == "91123"


class TestVariants:
    def test_variants_are_ordered_most_canonical_first(self):
        # Order is precedence: get_trader_by_phone tries them in turn, so the
        # spelling WhatsApp actually used must win over a legacy one.
        assert match_variants("919136875481")[0] == "919136875481"

    def test_local_and_international_find_each_other(self):
        assert "919136875481" in match_variants("9136875481")
        assert "9136875481" in match_variants("919136875481")

    def test_no_bogus_short_variant_for_91_prefixed_subscriber(self):
        assert "36875481" not in match_variants("9136875481")

    def test_no_duplicates(self):
        v = match_variants("919136875481")
        assert len(v) == len(set(v))

    def test_blank_yields_nothing_to_match_on(self):
        # An empty variant list must not become an unfiltered query. Callers
        # check for this explicitly; the contract is that it stays empty.
        assert match_variants("") == []
        assert match_variants(None) == []


class TestSameNumber:
    def test_formats_of_one_number_compare_equal(self):
        assert same_number("9136875481", "+91 91368 75481")

    def test_different_numbers_do_not(self):
        assert not same_number("9136875481", "8265081641")

    def test_blank_is_never_equal_to_anything(self):
        assert not same_number("", "")
        assert not same_number(None, "919136875481")


def test_digits_only_keeps_only_digits():
    assert digits_only("+91 (913) 687-5481") == "919136875481"
    assert digits_only(None) == ""
