"""
Unit tests for GSTIN checksum validation.

27AAPFU0939F1ZV is a real-format, checksum-valid GSTIN used purely as a
numeric fixture here (no live API calls are made in these tests).
"""

from app.services.gstin import has_valid_checksum, is_valid_gstin_format

VALID_GSTIN = "27AAPFU0939F1ZV"


def test_valid_gstin_passes_checksum():
    assert has_valid_checksum(VALID_GSTIN) is True
    assert is_valid_gstin_format(VALID_GSTIN) is True


def test_corrupted_checksum_digit_fails():
    # Flip only the 15th (check-digit) character; everything else unchanged.
    corrupted = VALID_GSTIN[:14] + "X"
    assert corrupted != VALID_GSTIN
    assert has_valid_checksum(corrupted) is False
    assert is_valid_gstin_format(corrupted) is False


def test_too_short_gstin_rejected():
    assert has_valid_checksum("27AAPFU0939F1Z") is False
    assert is_valid_gstin_format("27AAPFU0939F1Z") is False
