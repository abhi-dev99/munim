"""
Munim.ai — phone number normalisation.

Nobody should have to type a country code into a GST app used in India, and
nobody does. The `91` prefix is not a form field: it is the format WhatsApp
uses on the wire. Meta's Cloud API delivers an inbound sender as
`919136875481` and expects the same shape on send, while numbers that reach
this system from anywhere else — a CA typing their client's mobile, a seed
script, a CSV — arrive as a bare ten digits, or with `+91`, or with spaces.

Nothing reconciled those two worlds, and `get_trader_by_phone` compared them
with an exact string match. The result in the live database: a trader stored
as `9136875481` can never be found by an inbound message from that very
handset, because Meta announces it as `919136875481`. Munim's busiest trader
was unreachable in both directions and nothing anywhere said so.

The fix belongs here, at the boundary, not in the data. Store whatever
arrives; compare on the normalised form.
"""

from __future__ import annotations

import re
from typing import Optional

DEFAULT_COUNTRY_CODE = "91"

# India's mobile numbering plan: ten digits, first digit 6-9. Used only to
# decide whether a bare ten-digit string is safe to prefix — never to reject a
# number, because rejecting a real customer's number over a numbering-plan
# quirk is a worse failure than storing an odd one.
_INDIAN_MOBILE = re.compile(r"^[6-9]\d{9}$")


def digits_only(raw: Optional[str]) -> str:
    """Strip everything that is not a digit: `+`, spaces, hyphens, brackets."""
    return re.sub(r"\D", "", raw or "")


def normalize_msisdn(raw: Optional[str], country_code: str = DEFAULT_COUNTRY_CODE) -> str:
    """
    The canonical form Munim compares and dials: country code + subscriber
    number, digits only, no `+`.

    Deliberately conservative. A bare ten-digit Indian mobile gains the
    country code; anything already carrying one is left alone; anything that
    is neither is returned as digits and left for the caller to deal with.
    Guessing aggressively here would silently redirect somebody's messages to
    a stranger, which is far worse than failing to match.
    """
    d = digits_only(raw)
    if not d:
        return ""
    if _INDIAN_MOBILE.match(d):
        return f"{country_code}{d}"
    # 0-prefixed trunk dialling, e.g. 09136875481
    if len(d) == 11 and d.startswith("0") and _INDIAN_MOBILE.match(d[1:]):
        return f"{country_code}{d[1:]}"
    return d


def local_msisdn(raw: Optional[str], country_code: str = DEFAULT_COUNTRY_CODE) -> str:
    """
    The subscriber number without its country code — the other half of the
    pair a legacy row might be stored as.

    The leading-digit check is not decoration. India's country code is `91`
    and Indian mobiles may themselves begin `91`, so a naive strip turns the
    real number `9136875481` into `36875481` — eight digits belonging to
    nobody. Fed into an `in_(...)` lookup that is a false match waiting to
    happen, and one of those lookups decides whether a CA may read another
    trader's books. Only strip when what remains is a plausible subscriber
    number.
    """
    d = digits_only(raw)
    if d.startswith(country_code) and len(d) > len(country_code):
        rest = d[len(country_code):]
        if _INDIAN_MOBILE.match(rest):
            return rest
    return d


def match_variants(raw: Optional[str], country_code: str = DEFAULT_COUNTRY_CODE) -> list[str]:
    """
    Every spelling of this number that might be sitting in the database,
    most-canonical first.

    Order matters: callers use it as a precedence list, so an exact
    international match always wins over a bare-local one. That is what keeps
    lookups deterministic when two rows hold the same number in different
    formats — the row stored the way WhatsApp actually spells it is the one
    that owns the handset.
    """
    d = digits_only(raw)
    if not d:
        return []
    ordered = [d, normalize_msisdn(raw, country_code), local_msisdn(raw, country_code)]
    seen: list[str] = []
    for v in ordered:
        if v and v not in seen:
            seen.append(v)
    return seen


def same_number(a: Optional[str], b: Optional[str], country_code: str = DEFAULT_COUNTRY_CODE) -> bool:
    """Whether two spellings refer to the same subscriber."""
    na, nb = normalize_msisdn(a, country_code), normalize_msisdn(b, country_code)
    return bool(na) and na == nb
