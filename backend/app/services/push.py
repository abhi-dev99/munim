"""
Munim.ai — Expo push notifications.

One job: send a push notification to a trader's registered device (see
migrations/add_trader_push_token.sql, api/dashboard.py's
register_push_token). This is an ADDITIONAL delivery channel for alerts
that already work over WhatsApp (main.py's deadline_alerts job) -- never
the only way an alert reaches a trader, since most traders have no push
token registered at all (WhatsApp-only, or haven't opened the native app).
"""

import logging
import httpx

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


async def send_push_notification(token: str, title: str, body: str) -> bool:
    """
    Sends one push notification via Expo's push service. Never raises --
    a push failure (bad/expired token, Expo outage) should never break the
    WhatsApp send it accompanies, so this logs and returns False instead.
    """
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                EXPO_PUSH_URL,
                json={"to": token, "title": title, "body": body, "sound": "default"},
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            # Expo's own per-notification status, distinct from the HTTP
            # status -- a malformed/expired token still returns HTTP 200
            # with an "error" status inside the body.
            ticket = (data.get("data") or {})
            if ticket.get("status") == "error":
                logger.warning(f"Expo push rejected: {ticket.get('message')}")
                return False
            return True
    except Exception as e:
        logger.warning(f"Push notification failed (non-fatal): {e}")
        return False
