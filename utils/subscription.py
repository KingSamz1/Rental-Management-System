"""
LandlordPro subscription logic: one-time setup fee, one calendar-month free
trial, then a recurring monthly fee. Lives in the same database as the rest
of the app (utils/db.py) rather than a separate DB, since this is one product.

This module intentionally supports only ONE active subscription row —
this app is built for a single landlord running their own instance, not
a multi-tenant SaaS backend. If you later host this for multiple
landlords, each landlord needs their own deployment/database (or this
module needs a landlord_id everywhere, which is a bigger change).

Billing dates always land on the same day-of-month as the original sign-up
(via _add_month), not a fixed day-count offset — a fixed "+29 days" trial
drifts against the calendar in any month longer than 29 days (e.g. signing
up Aug 17 would "end" Sep 15, two days short of a real month). Every
boundary here is calendar-month based so the due date always matches the
day the landlord originally signed up.
"""
import calendar
from datetime import date, datetime, timedelta
from utils.db import get_conn

SETUP_FEE = 50_000
MONTHLY_FEE = 100_000

# Access isn't cut the instant a due date passes — there's a short grace
# window after TRIAL_END / NEXT_PAYMENT_DATE before status flips to EXPIRED,
# so a landlord who's a day or two late doesn't get locked out mid-cycle.
GRACE_DAYS = 2


def _today():
    return date.today()


def _date_str(d):
    return d.isoformat()


def _parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _add_month(d, months=1):
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(d.day, last_day)
    return date(year, month, day)


def create_subscription(landlord_name, payment_reference, payment_method):
    """Called once, when the landlord pays the setup fee and starts their trial."""
    start = _today()
    # One calendar month, not a fixed day count — see module docstring.
    trial_end = _add_month(start) - timedelta(days=1)
    now = datetime.now().isoformat()

    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO subscription
               (landlord_name, setup_fee, setup_paid, setup_payment_reference, setup_payment_method,
                trial_start, trial_end, monthly_fee, status, created_at, updated_at)
               VALUES (?, ?, 1, ?, ?, ?, ?, ?, 'TRIAL', ?, ?)""",
            (landlord_name, SETUP_FEE, payment_reference.strip(), payment_method,
             _date_str(start), _date_str(trial_end), MONTHLY_FEE, now, now),
        )
        return cur.lastrowid


def get_subscription():
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM subscription ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None


def _due_date(sub):
    """The date payment is due for the current cycle (trial's last day + 1,
    or the stored next_payment_date once on a paid cycle)."""
    if sub["status"] == "TRIAL":
        return _parse_date(sub["trial_end"]) + timedelta(days=1)
    if sub["status"] == "ACTIVE":
        return _parse_date(sub["next_payment_date"])
    return None


def update_subscription_status():
    """Recomputes TRIAL -> EXPIRED or ACTIVE -> EXPIRED based on today's date,
    allowing a GRACE_DAYS window past the due date before locking the account.
    Call this before reading status anywhere it matters. Adds two read-only
    convenience keys to the returned dict: `past_due` and `grace_days_left`."""
    sub = get_subscription()
    if not sub:
        return None

    today = _today()
    status = sub["status"]
    past_due = False
    grace_days_left = 0

    if status in ("TRIAL", "ACTIVE"):
        due = _due_date(sub)
        lockout_day = due + timedelta(days=GRACE_DAYS)
        if today >= lockout_day:
            status = "EXPIRED"
        elif today >= due:
            past_due = True
            grace_days_left = (lockout_day - today).days

    if status != sub["status"]:
        with get_conn() as conn:
            conn.execute(
                "UPDATE subscription SET status = ?, updated_at = ? WHERE id = ?",
                (status, datetime.now().isoformat(), sub["id"]),
            )
        sub["status"] = status

    sub["past_due"] = past_due
    sub["grace_days_left"] = grace_days_left
    return sub


def days_remaining():
    sub = update_subscription_status()
    if not sub:
        return 0

    today = _today()
    if sub["status"] == "TRIAL":
        end_date = _parse_date(sub["trial_end"])
    elif sub["status"] == "ACTIVE":
        end_date = _parse_date(sub["next_payment_date"]) - timedelta(days=1)
    else:
        return 0

    return max(0, (end_date - today).days + 1)


def system_active():
    """True if the landlord currently has full access (trial, paid, or still
    within the post-due grace window)."""
    sub = update_subscription_status()
    if not sub:
        return False
    return sub["status"] in ("TRIAL", "ACTIVE")


def renew_subscription(payment_reference, payment_method, note=""):
    sub = update_subscription_status()
    if not sub:
        raise ValueError("No landlord account exists yet.")
    if not payment_reference.strip():
        raise ValueError("Payment reference is required.")

    with get_conn() as conn:
        duplicate = conn.execute(
            "SELECT id FROM subscription_payments WHERE transaction_reference = ?",
            (payment_reference.strip(),),
        ).fetchone()
        if duplicate:
            raise ValueError("This payment reference has already been used.")

        today = _today()

        if sub["status"] == "TRIAL":
            period_start = _parse_date(sub["trial_end"]) + timedelta(days=1)
        elif sub["status"] == "ACTIVE":
            period_start = _parse_date(sub["next_payment_date"])
        else:  # EXPIRED
            period_start = today

        period_end = _add_month(period_start) - timedelta(days=1)
        next_payment = _add_month(period_start)
        now = datetime.now().isoformat()

        conn.execute(
            """INSERT INTO subscription_payments
               (subscription_id, amount, payment_date, payment_method, transaction_reference,
                period_start, period_end, note, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (sub["id"], MONTHLY_FEE, _date_str(today), payment_method, payment_reference.strip(),
             _date_str(period_start), _date_str(period_end), note.strip(), now),
        )

        conn.execute(
            """UPDATE subscription
               SET status = 'ACTIVE', subscription_start = ?, next_payment_date = ?, updated_at = ?
               WHERE id = ?""",
            (_date_str(period_start), _date_str(next_payment), now, sub["id"]),
        )

    return get_subscription()


