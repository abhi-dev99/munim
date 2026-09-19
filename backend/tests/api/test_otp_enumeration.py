"""
Regression test: request-otp must not leak whether a phone number is
registered. Previously returned 404 "Mobile number not registered" for
unregistered numbers vs. 200 for registered ones -- a direct oracle for
enumerating onboarded traders/CAs. Both cases must now return the same
response shape and status.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.api import auth as auth_module


class _FakeQueryResult:
    def __init__(self, data):
        self.data = data


def _fake_supabase(registered: bool):
    """A minimal stand-in for get_supabase() covering exactly the chain
    request_otp uses: .table(...).select(...).eq(...).execute()."""
    db = MagicMock()
    result = _FakeQueryResult([{"id": "trader-1", "language_pref": "en"}] if registered else [])
    db.table.return_value.select.return_value.eq.return_value.execute.return_value = result
    return db


@pytest.mark.anyio
async def test_request_otp_response_identical_for_registered_and_unregistered():
    with patch.object(auth_module, "check_rate_limit", return_value=True), \
         patch.object(auth_module, "whatsapp") as mock_whatsapp, \
         patch.object(auth_module, "set_otp"):
        mock_whatsapp.send_text_message = MagicMock(return_value=None)

        async def _await_none(*a, **k):
            return None
        mock_whatsapp.send_text_message.side_effect = _await_none

        with patch.object(auth_module, "get_supabase", return_value=_fake_supabase(registered=True)):
            registered_response = await auth_module.request_otp(
                auth_module.OTPRequest(mobile_number="919876543210")
            )

        with patch.object(auth_module, "get_supabase", return_value=_fake_supabase(registered=False)):
            unregistered_response = await auth_module.request_otp(
                auth_module.OTPRequest(mobile_number="919999999999")
            )

        assert registered_response == unregistered_response
        assert "message" in registered_response


@pytest.mark.anyio
async def test_request_otp_does_not_raise_for_unregistered_number():
    # The old behaviour raised HTTPException(404) here -- confirm that's gone.
    with patch.object(auth_module, "check_rate_limit", return_value=True), \
         patch.object(auth_module, "get_supabase", return_value=_fake_supabase(registered=False)):
        response = await auth_module.request_otp(
            auth_module.OTPRequest(mobile_number="910000000000")
        )
        assert response["message"]
