"""Unit tests for app.utils.errors.safe_http_error."""

import logging
import re

from fastapi import HTTPException

from app.utils.errors import safe_http_error


def test_safe_http_error_hides_raw_exception_text():
    logger = logging.getLogger("test.errors")
    secret_detail = "connection to db.internal.example:5432 failed: password authentication failed for user 'admin'"
    exc = RuntimeError(secret_detail)

    result = safe_http_error(logger, "Failed to fetch trader summary", exc)

    assert isinstance(result, HTTPException)
    assert secret_detail not in result.detail
    assert "password" not in result.detail


def test_safe_http_error_includes_reference_id_and_message():
    logger = logging.getLogger("test.errors")
    exc = ValueError("boom")

    result = safe_http_error(logger, "Failed to fetch trader summary", exc)

    assert result.detail.startswith("Failed to fetch trader summary.")
    assert re.search(r"Reference: [0-9a-f]{8}\b", result.detail)


def test_safe_http_error_logs_real_detail(caplog):
    logger = logging.getLogger("test.errors")
    secret_detail = "raw internal detail that must not leak to clients"
    exc = RuntimeError(secret_detail)

    with caplog.at_level(logging.ERROR, logger="test.errors"):
        result = safe_http_error(logger, "Operation failed", exc)

    # The reference ID in the client-facing detail must also appear in logs,
    # so a user-reported error ID can be traced back to the real exception.
    ref_id = result.detail.split("Reference: ")[1]
    assert any(ref_id in record.message for record in caplog.records)
    assert any(secret_detail in record.message for record in caplog.records)


def test_safe_http_error_default_status_code_is_500():
    logger = logging.getLogger("test.errors")
    result = safe_http_error(logger, "Something failed", Exception("x"))
    assert result.status_code == 500


def test_safe_http_error_custom_status_code():
    logger = logging.getLogger("test.errors")
    result = safe_http_error(logger, "Bad upstream response", Exception("x"), status_code=502)
    assert result.status_code == 502
