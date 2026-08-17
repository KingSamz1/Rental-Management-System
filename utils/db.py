"""
Database layer for the Rental Management app.
SQLite, single-file, created automatically on first run.
"""
import sqlite3
import os
from datetime import datetime, date
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


def init_db():
    """Create all tables if they don't exist. Safe to call every run."""
    with get_conn() as conn:
        c = conn.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_id INTEGER NOT NULL,
            unit_name TEXT NOT NULL,
            monthly_rent REAL NOT NULL DEFAULT 0,
            water_rate REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'vacant',  -- vacant / occupied
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
            id_number TEXT,             -- the actual ID/passport number
            id_document_path TEXT,      -- path to uploaded photo/scan of the ID
            move_in_date TEXT,
            move_out_date TEXT,
            status TEXT NOT NULL DEFAULT 'active',  -- active / vacated
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE
        )
        """)

        # One row per tenant per billing month = the rent charge for that month
        c.execute("""
        CREATE TABLE IF NOT EXISTS rent_charges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            period TEXT NOT NULL,          -- 'YYYY-MM'
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
            charge_id INTEGER,              -- linked rent_charges row, nullable (advance payments may be unlinked)
            amount REAL NOT NULL,
            payment_date TEXT NOT NULL,
            method TEXT NOT NULL DEFAULT 'cash',  -- cash / mobile_money / bank
            momo_reference TEXT,
            momo_provider TEXT,             -- MTN / Airtel / etc
            payment_type TEXT NOT NULL DEFAULT 'rent',  -- rent / water / deposit / advance / other
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
            status TEXT NOT NULL DEFAULT 'held',  -- held / refunded / forfeited
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

        # Migration: add download_name to receipts table if it doesn't exist yet
        # (covers databases created before this column was introduced).
        existing_cols = [row["name"] for row in c.execute("PRAGMA table_info(receipts)").fetchall()]
        if "download_name" not in existing_cols:
            c.execute("ALTER TABLE receipts ADD COLUMN download_name TEXT")

        # Migration: add id_document_path / id_number to tenants if missing.
        existing_tenant_cols = [row["name"] for row in c.execute("PRAGMA table_info(tenants)").fetchall()]
        if "id_number" not in existing_tenant_cols:
            c.execute("ALTER TABLE tenants ADD COLUMN id_number TEXT")
        if "id_document_path" not in existing_tenant_cols:
            c.execute("ALTER TABLE tenants ADD COLUMN id_document_path TEXT")

        c.execute("""
        CREATE TABLE IF NOT EXISTS reminders_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            period TEXT NOT NULL,
            message TEXT NOT NULL,
            channel TEXT NOT NULL DEFAULT 'whatsapp',
            status TEXT NOT NULL DEFAULT 'prepared',  -- prepared / sent / failed
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS subscription (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            landlord_name TEXT NOT NULL,
            setup_fee REAL NOT NULL DEFAULT 50000,
            setup_paid INTEGER NOT NULL DEFAULT 0,
            setup_payment_reference TEXT,
            setup_payment_method TEXT,
            trial_start TEXT,
            trial_end TEXT,
            subscription_start TEXT,
            next_payment_date TEXT,
            monthly_fee REAL NOT NULL DEFAULT 100000,
            status TEXT NOT NULL DEFAULT 'TRIAL',  -- TRIAL / ACTIVE / EXPIRED
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
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

        conn.commit()


def get_setting(key, default=None):
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key, value):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
