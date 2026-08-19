"""
Business logic: properties, units, tenants, charges, payments, balances.
Kept separate from the Streamlit UI so it can be tested/reasoned about on its own.
"""
import os
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
from utils.db import get_conn

TENANT_DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tenant_documents")


def save_tenant_id_document(tenant_id, uploaded_file):
    """Save an uploaded ID/passport photo to disk and return its path.
    uploaded_file is a Streamlit UploadedFile object."""
    os.makedirs(TENANT_DOCS_DIR, exist_ok=True)
    ext = os.path.splitext(uploaded_file.name)[1] or ".jpg"
    file_path = os.path.join(TENANT_DOCS_DIR, f"tenant_{tenant_id}_id{ext}")
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path


# ---------- Properties ----------

def add_property(name, address="", account_id=1):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO properties (account_id, name, address) VALUES (?, ?, ?)",
            (account_id, name, address),
        )
        return cur.lastrowid


def list_properties(account_id=1):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM properties WHERE account_id = ? ORDER BY name", (account_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_property(property_id, name, address=""):
    with get_conn() as conn:
        conn.execute("UPDATE properties SET name = ?, address = ? WHERE id = ?", (name, address, property_id))


def delete_property(property_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM properties WHERE id = ?", (property_id,))


# ---------- Units ----------

def add_unit(property_id, unit_name, monthly_rent, water_rate=0):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO units (property_id, unit_name, monthly_rent, water_rate) VALUES (?, ?, ?, ?)",
            (property_id, unit_name, monthly_rent, water_rate),
        )
        return cur.lastrowid


def list_units(property_id=None, account_id=1):
    with get_conn() as conn:
        if property_id:
            rows = conn.execute(
                """SELECT u.*, p.name as property_name FROM units u
                   JOIN properties p ON p.id = u.property_id
                   WHERE u.property_id = ? AND p.account_id = ? ORDER BY u.unit_name""",
                (property_id, account_id),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT u.*, p.name as property_name FROM units u
                   JOIN properties p ON p.id = u.property_id
                   WHERE p.account_id = ?
                   ORDER BY p.name, u.unit_name""",
                (account_id,),
            ).fetchall()
        return [dict(r) for r in rows]


def update_unit_status(unit_id, status):
    with get_conn() as conn:
        conn.execute("UPDATE units SET status = ? WHERE id = ?", (status, unit_id))


def update_unit(unit_id, unit_name, monthly_rent, water_rate):
    with get_conn() as conn:
        conn.execute(
            "UPDATE units SET unit_name = ?, monthly_rent = ?, water_rate = ? WHERE id = ?",
            (unit_name, monthly_rent, water_rate, unit_id),
        )


def get_unit(unit_id):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT u.*, p.name as property_name FROM units u
               JOIN properties p ON p.id = u.property_id WHERE u.id = ?""",
            (unit_id,),
        ).fetchone()
        return dict(row) if row else None


def delete_unit(unit_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM units WHERE id = ?", (unit_id,))


# ---------- Tenants ----------

def add_tenant(unit_id, full_name, phone="", email="", id_number="", id_document_path="", move_in_date=None):
    move_in_date = move_in_date or date.today().isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO tenants (unit_id, full_name, phone, email, id_number, id_document_path, move_in_date)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (unit_id, full_name, phone, email, id_number, id_document_path, move_in_date),
        )
        conn.execute("UPDATE units SET status = 'occupied' WHERE id = ?", (unit_id,))
        return cur.lastrowid


def update_tenant_id_document(tenant_id, id_document_path):
    with get_conn() as conn:
        conn.execute("UPDATE tenants SET id_document_path = ? WHERE id = ?", (id_document_path, tenant_id))


def update_tenant(tenant_id, full_name, phone="", email="", id_number="", move_in_date=None):
    """Edit a tenant's own details (not their unit/rent — that's set on the unit)."""
    with get_conn() as conn:
        conn.execute(
            """UPDATE tenants
               SET full_name = ?, phone = ?, email = ?, id_number = ?, move_in_date = ?
               WHERE id = ?""",
            (full_name, phone, email, id_number, move_in_date, tenant_id),
        )