def subscription_payment_history():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM subscription_payments ORDER BY payment_date DESC"
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Testing / admin-only helpers. Not linked to any tenant-facing flow — these
# exist so you (the landlord/developer) can exercise expiry and lockout
# behavior without waiting a real month. Safe to leave in the deployed app:
# only someone already logged in as the admin can reach them.
# ---------------------------------------------------------------------------

def fast_forward(days):
    """Shift the current cycle's boundary date `days` into the past, so it
    behaves as if that much time has passed. Use a positive number to move
    toward/through expiry, negative to push it back out. Returns the
    recomputed subscription dict."""
    sub = get_subscription()
    if not sub:
        raise ValueError("No landlord account exists yet.")

    with get_conn() as conn:
        if sub["status"] == "TRIAL":
            new_end = _parse_date(sub["trial_end"]) - timedelta(days=days)
            conn.execute(
                "UPDATE subscription SET trial_end = ?, updated_at = ? WHERE id = ?",
                (_date_str(new_end), datetime.now().isoformat(), sub["id"]),
            )
        else:
            current = sub["next_payment_date"]
            if not current:
                raise ValueError("This subscription has no next payment date to shift.")
            new_next = _parse_date(current) - timedelta(days=days)
            conn.execute(
                "UPDATE subscription SET next_payment_date = ?, updated_at = ? WHERE id = ?",
                (_date_str(new_next), datetime.now().isoformat(), sub["id"]),
            )

    return update_subscription_status()


def force_expire():
    """Immediately mark the subscription EXPIRED, bypassing the grace
    window — for testing the locked-out experience right now."""
    sub = get_subscription()
    if not sub:
        raise ValueError("No landlord account exists yet.")
    with get_conn() as conn:
        conn.execute(
            "UPDATE subscription SET status = 'EXPIRED', updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), sub["id"]),
        )
    return get_subscription()
