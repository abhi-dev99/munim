"""
Munim.ai — the missed-credit recovery loop.

Detection already exists: `/gstr2b/missed-itc` finds GSTR-2B rows a supplier
reported that no invoice was ever matched against. Detection on its own
changes nothing — somebody still has to find out whether the trader has that
bill. This module closes the loop by asking them, over WhatsApp, one bill at a
time, and recording what they say.

The shape of it is the product's whole compliance argument in miniature:
**Munim finds the gap and computes the money; a human decides what is true.**
Nothing in here concludes that a bill exists or does not. It asks, waits, and
records an answer given by the person who would know.

Durability, and why there are two kinds of state
------------------------------------------------
The ask may be answered in ninety seconds or on Thursday. Conversation state
in Redis has a one-hour TTL and does not survive a restart, so it cannot be
the record — it is only a fast path telling us which bill the next reply is
about. The durable record is an event per bill (see `services/event_store`).

When the fast path is gone, `handle_reply` falls back to the oldest still-open
event for that trader. A trader who answers two days later is answering the
question we asked; losing that because a cache expired would be the sort of
failure that teaches somebody to stop replying.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Optional

from app.services import event_store
from app.services.redis_cache import (
    clear_conversation_state,
    get_conversation_state,
    set_conversation_state,
)
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

STATE = "awaiting_missing_invoice"

# One bill at a time. A list of six in a WhatsApp message gets no reply at all;
# a single question with a rupee figure gets one.
MAX_ASKS_PER_RUN = 3

# Event payload `status` values. Stored, so treat as schema.
ASKED = "asked"
HAS_BILL = "has_bill"
NO_BILL = "no_bill"
RESOLVED = "resolved"
OPEN_STATUSES = {ASKED, HAS_BILL}


def _inr(amount) -> str:
    return f"₹{round(float(amount or 0)):,}"


def _pretty_date(value) -> str:
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").strftime("%d %b %Y")
    except (ValueError, TypeError):
        return str(value or "")


_MESSAGES = {
    "en": {
        "intro": (
            "*Unclaimed credit found*\n\n"
            "{supplier} told the GST portal they sold to you, but we have never "
            "seen this bill."
        ),
        "detail": "Bill {number} dated {date}\nTax you can claim: *{tax}*",
        "ask": "Do you have this bill?\n\nReply *YES* and send a photo of it, or *NO* if you do not have it.",
        "yes": "Good. Send me a photo of that bill and I will check it straight away.",
        "no": "Noted — I have recorded that this bill is not with you. Your CA will see it.",
        "stop": "Alright, I will stop asking about these.",
        "done": "That is all of them. Thank you.",
        "next": "Next one.",
        "none": "Nothing unclaimed right now — every bill your suppliers reported is matched.",
    },
    "hi": {
        "intro": (
            "*Bina claim kiya credit mila*\n\n"
            "{supplier} ne GST portal par bataya hai ki unhone aapko maal becha, "
            "lekin yeh bill humne kabhi nahi dekha."
        ),
        "detail": "Bill {number}, tarikh {date}\nJo tax aap claim kar sakte hain: *{tax}*",
        "ask": "Kya yeh bill aapke paas hai?\n\n*HAAN* likhkar bill ka photo bhejiye, ya *NAHI* likhiye agar bill nahi hai.",
        "yes": "Theek hai. Us bill ka photo bhejiye, main turant check kar dunga.",
        "no": "Note kar liya — yeh bill aapke paas nahi hai. Aapke CA ko dikh jayega.",
        "stop": "Theek hai, ab main inke baare mein nahi puchunga.",
        "done": "Bas itne hi the. Dhanyavaad.",
        "next": "Agla.",
        "none": "Abhi kuch bhi bina claim ka nahi hai — supplier ke sabhi bill match ho chuke hain.",
    },
    "mr": {
        "intro": (
            "*Claim na kelela credit sapadle*\n\n"
            "{supplier} ne GST portal var sangitle ki tyanni tumhala maal vikla, "
            "pan he bill aamhi kadhich pahile nahi."
        ),
        "detail": "Bill {number}, tarikh {date}\nTumhi claim karu shakta asa tax: *{tax}*",
        "ask": "He bill tumchyakade aahe ka?\n\n*HOY* lihun bill cha photo pathva, kinva *NAHI* liha jar bill nasel tar.",
        "yes": "Theek aahe. Tya bill cha photo pathva, mi lagech check karto.",
        "no": "Nond kelay — he bill tumchyakade nahi. Tumchya CA la disel.",
        "stop": "Theek aahe, mi aata yabaddal vicharnar nahi.",
        "done": "Evadhech hote. Dhanyavaad.",
        "next": "Pudhcha.",
        "none": "Sadhya kahich claim baki nahi — supplier che sagle bill match zale aahet.",
    },
    "gu": {
        "intro": (
            "*Claim na karelu credit malyu*\n\n"
            "{supplier} e GST portal par kahyu chhe ke temne tamne maal vechyo, "
            "pan aa bill ame kyarey joyu nathi."
        ),
        "detail": "Bill {number}, tarikh {date}\nTame claim kari shako te tax: *{tax}*",
        "ask": "Shu aa bill tamari pase chhe?\n\n*HA* lakhi bill no photo moklo, athva *NA* lakho jo bill na hoy.",
        "yes": "Saras. Te bill no photo moklo, hu turant check kari daish.",
        "no": "Nondh kari lidhu — aa bill tamari pase nathi. Tamara CA ne dekhashe.",
        "stop": "Theek chhe, have hu aa vishe nahi puchhu.",
        "done": "Bas aatla j hata. Aabhar.",
        "next": "Aagal nu.",
        "none": "Atyare kai claim baki nathi — supplier na badha bill match thai gaya chhe.",
    },
}


def _copy(lang: Optional[str]) -> dict:
    return _MESSAGES.get((lang or "en").lower(), _MESSAGES["en"])


def _question(record: dict, lang: Optional[str]) -> str:
    c = _copy(lang)
    return "\n\n".join([
        c["intro"].format(supplier=record.get("supplier_name") or "A supplier"),
        c["detail"].format(
            number=record.get("invoice_number") or "—",
            date=_pretty_date(record.get("invoice_date")),
            tax=_inr(record.get("tax")),
        ),
        c["ask"],
    ])


# --------------------------------------------------------------------------
# Asking
# --------------------------------------------------------------------------

async def ask_trader(
    trader_id: str,
    month: Optional[int] = None,
    year: Optional[int] = None,
    limit: int = MAX_ASKS_PER_RUN,
) -> dict:
    """
    Ask a trader about their largest unclaimed bills.

    Returns a result dict rather than raising, so the caller can report
    precisely what happened — including the awkward cases, which are the ones
    that matter: nothing unclaimed, nothing reconciled yet, no WhatsApp number,
    or already asked.
    """
    from app.api.gstr2b import get_missed_itc_snapshot

    db = get_supabase()
    rows = (
        db.table("traders")
        .select("id, whatsapp_number, language_pref, name, business_name")
        .eq("id", trader_id)
        .limit(1)
        .execute()
    ).data or []
    if not rows:
        return {"asked": 0, "status": "no_trader", "detail": "Trader not found."}
    trader = rows[0]
    phone = trader.get("whatsapp_number")
    if not phone:
        return {
            "asked": 0,
            "status": "no_whatsapp",
            "detail": "This client has no WhatsApp number on file, so there is nobody to ask.",
        }

    snapshot = await get_missed_itc_snapshot(trader_id, month, year)

    # The same caution the panel carries: before reconciliation has persisted
    # any match, every 2B row is unmatched by definition. Asking a trader about
    # forty bills they have in fact already sent us is how they stop replying.
    if not snapshot.get("reconciled"):
        return {
            "asked": 0,
            "status": "not_reconciled",
            "detail": (
                "Reconciliation has not been run for this period, so every "
                "GSTR-2B row still looks unmatched. Reconcile first — otherwise "
                "we would ask about bills the trader has already sent."
            ),
        }

    candidates = snapshot.get("records") or []
    if not candidates:
        return {"asked": 0, "status": "nothing_unclaimed", "detail": "Nothing unclaimed in this period."}

    # Never ask twice about the same 2B row, whatever the answer was.
    already = {
        e.get("record_id")
        for e in event_store.find(event_store.ITC_RECOVERY_REQUEST, trader_id, limit=400)
        if e.get("record_id")
    }
    fresh = [r for r in candidates if r.get("record_id") not in already][:max(1, limit)]
    if not fresh:
        return {
            "asked": 0,
            "status": "already_asked",
            "detail": "This trader has already been asked about every unclaimed bill in this period.",
        }

    queue: list[str] = []
    for record in fresh:
        event_id = event_store.record(trader_id, event_store.ITC_RECOVERY_REQUEST, {
            "record_id": record.get("record_id"),
            "supplier_gstin": record.get("supplier_gstin"),
            "supplier_name": record.get("supplier_name"),
            "invoice_number": record.get("invoice_number"),
            "invoice_date": record.get("invoice_date"),
            "tax": record.get("tax"),
            "taxable_value": record.get("taxable_value"),
            "period": snapshot.get("period"),
            "status": ASKED,
            "asked_at": date.today().isoformat(),
        })
        if event_id:
            queue.append(event_id)
        else:
            logger.error("itc_recovery: could not record ask for %s", record.get("record_id"))

    if not queue:
        return {
            "asked": 0,
            "status": "not_recorded",
            "detail": "Could not record the request, so nothing was sent. Nothing was asked that we cannot track.",
        }

    from app.services import whatsapp

    lang = trader.get("language_pref")
    first = event_store.get(queue[0]) or {}
    sent = await whatsapp.send_text_message(phone, _question(first, lang))
    if not sent:
        for event_id in queue:
            event_store.update(event_id, {"status": "send_failed"})
        return {
            "asked": 0,
            "status": "send_failed",
            "detail": "WhatsApp would not accept the message. Nothing was asked.",
        }

    set_conversation_state(phone, STATE, context={"queue": queue, "index": 0})
    return {
        "asked": len(queue),
        "status": "sent",
        "period": snapshot.get("period"),
        "detail": f"Asked about {len(queue)} unclaimed bill{'s' if len(queue) != 1 else ''}.",
        "total_tax": round(sum(float(r.get("tax") or 0) for r in fresh), 2),
    }


# --------------------------------------------------------------------------
# Replying
# --------------------------------------------------------------------------

_YES = {"yes", "y", "haan", "han", "ha", "hai", "hoy", "ho", "1", "yeah", "yep", "haa", "हाँ", "हा", "છે", "હા"}
_NO = {"no", "n", "nahi", "nai", "na", "nahin", "2", "nope", "नहीं", "ना", "ના"}
_STOP = {"stop", "ruko", "band", "cancel", "band karo", "बंद", "थांबा"}


def pending_for(trader_id: str) -> list[dict]:
    """Open recovery requests for a trader, newest first."""
    return [
        e for e in event_store.find(event_store.ITC_RECOVERY_REQUEST, trader_id, limit=200)
        if e.get("status") in OPEN_STATUSES
    ]


def _oldest_open(trader_id: str) -> Optional[dict]:
    """Fallback when the conversation cache is gone — see the module docstring."""
    open_items = [
        e for e in event_store.find(event_store.ITC_RECOVERY_REQUEST, trader_id, limit=200)
        if e.get("status") == ASKED
    ]
    return open_items[-1] if open_items else None


async def handle_reply(phone: str, trader: dict, text: str) -> bool:
    """
    Interpret a reply to a recovery question.

    Returns True when this module has dealt with the message. Returns False
    when the reply is not an answer to our question — "status", "help", a photo
    caption, anything — so the normal handler takes it. A trader who changes
    the subject must not be trapped in a loop waiting for a yes or a no; that
    is the difference between an assistant and a phone tree.
    """
    answer = (text or "").strip().lower().rstrip(".!")
    if not answer:
        return False

    conv = get_conversation_state(phone) or {}
    in_flow = conv.get("state") == STATE

    if answer in _STOP:
        if not in_flow:
            return False
        clear_conversation_state(phone)
        from app.services import whatsapp
        await whatsapp.send_text_message(phone, _copy(trader.get("language_pref"))["stop"])
        return True

    if answer not in _YES and answer not in _NO:
        return False

    context = conv.get("context") or {}
    queue: list[str] = list(context.get("queue") or [])
    index = int(context.get("index") or 0)

    current = None
    if in_flow and 0 <= index < len(queue):
        current = event_store.get(queue[index])
    if current is None:
        current = _oldest_open(trader["id"])
        queue, index = ([current["event_id"]] if current else []), 0
    if current is None:
        return False

    from app.services import whatsapp

    c = _copy(trader.get("language_pref"))
    said_yes = answer in _YES
    event_store.update(current["event_id"], {
        "status": HAS_BILL if said_yes else NO_BILL,
        "answered_at": date.today().isoformat(),
        "answer": "yes" if said_yes else "no",
    })
    await whatsapp.send_text_message(phone, c["yes"] if said_yes else c["no"])

    # "Yes" means a photo is coming, so hold this item open and stay put.
    # Moving on would leave the trader answering a question about bill two
    # while photographing bill one.
    if said_yes:
        set_conversation_state(phone, STATE, context={"queue": queue, "index": index, "awaiting_photo": True})
        return True

    next_index = index + 1
    while next_index < len(queue):
        nxt = event_store.get(queue[next_index])
        if nxt and nxt.get("status") == ASKED:
            set_conversation_state(phone, STATE, context={"queue": queue, "index": next_index})
            await whatsapp.send_text_message(phone, _question(nxt, trader.get("language_pref")))
            return True
        next_index += 1

    clear_conversation_state(phone)
    await whatsapp.send_text_message(phone, c["done"])
    return True


async def note_invoice_uploaded(trader: dict, invoice: dict) -> None:
    """
    A trader who was asked for a missing bill has just sent an invoice.

    Closes the matching open request if the invoice plausibly *is* that bill.
    The test is deliberately strict — same supplier GSTIN, or the same invoice
    number — because closing the wrong request would tell a CA a bill is in
    hand when it is not. Where nothing matches confidently, the request stays
    open and a human resolves it; that is the correct outcome, not a failure.

    Best-effort throughout: this runs after an invoice has already been stored
    and must never be able to fail that.
    """
    try:
        open_items = pending_for(trader["id"])
        if not open_items:
            return

        gstin = (invoice.get("gstin_supplier") or "").strip().upper()
        number = (invoice.get("invoice_number") or "").strip().lower()

        match = None
        for item in open_items:
            item_gstin = (item.get("supplier_gstin") or "").strip().upper()
            item_number = (item.get("invoice_number") or "").strip().lower()
            if gstin and item_gstin and gstin == item_gstin:
                match = item
                break
            if number and item_number and number == item_number:
                match = item
                break
        if not match:
            return

        event_store.update(match["event_id"], {
            "status": RESOLVED,
            "resolved_invoice_id": invoice.get("id"),
            "resolved_at": date.today().isoformat(),
        })
        logger.info(
            "itc_recovery: invoice %s closed recovery request %s",
            invoice.get("id"), match["event_id"],
        )

        # Move the conversation on to the next open question, if the trader is
        # still in the flow.
        phone = trader.get("whatsapp_number")
        conv = get_conversation_state(phone) if phone else None
        if not phone or not conv or conv.get("state") != STATE:
            return

        context = conv.get("context") or {}
        queue = list(context.get("queue") or [])
        from app.services import whatsapp

        for i, event_id in enumerate(queue):
            nxt = event_store.get(event_id)
            if nxt and nxt.get("status") == ASKED:
                set_conversation_state(phone, STATE, context={"queue": queue, "index": i})
                await whatsapp.send_text_message(phone, _question(nxt, trader.get("language_pref")))
                return

        clear_conversation_state(phone)
    except Exception as e:
        logger.warning("itc_recovery.note_invoice_uploaded failed: %s", e)


def summary_for(trader_id: str) -> dict:
    """What the dashboard panel renders: every request and where it stands."""
    events = event_store.find(event_store.ITC_RECOVERY_REQUEST, trader_id, limit=200)
    by_status: dict[str, int] = {}
    for e in events:
        by_status[e.get("status") or "unknown"] = by_status.get(e.get("status") or "unknown", 0) + 1
    return {
        "requests": events,
        "counts": by_status,
        "open": sum(1 for e in events if e.get("status") in OPEN_STATUSES),
        "recovered_tax": round(
            sum(float(e.get("tax") or 0) for e in events if e.get("status") == RESOLVED), 2
        ),
        "written_off_tax": round(
            sum(float(e.get("tax") or 0) for e in events if e.get("status") == NO_BILL), 2
        ),
    }