def list_tenants(status=None, account_id=1):
    with get_conn() as conn:
        q = """SELECT t.*, u.unit_name, u.monthly_rent, u.water_rate,
                      p.name as property_name, p.id as property_id
               FROM tenants t
               JOIN units u ON u.id = t.unit_id
               JOIN properties p ON p.id = u.property_id
               WHERE p.account_id = ?"""
        params = [account_id]
        if status:
            q += " AND t.status = ?"
            params.append(status)
        q += " ORDER BY t.full_name"
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def get_tenant(tenant_id):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT t.*, u.unit_name, u.monthly_rent, u.water_rate, p.name as property_name
               FROM tenants t
               JOIN units u ON u.id = t.unit_id
               JOIN properties p ON p.id = u.property_id
               WHERE t.id = ?""",
            (tenant_id,),
        ).fetchone()
        return dict(row) if row else None


def vacate_tenant(tenant_id, move_out_date=None):
    move_out_date = move_out_date or date.today().isoformat()
    with get_conn() as conn:
        tenant = conn.execute("SELECT unit_id FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
        conn.execute(
            "UPDATE tenants SET status = 'vacated', move_out_date = ? WHERE id = ?",
            (move_out_date, tenant_id),
        )
        if tenant:
            conn.execute("UPDATE units SET status = 'vacant' WHERE id = ?", (tenant["unit_id"],))


# ---------- Rent charges (monthly billing) ----------

def generate_charge(tenant_id, period, rent_amount=None, water_amount=None, other_amount=0, note=""):
    """Create (or fetch existing) charge for a tenant for a given 'YYYY-MM' period.
    rent_amount/water_amount default to the tenant's unit rates when not specified."""
    tenant = get_tenant(tenant_id)
    if rent_amount is None:
        rent_amount = tenant["monthly_rent"]
    if water_amount is None:
        water_amount = tenant["water_rate"]
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT * FROM rent_charges WHERE tenant_id = ? AND period = ?", (tenant_id, period)
        ).fetchone()
        if existing:
            return dict(existing)
        cur = conn.execute(
            """INSERT INTO rent_charges (tenant_id, period, rent_amount, water_amount, other_amount, note)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (tenant_id, period, rent_amount, water_amount, other_amount, note),
        )
        return {
            "id": cur.lastrowid, "tenant_id": tenant_id, "period": period,
            "rent_amount": rent_amount, "water_amount": water_amount, "other_amount": other_amount,
        }


def generate_charges_for_all_active(period):
    """Bulk-create this month's rent charge for every active tenant. Skips ones that already exist."""
    created = 0
    for t in list_tenants(status="active"):
        with get_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM rent_charges WHERE tenant_id = ? AND period = ?", (t["id"], period)
            ).fetchone()
        if not existing:
            generate_charge(t["id"], period, rent_amount=t["monthly_rent"], water_amount=t["water_rate"])
            created += 1
    return created


def list_charges(tenant_id=None, period=None):
    with get_conn() as conn:
        q = "SELECT * FROM rent_charges WHERE 1=1"
        params = []
        if tenant_id:
            q += " AND tenant_id = ?"
            params.append(tenant_id)
        if period:
            q += " AND period = ?"
            params.append(period)
        q += " ORDER BY period DESC"
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


# ---------- Payments ----------

def record_payment(tenant_id, amount, payment_date=None, method="cash", momo_reference="",
                    momo_provider="", payment_type="rent", charge_id=None, note=""):
    payment_date = payment_date or date.today().isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO payments
               (tenant_id, charge_id, amount, payment_date, method, momo_reference, momo_provider, payment_type, note)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (tenant_id, charge_id, amount, payment_date, method, momo_reference, momo_provider, payment_type, note),
        )
        return cur.lastrowid


def list_payments(tenant_id=None, limit=None):
    with get_conn() as conn:
        q = """SELECT pay.*, t.full_name, u.unit_name, p.name as property_name
               FROM payments pay
               JOIN tenants t ON t.id = pay.tenant_id
               JOIN units u ON u.id = t.unit_id
               JOIN properties p ON p.id = u.property_id
               WHERE 1=1"""
        params = []
        if tenant_id:
            q += " AND pay.tenant_id = ?"
            params.append(tenant_id)
        q += " ORDER BY pay.payment_date DESC, pay.id DESC"
        if limit:
            q += " LIMIT ?"
            params.append(limit)
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def get_payment(payment_id):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT pay.*, t.full_name, t.phone, u.unit_name, p.name as property_name
               FROM payments pay
               JOIN tenants t ON t.id = pay.tenant_id
               JOIN units u ON u.id = t.unit_id
               JOIN properties p ON p.id = u.property_id
               WHERE pay.id = ?""",
            (payment_id,),
        ).fetchone()
        return dict(row) if row else None


# ---------- Deposits & advance rent ----------

def add_deposit(tenant_id, amount, date_received=None, note=""):
    date_received = date_received or date.today().isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO deposits (tenant_id, amount, date_received, note) VALUES (?, ?, ?, ?)",
            (tenant_id, amount, date_received, note),
        )
        return cur.lastrowid


def list_deposits(tenant_id=None):
    with get_conn() as conn:
        q = """SELECT d.*, t.full_name FROM deposits d JOIN tenants t ON t.id = d.tenant_id WHERE 1=1"""
        params = []
        if tenant_id:
            q += " AND d.tenant_id = ?"
            params.append(tenant_id)
        q += " ORDER BY d.date_received DESC"
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def add_advance_rent(tenant_id, amount, months_covered=1, date_received=None, note=""):
    date_received = date_received or date.today().isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO advance_rent (tenant_id, amount, months_covered, date_received, note)
               VALUES (?, ?, ?, ?, ?)""",
            (tenant_id, amount, months_covered, date_received, note),
        )
        return cur.lastrowid


