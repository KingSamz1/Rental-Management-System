"""
WhatsApp reminder preparation.

This module deliberately separates MESSAGE PREPARATION from SENDING.
Preparation (building the reminder text, logging it) works today with no
external dependency. Sending is a swappable interface: `send_via_provider()`
is where you'd plug in the WhatsApp Business API (Meta Cloud API), Twilio,
or a local aggregator later. Right now it's a stub that raises, so it's
obvious in the UI what still needs to be wired up.
"""
from utils.db import get_conn
from utils.logic import get_tenant, tenant_balance
from utils.db import get_setting


def build_reminder_message(tenant_id, period):
    tenant = get_tenant(tenant_id)
    balance = tenant_balance(tenant_id)
    currency = get_setting("currency", "UGX")
    business_name = get_setting("business_name", "Your Landlord")

    if balance["balance"] > 0:
        body = (
            f"Dear {tenant['full_name']}, this is a reminder from {business_name} that "
            f"your rent balance for {tenant['unit_name']} ({tenant['property_name']}) as of now is "
            f"{currency} {balance['balance']:,.0f}. Kindly make payment at your earliest convenience. Thank you."
        )
    else:
        body = (
            f"Dear {tenant['full_name']}, thank you for keeping your rent account for "
            f"{tenant['unit_name']} ({tenant['property_name']}) up to date."
        )
    return body


def prepare_and_log_reminder(tenant_id, period):
    """Build the message and store it in reminders_log with status='prepared'.
    This is safe to call with no external API — it's the 'preparation' half."""
    message = build_reminder_message(tenant_id, period)
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO reminders_log (tenant_id, period, message, channel, status)
               VALUES (?, ?, ?, 'whatsapp', 'prepared')""",
            (tenant_id, period, message),
        )
        return {"id": cur.lastrowid, "message": message}


def send_via_provider(reminder_id, provider_config=None):
    """
    Plug your WhatsApp Business API / Twilio / aggregator call in here.
    Expected flow once wired up:
        1. Look up the reminders_log row by reminder_id
        2. POST to your provider's send-message endpoint with the tenant phone + message
        3. Update reminders_log.status to 'sent' or 'failed' based on the response

    Left unimplemented on purpose so it fails loudly instead of pretending to send.
    """
    raise NotImplementedError(
        "No WhatsApp provider is connected yet. Wire this function to the WhatsApp "
        "Business Cloud API (or Twilio/another aggregator) to enable real sending."
    )


def list_reminders(tenant_id=None, status=None):
    with get_conn() as conn:
        q = """SELECT r.*, t.full_name, t.phone FROM reminders_log r
               JOIN tenants t ON t.id = r.tenant_id WHERE 1=1"""
        params = []
        if tenant_id:
            q += " AND r.tenant_id = ?"
            params.append(tenant_id)
        if status:
            q += " AND r.status = ?"
            params.append(status)
        q += " ORDER BY r.created_at DESC"
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def whatsapp_click_to_chat_link(phone, message):
    """Fallback that works with zero API integration: opens WhatsApp Web/App
    with the message pre-filled, for manual send-by-click."""
    import urllib.parse
    clean_phone = "".join(ch for ch in phone if ch.isdigit())
    encoded_message = urllib.parse.quote(message)
    return f"https://wa.me/{clean_phone}?text={encoded_message}"
