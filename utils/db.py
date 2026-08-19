"""
Database layer for LandlordPro.
SQLite, single-file, created automatically on first run.

Multi-account: every major table has an account_id foreign key so each
landlord sees only their own data. The migration block at the bottom of
init_db() handles existing single-landlord databases (adds account_id = 1
to every existing row) so nothing is lost when upgrading.
"""
import sqlite3
import os
import hashlib
import secrets
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "rental.db")


def _ensure_data_dir():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


@contextmanager
def get_conn():
    _ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ---------- Password helpers ----------

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split(":", 1)
        return hashlib.sha256((salt + password).encode()).hexdigest() == h
    except Exception:
        return False


# ---------- Schema ----------

def init_db():
    """Create all tables if they don't exist. Safe to call every run."""
    with get_conn() as conn:
        c = conn.cursor()

        # Accounts table — one row per landlord
        c.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            business_name TEXT NOT NULL DEFAULT 'My Rentals',
            currency TEXT NOT NULL DEFAULT 'UGX',
            business_phone TEXT NOT NULL DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL DEFAULT 1,
            name TEXT NOT NULL,
            address TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_id INTEGER NOT NULL,
            unit_name TEXT NOT NULL,
            monthly_rent REAL NOT NULL DEFAULT 0,
            water_rate REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'vacant',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            national_id TEXT,
            id_number TEXT,
            id_document_path TEXT,
            move_in_date TEXT,
            move_out_date TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS rent_charges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            period TEXT NOT NULL,
            rent_amount REAL NOT NULL DEFAULT 0,
            water_amount REAL NOT NULL DEFAULT 0,
            other_amount REAL NOT NULL DEFAULT 0,
            note TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
            UNIQUE(tenant_id, period)
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            charge_id INTEGER,
            amount REAL NOT NULL,
            payment_date TEXT NOT NULL,
            method TEXT NOT NULL DEFAULT 'cash',
            momo_reference TEXT,
            momo_provider TEXT,
            payment_type TEXT NOT NULL DEFAULT 'rent',
            note TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
            FOREIGN KEY (charge_id) REFERENCES rent_charges(id) ON DELETE SET NULL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            date_received TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'held',
            note TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS advance_rent (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            months_covered INTEGER NOT NULL DEFAULT 1,
            date_received TEXT NOT NULL,
            note TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_id INTEGER NOT NULL,
            receipt_number TEXT NOT NULL UNIQUE,
            file_path TEXT NOT NULL,
            download_name TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE CASCADE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS reminders_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            period TEXT NOT NULL,
            message TEXT NOT NULL,
            channel TEXT NOT NULL DEFAULT 'whatsapp',
            status TEXT NOT NULL DEFAULT 'prepared',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        )
        """)

        # Per-account settings (replaces global settings table)
        c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT NOT NULL,
            account_id INTEGER NOT NULL DEFAULT 1,
            value TEXT,
            PRIMARY KEY (key, account_id)
        )
        """)

        # Per-account subscription
        c.execute("""
        CREATE TABLE IF NOT EXISTS subscription (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL DEFAULT 1,
            landlord_name TEXT NOT NULL,
            trial_start TEXT,
            trial_end TEXT,
            subscription_start TEXT,
            next_payment_date TEXT,
            monthly_fee REAL NOT NULL DEFAULT 100000,
            status TEXT NOT NULL DEFAULT 'TRIAL',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS subscription_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subscription_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_date TEXT NOT NULL,
            payment_method TEXT,
            transaction_reference TEXT UNIQUE,
            period_start TEXT,
            period_end TEXT,
            note TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (subscription_id) REFERENCES subscription(id) ON DELETE CASCADE
        )
        """)

        # One-time renewal codes generated by admin, redeemed by clients
        c.execute("""
        CREATE TABLE IF NOT EXISTS renewal_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            months INTEGER NOT NULL DEFAULT 1,
            created_by INTEGER NOT NULL,
            used_by INTEGER,
            used_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        conn.commit()

        # ---- Migrations for existing single-landlord databases ----
        _migrate(c, conn)

        conn.commit()


def _col_exists(c, table, col):
    cols = [r["name"] for r in c.execute(f"PRAGMA table_info({table})").fetchall()]
    return col in cols


def _migrate(c, conn):
    """Non-destructive upgrades: add missing columns, seed account #1 from legacy data."""

    # receipts.download_name
    if not _col_exists(c, "receipts", "download_name"):
        c.execute("ALTER TABLE receipts ADD COLUMN download_name TEXT")

    # tenants.id_number / id_document_path
    if not _col_exists(c, "tenants", "id_number"):
        c.execute("ALTER TABLE tenants ADD COLUMN id_number TEXT")
    if not _col_exists(c, "tenants", "id_document_path"):
        c.execute("ALTER TABLE tenants ADD COLUMN id_document_path TEXT")

    # properties.account_id
    if not _col_exists(c, "properties", "account_id"):
        c.execute("ALTER TABLE properties ADD COLUMN account_id INTEGER NOT NULL DEFAULT 1")

    # settings: migrate old single-key table to (key, account_id) if needed
    old_settings_cols = [r["name"] for r in c.execute("PRAGMA table_info(settings)").fetchall()]
    if "account_id" not in old_settings_cols and "key" in old_settings_cols:
        # old schema: (key TEXT PRIMARY KEY, value TEXT)
        old_rows = c.execute("SELECT key, value FROM settings").fetchall()
        c.execute("DROP TABLE settings")
        c.execute("""
            CREATE TABLE settings (
                key TEXT NOT NULL,
                account_id INTEGER NOT NULL DEFAULT 1,
                value TEXT,
                PRIMARY KEY (key, account_id)
            )
        """)
        for row in old_rows:
            c.execute("INSERT OR IGNORE INTO settings (key, account_id, value) VALUES (?, 1, ?)",
                      (row["key"], row["value"]))

    # Seed account #1 from legacy secrets.toml if no accounts exist yet.
    # IMPORTANT: this must run BEFORE the subscription rebuild below so that
    # account #1 exists when old subscription rows are re-inserted with
    # account_id = 1 (otherwise the foreign-key constraint fires).
    existing_accounts = c.execute("SELECT COUNT(*) c FROM accounts").fetchone()["c"]
    if existing_accounts == 0:
        import streamlit as st
        try:
            username = st.secrets["auth"]["username"]
            raw_password = st.secrets["auth"]["password"]
            business_name = st.secrets.get("landlord", {}).get("business_name", "My Rentals")
            currency = st.secrets.get("landlord", {}).get("currency", "UGX")
            phone = st.secrets.get("landlord", {}).get("phone", "")
        except Exception:
            username = "admin"
            raw_password = "changeme123"
            business_name = "My Rentals"
            currency = "UGX"
            phone = ""

        pw_hash = hash_password(raw_password)
        c.execute(
            """INSERT OR IGNORE INTO accounts (id, username, password_hash, business_name, currency, business_phone)
               VALUES (1, ?, ?, ?, ?, ?)""",
            (username, pw_hash, business_name, currency, phone),
        )
        # Migrate any existing settings rows for account 1 to accounts table
        biz = c.execute("SELECT value FROM settings WHERE key='business_name' AND account_id=1").fetchone()
        cur = c.execute("SELECT value FROM settings WHERE key='currency' AND account_id=1").fetchone()
        ph = c.execute("SELECT value FROM settings WHERE key='business_phone' AND account_id=1").fetchone()
        if biz:
            c.execute("UPDATE accounts SET business_name=? WHERE id=1", (biz["value"],))
        if cur:
            c.execute("UPDATE accounts SET currency=? WHERE id=1", (cur["value"],))
        if ph:
            c.execute("UPDATE accounts SET business_phone=? WHERE id=1", (ph["value"],))

    # Seed the admin account (samzinov) — always ensure it exists with the correct password
    ADMIN_USERNAME = "samzinov"
    ADMIN_PASSWORD = "s@mz!n0v"
    existing_admin = c.execute(
        "SELECT id FROM accounts WHERE username = ? COLLATE NOCASE", (ADMIN_USERNAME,)
    ).fetchone()
    if not existing_admin:
        admin_hash = hash_password(ADMIN_PASSWORD)
        c.execute(
            """INSERT OR IGNORE INTO accounts (username, password_hash, business_name, currency, business_phone)
               VALUES (?, ?, 'LandlordPro Admin', 'UGX', '')""",
            (ADMIN_USERNAME, admin_hash),
        )
    else:
        # Always keep admin password in sync (so a deploy always resets it)
        admin_hash = hash_password(ADMIN_PASSWORD)
        c.execute(
            "UPDATE accounts SET password_hash = ? WHERE username = ? COLLATE NOCASE",
            (admin_hash, ADMIN_USERNAME),
        )

    # subscription: drop setup_fee / setup_paid columns (they no longer exist in new schema)
    # and add account_id if missing. SQLite can't DROP COLUMN before 3.35, so we
    # recreate the table only when needed.
    # NOTE: runs after account #1 is seeded so FK (account_id = 1) is satisfied.
    sub_cols = {r["name"] for r in c.execute("PRAGMA table_info(subscription)").fetchall()}
    needs_sub_rebuild = "account_id" not in sub_cols or "setup_fee" in sub_cols
    if needs_sub_rebuild and sub_cols:
        old_subs = c.execute("SELECT * FROM subscription").fetchall()
        c.execute("DROP TABLE IF EXISTS subscription")
        c.execute("""
            CREATE TABLE subscription (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL DEFAULT 1,
                landlord_name TEXT NOT NULL,
                trial_start TEXT,
                trial_end TEXT,
                subscription_start TEXT,
                next_payment_date TEXT,
                monthly_fee REAL NOT NULL DEFAULT 100000,
                status TEXT NOT NULL DEFAULT 'TRIAL',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            )
        """)
        for row in old_subs:
            c.execute("""
                INSERT OR IGNORE INTO subscription
                (id, account_id, landlord_name, trial_start, trial_end,
                 subscription_start, next_payment_date, monthly_fee, status, created_at, updated_at)
                VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["id"],
                row["landlord_name"],
                row["trial_start"] if "trial_start" in row.keys() else None,
                row["trial_end"] if "trial_end" in row.keys() else None,
                row["subscription_start"] if "subscription_start" in row.keys() else None,
                row["next_payment_date"] if "next_payment_date" in row.keys() else None,
                row["monthly_fee"] if "monthly_fee" in row.keys() else 100000,
                row["status"] if "status" in row.keys() else "TRIAL",
                row["created_at"] if "created_at" in row.keys() else datetime.now().isoformat(),
                row["updated_at"] if "updated_at" in row.keys() else datetime.now().isoformat(),
            ))


# ---------- Account helpers ----------

def get_account(account_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        return dict(row) if row else None


def get_account_by_username(username):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM accounts WHERE username = ? COLLATE NOCASE", (username,)).fetchone()
        return dict(row) if row else None


def create_account(username, password, business_name="My Rentals", currency="UGX", business_phone=""):
    pw_hash = hash_password(password)
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO accounts (username, password_hash, business_name, currency, business_phone) VALUES (?,?,?,?,?)",
            (username.strip(), pw_hash, business_name.strip(), currency.strip().upper(), business_phone.strip()),
        )
        return cur.lastrowid


def update_account_settings(account_id, business_name, currency, business_phone):
    with get_conn() as conn:
        conn.execute(
            "UPDATE accounts SET business_name=?, currency=?, business_phone=? WHERE id=?",
            (business_name, currency, business_phone, account_id),
        )


def update_account_password(account_id, new_password):
    with get_conn() as conn:
        conn.execute(
            "UPDATE accounts SET password_hash=? WHERE id=?",
            (hash_password(new_password), account_id),
        )


# ---------- Legacy settings shim (now stored on accounts row) ----------
# These wrappers keep every page working without changes to how they call
# get_setting/set_setting — they just look up the active account_id from
# the accounts table instead of a flat settings table.

def get_setting(key, default=None, account_id=1):
    """Read business_name / currency / business_phone off the accounts row."""
    account = get_account(account_id)
    if not account:
        return default
    return account.get(key, default) or default


def set_setting(key, value, account_id=1):
    """Write business_name / currency / business_phone to the accounts row."""
    allowed = {"business_name", "currency", "business_phone"}
    if key not in allowed:
        return
    with get_conn() as conn:
        conn.execute(f"UPDATE accounts SET {key} = ? WHERE id = ?", (value, account_id))
