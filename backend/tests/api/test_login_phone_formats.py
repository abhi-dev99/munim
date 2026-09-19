"""
A person signing in types the number they know: ten digits, no country code.

`traders.whatsapp_number` may hold it either way, because rows reach that table
from WhatsApp onboarding (which stores Meta's `919822062252`), from a CA typing
a client's mobile, and from seed scripts. Login used to compare the typed
string to the stored one directly, so a trader stored with the country code
could not sign in without typing it — and because the endpoint correctly
refuses to reveal whether a number is registered, the failure was silent.
"""

import asyncio

import pytest

import app.api.auth as auth


@pytest.fixture
def captured(monkeypatch):
    """Run request_otp without Redis, WhatsApp or a database, capturing the
    keys it derives. Those keys are the whole point: they decide whether two
    spellings of one number are one account or two."""
    state = {"rate_keys": [], "otps": {}, "sent": [], "queried": []}

    monkeypatch.setattr(auth, "check_rate_limit",
                        lambda key, **kw: (state["rate_keys"].append(key), True)[1])
    monkeypatch.setattr(auth, "set_otp", lambda phone, otp: state["otps"].__setitem__(phone, otp))
    monkeypatch.setattr(auth, "get_otp", lambda phone: state["otps"].get(phone))

    async def fake_send(to, msg):
        state["sent"].append(to)
        return True

    monkeypatch.setattr(auth.whatsapp, "send_text_message", fake_send)

    class FakeQuery:
        def __init__(self, registry): self.registry = registry; self.col = None; self.vals = []
        def select(self, *_a, **_k): return self
        def in_(self, col, vals):
            self.col, self.vals = col, list(vals)
            state["queried"].append((col, tuple(vals)))
            return self
        def eq(self, col, val): return self.in_(col, [val])
        def execute(self):
            rows = [r for r in self.registry
                    if r.get(self.col) and r[self.col] in self.vals]
            return type("R", (), {"data": rows})()

    class FakeDB:
        def __init__(self, registry): self.registry = registry
        def table(self, _name): return FakeQuery(self.registry)

    state["registry"] = [
        {"id": "t1", "name": "Abhishek", "language_pref": "en",
         "whatsapp_number": "919822062252", "ca_whatsapp_number": "919822062252"},
    ]
    monkeypatch.setattr(auth, "get_supabase", lambda: FakeDB(state["registry"]))
    return state


SPELLINGS = ["9822062252", "919822062252", "+91 98220 62252", "098220 62252", "+919822062252"]


@pytest.mark.parametrize("typed", SPELLINGS)
def test_any_spelling_finds_the_account_and_sends_an_otp(captured, typed):
    asyncio.run(auth.request_otp(auth.OTPRequest(mobile_number=typed)))
    assert captured["otps"], f"no OTP issued for {typed!r} — this number cannot log in"
    assert list(captured["otps"]) == ["919822062252"]


def test_every_spelling_shares_one_rate_limit_bucket(captured):
    for typed in SPELLINGS:
        asyncio.run(auth.request_otp(auth.OTPRequest(mobile_number=typed)))
    # Keying the limiter on the typed string gave each spelling its own budget,
    # so three requests became fifteen just by adding spaces.
    assert set(captured["rate_keys"]) == {"otp-req:919822062252"}


def test_otp_requested_one_way_verifies_another(captured):
    asyncio.run(auth.request_otp(auth.OTPRequest(mobile_number="9822062252")))
    code = captured["otps"]["919822062252"]
    result = asyncio.run(auth.verify_otp(
        auth.OTPVerify(mobile_number="+91 98220 62252", otp=code)
    ))
    assert result["token"]
    assert "trader" in result["roles"]


def test_unregistered_number_gets_no_otp_and_gives_nothing_away(captured):
    res = asyncio.run(auth.request_otp(auth.OTPRequest(mobile_number="7000000001")))
    assert not captured["otps"], "issued an OTP for an unregistered number"
    assert not captured["sent"]
    assert "If this number is registered" in res["message"]


def test_garbage_input_is_refused_without_an_oracle(captured):
    res = asyncio.run(auth.request_otp(auth.OTPRequest(mobile_number="not-a-number")))
    assert not captured["otps"]
    # Same wording as an unregistered number: a different message here would
    # tell a prober which inputs are even considered.
    assert "If this number is registered" in res["message"]


def test_lookup_covers_both_the_trader_and_the_ca_column(captured):
    asyncio.run(auth.request_otp(auth.OTPRequest(mobile_number="9822062252")))
    cols = {col for col, _ in captured["queried"]}
    assert cols == {"whatsapp_number", "ca_whatsapp_number"}
    for _, vals in captured["queried"]:
        assert "919822062252" in vals and "9822062252" in vals
