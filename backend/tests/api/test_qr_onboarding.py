"""
Regression tests for QR-code onboarding: a trader's first WhatsApp message
can be JOIN-<short_code> from scanning a CA's dashboard QR code. This must
pre-fill ca_whatsapp_number so the manual awaiting_ca_number step is skipped,
and must fall back to the normal registration flow untouched on any
malformed or unmatched code.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.api import webhook as webhook_module


def _new_trader(trader_id="trader-1", ca_whatsapp_number=None):
    return {"id": trader_id, "ca_whatsapp_number": ca_whatsapp_number}


@pytest.mark.parametrize(
    "text,expected_code",
    [
        ("JOIN-AB12CD", "AB12CD"),
        ("join-ab12cd", "ab12cd"),
        ("  JOIN-XYZ9  ", "XYZ9"),
    ],
)
def test_join_code_regex_extracts_code(text, expected_code):
    match = webhook_module.JOIN_CODE_REGEX.match(text.strip())
    assert match is not None
    assert match.group(1) == expected_code


@pytest.mark.parametrize("text", ["hi", "JOIN", "JOIN-", "JOIN AB12CD", "not-a-join-code"])
def test_join_code_regex_rejects_non_join_text(text):
    assert webhook_module.JOIN_CODE_REGEX.match(text.strip()) is None


@pytest.mark.anyio
async def test_registration_with_valid_join_code_links_ca():
    ca_row = {"id": "ca-1", "whatsapp_number": "919876500000", "business_name": "Sharma & Co"}

    with patch.object(webhook_module, "get_trader_by_short_code", AsyncMock(return_value=ca_row)) as mock_lookup, \
         patch.object(webhook_module, "create_trader", AsyncMock(return_value=_new_trader())), \
         patch.object(webhook_module, "update_trader", AsyncMock(return_value=True)) as mock_update, \
         patch.object(webhook_module, "set_conversation_state") as mock_set_state, \
         patch.object(webhook_module.whatsapp, "send_text_message", AsyncMock()) as mock_send:

        await webhook_module._handle_registration("919999999999", "JOIN-AB12CD")

    mock_lookup.assert_awaited_once_with("AB12CD")
    mock_update.assert_awaited_once_with("trader-1", {"ca_whatsapp_number": "919876500000"})
    mock_set_state.assert_called_once_with(
        "919999999999", "awaiting_language", context={"linked_ca_name": "Sharma & Co"}
    )
    sent_text = mock_send.call_args.args[1]
    assert "Sharma & Co" in sent_text


@pytest.mark.anyio
async def test_registration_with_unknown_join_code_falls_back_to_manual_flow():
    with patch.object(webhook_module, "get_trader_by_short_code", AsyncMock(return_value=None)) as mock_lookup, \
         patch.object(webhook_module, "create_trader", AsyncMock(return_value=_new_trader())), \
         patch.object(webhook_module, "update_trader", AsyncMock()) as mock_update, \
         patch.object(webhook_module, "set_conversation_state") as mock_set_state, \
         patch.object(webhook_module.whatsapp, "send_text_message", AsyncMock()):

        await webhook_module._handle_registration("919999999999", "JOIN-NOTREAL")

    mock_lookup.assert_awaited_once_with("NOTREAL")
    mock_update.assert_not_awaited()
    mock_set_state.assert_called_once_with("919999999999", "awaiting_language")


@pytest.mark.anyio
async def test_registration_with_plain_message_never_looks_up_a_ca():
    with patch.object(webhook_module, "get_trader_by_short_code", AsyncMock()) as mock_lookup, \
         patch.object(webhook_module, "create_trader", AsyncMock(return_value=_new_trader())), \
         patch.object(webhook_module, "set_conversation_state"), \
         patch.object(webhook_module.whatsapp, "send_text_message", AsyncMock()):

        await webhook_module._handle_registration("919999999999", "Hi there")

    mock_lookup.assert_not_awaited()


@pytest.mark.anyio
async def test_awaiting_name_step_skips_ca_number_when_already_linked():
    trader = _new_trader(ca_whatsapp_number="919876500000")
    llm_result = {
        "status": "ok",
        "extracted": {"name": "Raju", "business_name": "Raju's Kirana Store"},
    }

    with patch("app.services.gemini.run_onboarding_llm", AsyncMock(return_value=llm_result)), \
         patch.object(webhook_module, "update_trader", AsyncMock()), \
         patch.object(webhook_module, "set_conversation_state") as mock_set_state, \
         patch.object(webhook_module.whatsapp, "send_text_message", AsyncMock()) as mock_send:

        await webhook_module._process_registration_step(
            "919999999999", "Raju", trader, "awaiting_name"
        )

    mock_set_state.assert_called_once_with("919999999999", "awaiting_gstin")
    sent_text = mock_send.call_args.args[1]
    assert "GSTIN" in sent_text


@pytest.mark.anyio
async def test_awaiting_name_step_asks_for_ca_number_when_not_linked():
    trader = _new_trader(ca_whatsapp_number=None)
    llm_result = {
        "status": "ok",
        "extracted": {"name": "Raju", "business_name": "Raju's Kirana Store"},
    }

    with patch("app.services.gemini.run_onboarding_llm", AsyncMock(return_value=llm_result)), \
         patch.object(webhook_module, "update_trader", AsyncMock()), \
         patch.object(webhook_module, "set_conversation_state") as mock_set_state, \
         patch.object(webhook_module.whatsapp, "send_text_message", AsyncMock()) as mock_send:

        await webhook_module._process_registration_step(
            "919999999999", "Raju", trader, "awaiting_name"
        )

    mock_set_state.assert_called_once_with("919999999999", "awaiting_ca_number")
    sent_text = mock_send.call_args.args[1]
    assert "CA" in sent_text