def list_advance_rent(tenant_id=None):
    with get_conn() as conn:
        q = """SELECT a.*, t.full_name FROM advance_rent a JOIN tenants t ON t.id = a.tenant_id WHERE 1=1"""
        params = []
        if tenant_id:
            q += " AND a.tenant_id = ?"
            params.append(tenant_id)
        q += " ORDER BY a.date_received DESC"
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


# ---------- Balance calculation ----------

def tenant_balance(tenant_id):
    """
    Balance = sum of all rent-related charges (rent_charges) minus sum of all
    payments of type rent/water/other applied. Positive = tenant owes money.
    Advance rent and deposits are tracked separately and not netted into this
    balance automatically (they're credits held for future/other purposes).
    """
    charges = list_charges(tenant_id=tenant_id)
    total_charged = sum(c["rent_amount"] + c["water_amount"] + c["other_amount"] for c in charges)

    with get_conn() as conn:
        row = conn.execute(
            """SELECT COALESCE(SUM(amount), 0) as total FROM payments
               WHERE tenant_id = ? AND payment_type IN ('rent', 'water', 'other')""",
            (tenant_id,),
        ).fetchone()
    total_paid = row["total"]

    balance = round(total_charged - total_paid, 2)
    return {
        "total_charged": round(total_charged, 2),
        "total_paid": round(total_paid, 2),
        "balance": balance,  # positive = owes, negative = credit
        "balance_status": "owing" if balance > 0 else ("credit" if balance < 0 else "settled"),
    }


def all_tenant_balances(account_id=1):
    results = []
    for t in list_tenants(account_id=account_id):
        bal = tenant_balance(t["id"])
        results.append({**t, **bal})
    return results


def portfolio_summary(account_id=1):
    """High-level numbers for the dashboard."""
    with get_conn() as conn:
        total_units = conn.execute(
            """SELECT COUNT(*) c FROM units u
               JOIN properties p ON p.id = u.property_id
               WHERE p.account_id = ?""", (account_id,)
        ).fetchone()["c"]
        occupied = conn.execute(
            """SELECT COUNT(*) c FROM units u
               JOIN properties p ON p.id = u.property_id
               WHERE p.account_id = ? AND u.status = 'occupied'""", (account_id,)
        ).fetchone()["c"]
        this_month = date.today().strftime("%Y-%m")
        collected_this_month = conn.execute(
            """SELECT COALESCE(SUM(pay.amount),0) t FROM payments pay
               JOIN tenants t ON t.id = pay.tenant_id
               JOIN units u ON u.id = t.unit_id
               JOIN properties p ON p.id = u.property_id
               WHERE p.account_id = ? AND pay.payment_date LIKE ?""",
            (account_id, f"{this_month}%"),
        ).fetchone()["t"]

    tenant_rows = list_tenants(status="active", account_id=account_id)
    total_owed = 0
    total_credit = 0
    for t in tenant_rows:
        b = tenant_balance(t["id"])
        if b["balance"] > 0:
            total_owed += b["balance"]
        elif b["balance"] < 0:
            total_credit += -b["balance"]

    return {
        "total_units": total_units,
        "occupied_units": occupied,
        "vacant_units": total_units - occupied,
        "active_tenants": len(tenant_rows),
        "collected_this_month": round(collected_this_month, 2),
        "total_outstanding": round(total_owed, 2),
        "total_credit": round(total_credit, 2),
    }


def current_period():
    return date.today().strftime("%Y-%m")


def period_label(period_str):
    """'2026-08' -> 'August 2026'"""
    try:
        d = datetime.strptime(period_str, "%Y-%m")
        return d.strftime("%B %Y")
    except ValueError:
        return period_str
