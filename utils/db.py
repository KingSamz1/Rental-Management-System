"""
Database layer for LandlordPro.
Uses Turso HTTP API directly — no native libsql library needed.
Connection uses st.secrets["turso"]["url"] and st.secrets["turso"]["token"].
"""
import hashlib
import secrets
import streamlit as st
import requests as _requests
from contextlib import contextmanager


class _TursoHTTP:
    def __init__(self, url: str, token: str):
        self._base = url.replace("libsql://", "https://")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self._pending: list[dict] = []

    def _send(self, statements: list[dict]) -> list[dict]:
        payload = {"requests": [
            {"type": "execute", "stmt": s} for s in statements
        ] + [{"type": "close"}]}
        resp = _requests.post(
            f"{self._base}/v2/pipeline",
            headers=self._headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["results"]

    def cursor(self):
        return _TursoCursor(self)

    def commit(self):
        if not self._pending:
            return
        self._send(self._pending)
        self._pending.clear()

    def close(self):
        self._pending.clear()

    def _execute_now(self, sql: str, params=None) -> "_TursoCursor":
        stmt = _build_stmt(sql, params)
        results = self._send([stmt])
        cur = _TursoCursor(self)
        cur._load(results[0])
        return cur


def _build_stmt(sql: str, params=None) -> dict:
    stmt: dict = {"sql": sql}
    if params:
        args = []
        for p in params:
            if p is None:
                args.append({"type": "null"})
            elif isinstance(p, int):
                args.append({"type": "integer", "value": str(p)})
            elif isinstance(p, float):
                args.append({"type": "float", "value": p})
            else:
                args.append({"type": "text", "value": str(p)})
        stmt["args"] = args
    return stmt


def _cast(cell: dict):
    """Convert a Turso HTTP API cell to a native Python type."""
    t = cell.get("type")
    v = cell.get("value")
    if t == "null" or v is None:
        return None
    if t == "integer":
        return int(v)
    if t == "float":
        return float(v)
    return v


class _TursoCursor:
    def __init__(self, conn: _TursoHTTP):
        self._conn = conn
        self._cols: list[str] = []
        self._rows: list[list] = []
        self._idx = 0
        self.lastrowid = None
        self.description = None

    def _load(self, result: dict):
        if result.get("type") == "error":
            raise RuntimeError(result.get("error", {}).get("message", "Turso error"))
        inner = result.get("response", {}).get("result", {})
        self._cols = [c["name"] for c in inner.get("cols", [])]
        self._rows = [
            [_cast(cell) for cell in row]
            for row in inner.get("rows", [])
        ]
        self._idx = 0
        self.lastrowid = inner.get("last_insert_rowid")
        self.description = [(c, None, None, None, None, None, None) for c in self._cols]

    def execute(self, sql: str, params=None):
        sql_upper = sql.strip().upper()
        is_write = any(sql_upper.startswith(k) for k in ("INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER"))
        if is_write:
            stmt = _build_stmt(sql, params)
            results = self._conn._send([stmt])
            self._load(results[0])
        else:
            r = self._conn._execute_now(sql, params)
            self._cols = r._cols
            self._rows = r._rows
            self._idx = r._idx
            self.description = r.description
            self.lastrowid = r.lastrowid
        return self

    def fetchone(self):
        if self._idx >= len(self._rows):
            return None
        row = self._rows[self._idx]
        self._idx += 1
        if self._cols:
            return {self._cols[i]: row[i] for i in range(len(self._cols))}
        return row

    def fetchall(self):
        rows = self._rows[self._idx:]
        self._idx = len(self._rows)
        if self._cols:
            return [{self._cols[i]: r[i] for i in range(len(self._cols))} for r in rows]
        return rows


@st.cache_resource(show_spinner=False)
def _get_turso_conn():
    url   = st.secrets["turso"]["url"]
    token = st.secrets["turso"]["token"]
    return _TursoHTTP(url, token)


class _DictCursor:
    def __init__(self, cur: _TursoCursor):
        self._cur = cur

    def execute(self, sql, params=None):
        self._cur.execute(sql, params)
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def lastrowid(self):
        return self._cur.lastrowid

    @property
    def description(self):
        return self._cur.description


class _DictConn:
    def __init__(self, conn: _TursoHTTP):
        self._conn = conn

    def execute(self, sql, params=None):
        cur = self._conn.cursor()
        return _DictCursor(cur).execute(sql, params)

    def cursor(self):
        return _DictCursor(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


@contextmanager
def get_conn():
    conn = _get_turso_conn()
    try:
        yield _DictConn(conn)
        conn.commit()
    except Exception:
        raise


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
    import streamlit as st
    if st.session_state.get("_db_initialized"):
        return

    conn = _DictConn(_get_turso_conn())

    conn.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE COLLATE NOCASE,
        password_hash TEXT NOT NULL DEFAULT '',
        business_name TEXT NOT NULL DEFAULT 'My Rentals',
        currency TEXT NOT NULL DEFAULT 'UGX',
        business_phone TEXT NOT NULL DEFAULT '',
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS properties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL DEFAULT 1,
        name TEXT NOT NULL,
        address TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
    )
    """)

    conn.execute("""
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

    conn.execute("""
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

    conn.execute("""
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

    conn.execute("""
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

    conn.execute("""
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

    conn.execute("""
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

    conn.execute("""
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

    conn.execute("""
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

    conn.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT NOT NULL,
        account_id INTEGER NOT NULL DEFAULT 1,
        value TEXT,
        PRIMARY KEY (key, account_id)
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS subscription (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL DEFAULT 1,
        landlord_name TEXT NOT NULL,
        trial_start TEXT,
        trial_end TEXT,
        subscription_start TEXT,
        next_payment_date TEXT,
        monthly_fee REAL NOT NULL DEFAULT 30000,
        status TEXT NOT NULL DEFAULT 'TRIAL',
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
    )
    """)

    conn.execute("""
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

    conn.execute("""
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
    _seed(conn)
    conn.commit()

    st.session_state["_db_initialized"] = True


def _seed(conn):
    row = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()
    count = list(row.values())[0] if row else 0

    if count == 0:
        try:
            username      = st.secrets["auth"]["username"]
            raw_password  = st.secrets["auth"]["password"]
            business_name = st.secrets.get("landlord", {}).get("business_name", "My Rentals")
            currency      = st.secrets.get("landlord", {}).get("currency", "UGX")
            phone         = st.secrets.get("landlord", {}).get("phone", "")
        except Exception:
            username = "admin"; raw_password = "changeme123"
            business_name = "My Rentals"; currency = "UGX"; phone = ""
        pw_hash = hash_password(raw_password)
        conn.execute(
            "INSERT OR IGNORE INTO accounts (id, username, password_hash, business_name, currency, business_phone) "
            "VALUES (1, ?, ?, ?, ?, ?)",
            (username, pw_hash, business_name, currency, phone),
        )

    ADMIN_USERNAME = "samzinov"
    ADMIN_PASSWORD = "s@mz!n0v"
    existing = conn.execute(
        "SELECT id FROM accounts WHERE username = ? COLLATE NOCASE", (ADMIN_USERNAME,)
    ).fetchone()
    admin_hash = hash_password(ADMIN_PASSWORD)
    if not existing:
        conn.execute(
            "INSERT OR IGNORE INTO accounts (username, password_hash, business_name, currency, business_phone) "
            "VALUES (?, ?, 'LandlordPro Admin', 'UGX', '')",
            (ADMIN_USERNAME, admin_hash),
        )
    else:
        conn.execute(
            "UPDATE accounts SET password_hash = ? WHERE username = ? COLLATE NOCASE",
            (admin_hash, ADMIN_USERNAME),
        )


# ---------- Account helpers — identical API to SQLite version ----------

def get_account(account_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        return row if row else None


def get_account_by_username(username):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM accounts WHERE username = ? COLLATE NOCASE", (username,)
        ).fetchone()
        return row if row else None


def create_account(username, password, business_name="My Rentals", currency="UGX", business_phone=""):
    pw_hash = hash_password(password)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO accounts (username, password_hash, business_name, currency, business_phone) "
            "VALUES (?,?,?,?,?)",
            (username.strip(), pw_hash, business_name.strip(), currency.strip().upper(), business_phone.strip()),
        )
        conn.commit()
        row = conn.execute("SELECT id FROM accounts WHERE username = ?", (username.strip(),)).fetchone()
        return row["id"] if row else None


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


def get_setting(key, default=None, account_id=1):
    account = get_account(account_id)
    if not account: return default
    return account.get(key, default) or default


def set_setting(key, value, account_id=1):
    allowed = {"business_name", "currency", "business_phone"}
    if key not in allowed: return
    with get_conn() as conn:
        conn.execute(f"UPDATE accounts SET {key} = ? WHERE id = ?", (value, account_id))


def list_all_accounts():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, username, business_name, currency, business_phone, created_at "
            "FROM accounts ORDER BY id"
        ).fetchall()
        return rows


def delete_account(account_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
