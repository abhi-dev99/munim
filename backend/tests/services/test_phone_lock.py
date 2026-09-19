"""
Regression tests for the per-phone onboarding lock. Two fast WhatsApp
messages from the same number, dispatched as independent asyncio tasks,
could both read stale conversation state before either wrote its
transition. These test the lock primitive itself, not the full webhook
race end-to-end.
"""

from app.services.redis_cache import acquire_phone_lock, release_phone_lock


def test_first_acquire_succeeds():
    phone = "919000000001"
    release_phone_lock(phone)  # clean slate in case a prior test left it held
    assert acquire_phone_lock(phone) is True


def test_second_immediate_acquire_on_same_phone_fails():
    phone = "919000000002"
    release_phone_lock(phone)
    assert acquire_phone_lock(phone) is True
    assert acquire_phone_lock(phone) is False


def test_release_then_reacquire_succeeds():
    phone = "919000000003"
    release_phone_lock(phone)
    assert acquire_phone_lock(phone) is True
    release_phone_lock(phone)
    assert acquire_phone_lock(phone) is True


def test_different_phones_do_not_contend():
    phone_a, phone_b = "919000000004", "919000000005"
    release_phone_lock(phone_a)
    release_phone_lock(phone_b)
    assert acquire_phone_lock(phone_a) is True
    assert acquire_phone_lock(phone_b) is True
