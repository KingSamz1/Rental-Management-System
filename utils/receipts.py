"""
Automatic PDF receipt generation for payments.
"""
import os
import re
from datetime import datetime
from utils.db import get_conn, get_setting

try:
    from reportlab.lib.pagesizes import A5
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    # reportlab isn't installed in this environment. Importing this module
    # (and the page that imports it) should still work — receipt PDFs just
    # aren't generated until `pip install -r requirements.txt` is run.
    REPORTLAB_AVAILABLE = False

RECEIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "receipts")


def _ensure_dir():
    os.makedirs(RECEIPTS_DIR, exist_ok=True)


def _next_receipt_number():
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) c FROM receipts").fetchone()
    seq = row["c"] + 1
    year = datetime.now().strftime("%Y")
    return f"RCT-{year}-{seq:05d}"


def _safe_filename(name):
    """Strip characters that aren't safe in filenames across OSes."""
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = name.strip().replace(" ", "_")
    return name or "receipt"


def generate_receipt(payment_id, display_name=None):
    """Build a PDF receipt for a payment and register it in the receipts table.

    display_name: optional human-friendly base name (without extension) used
    for the downloadable filename, e.g. 'John_Mukasa_2026-08'. The file on
    disk is still stored under its receipt number so it never collides;
    display_name only controls what the user sees when they download it.
    """
    from utils.logic import get_payment  # local import avoids circular import at module load

    if not REPORTLAB_AVAILABLE:
        raise RuntimeError(
            "PDF receipts need the 'reportlab' package, which isn't installed in this "
            "environment. Run `pip install -r requirements.txt` (or `pip install reportlab`) "
            "on the server, then try again."
        )

    _ensure_dir()

    payment = get_payment(payment_id)
    if not payment:
        raise ValueError("Payment not found")

    receipt_number = _next_receipt_number()
    filename = f"{receipt_number}.pdf"
    file_path = os.path.join(RECEIPTS_DIR, filename)

    if display_name:
        download_name = f"{_safe_filename(display_name)}_{receipt_number}.pdf"
    else:
        download_name = filename

    business_name = get_setting("business_name", "Rental Management")
    business_phone = get_setting("business_phone", "")
    currency = get_setting("currency", "ZAR")

    c = canvas.Canvas(file_path, pagesize=A5)
    width, height = A5

    y = height - 20 * mm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(15 * mm, y, business_name)
    y -= 7 * mm

    c.setFont("Helvetica", 9)
    if business_phone:
        c.drawString(15 * mm, y, f"Contact: {business_phone}")
        y -= 6 * mm

    c.setStrokeColor(colors.grey)
    c.line(15 * mm, y, width - 15 * mm, y)
    y -= 10 * mm

    c.setFont("Helvetica-Bold", 13)
    c.drawString(15 * mm, y, "PAYMENT RECEIPT")
    c.setFont("Helvetica", 9)
    c.drawRightString(width - 15 * mm, y, receipt_number)
    y -= 10 * mm

    c.setFont("Helvetica", 10)
    rows = [
        ("Date", payment["payment_date"]),
        ("Tenant", payment["full_name"]),
        ("Property", payment["property_name"]),
        ("Unit", payment["unit_name"]),
        ("Payment type", payment["payment_type"].replace("_", " ").title()),
        ("Method", payment["method"].replace("_", " ").title()),
    ]
    if payment.get("momo_reference"):
        rows.append(("Mobile Money Ref", payment["momo_reference"]))
    if payment.get("momo_provider"):
        rows.append(("Provider", payment["momo_provider"]))

    for label, value in rows:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(15 * mm, y, f"{label}:")
        c.setFont("Helvetica", 10)
        c.drawString(60 * mm, y, str(value))
        y -= 7 * mm

    y -= 5 * mm
    c.setStrokeColor(colors.grey)
    c.line(15 * mm, y, width - 15 * mm, y)
    y -= 10 * mm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(15 * mm, y, "Amount Paid:")
    c.drawRightString(width - 15 * mm, y, f"{currency} {payment['amount']:,.0f}")
    y -= 15 * mm

    if payment.get("note"):
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(15 * mm, y, f"Note: {payment['note']}")
        y -= 10 * mm

    c.setFont("Helvetica", 8)
    c.setFillColor(colors.grey)
    c.drawString(15 * mm, 15 * mm, "Generated automatically by the Rental Management system.")

    c.showPage()
    c.save()

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO receipts (payment_id, receipt_number, file_path, download_name) VALUES (?, ?, ?, ?)",
            (payment_id, receipt_number, file_path, download_name),
        )

    return {"receipt_number": receipt_number, "file_path": file_path, "download_name": download_name}


def get_receipt_for_payment(payment_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM receipts WHERE payment_id = ?", (payment_id,)).fetchone()
        return dict(row) if row else None
