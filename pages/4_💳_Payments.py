import streamlit as st
from datetime import date
from utils.db import init_db, get_setting
from utils.auth import check_login, logout_button
from utils.logic import list_tenants, record_payment, list_payments, list_charges
from utils.receipts import generate_receipt, get_receipt_for_payment, REPORTLAB_AVAILABLE
from utils.theme import apply_theme, page_header, empty_state, section_label, subscription_banner, require_active_subscription

st.set_page_config(page_title="Payments", page_icon="💳", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

currency = get_setting("currency", "UGX")

page_header("Payment Recording", icon="💳")
subscription_banner()
if not REPORTLAB_AVAILABLE:
    st.warning(
        "PDF receipts are disabled: the 'reportlab' package isn't installed on this server. "
        "Payments still record normally — run `pip install -r requirements.txt` on the server "
        "and restart the app to enable receipts."
    )
st.write("")

tenants = list_tenants(status="active")

if not tenants:
    empty_state("No active tenants yet. Add tenants first.", icon="👤")
else:
    section_label("Record a payment")
    with st.form("payment_form"):
        tenant_options = {f"{t['full_name']} — {t['property_name']}/{t['unit_name']}": t for t in tenants}
        tenant_label = st.selectbox("Tenant*", list(tenant_options.keys()))
        selected = tenant_options[tenant_label]

        payment_type = st.selectbox("Payment type", ["rent", "water", "deposit", "advance", "other"])
        amount = st.number_input(f"Amount ({currency})*", min_value=0.0, step=10000.0)
        payment_date = st.date_input("Payment date", value=date.today())
        method = st.selectbox("Method", ["cash", "mobile_money", "bank"])

        momo_reference = ""
        momo_provider = ""
        if method == "mobile_money":
            col1, col2 = st.columns(2)
            with col1:
                momo_provider = st.selectbox("Mobile Money provider", ["MTN", "Airtel", "Other"])
            with col2:
                momo_reference = st.text_input("Transaction reference*")

        # Optionally link to a specific outstanding charge
        charges = list_charges(tenant_id=selected["id"])
        charge_options = {"Not linked to a specific period": None}
        for c in charges:
            charge_options[f"{c['period']} (rent {c['rent_amount']:,.0f} + water {c['water_amount']:,.0f})"] = c["id"]
        charge_label = st.selectbox("Link to billing period (optional)", list(charge_options.keys()))

        note = st.text_input("Note (optional)")
        submitted = st.form_submit_button("Record payment", type="primary")

        if submitted:
            if not require_active_subscription():
                pass
            elif amount <= 0:
                st.error("Amount must be greater than zero.")
            elif method == "mobile_money" and not momo_reference.strip():
                st.error("Mobile Money transaction reference is required for Mobile Money payments.")
            else:
                payment_id = record_payment(
                    tenant_id=selected["id"],
                    amount=amount,
                    payment_date=payment_date.isoformat(),
                    method=method,
                    momo_reference=momo_reference.strip(),
                    momo_provider=momo_provider,
                    payment_type=payment_type,
                    charge_id=charge_options[charge_label],
                    note=note.strip(),
                )
                # Build a human-friendly receipt filename: TenantName_Period_ReceiptNo.pdf
                period_for_name = charge_label.split(" ")[0] if charge_options[charge_label] else payment_date.strftime("%Y-%m")
                try:
                    receipt = generate_receipt(payment_id, display_name=f"{selected['full_name']}_{period_for_name}")
                    # Stash in session_state so the download button can render OUTSIDE the form
                    # (Streamlit forms cannot contain st.download_button).
                    st.session_state["last_receipt"] = receipt
                    st.session_state["last_payment_id"] = payment_id
                    st.success(f"Payment recorded. Receipt {receipt['receipt_number']} generated.")
                except RuntimeError as e:
                    # Payment is already saved at this point — only the PDF failed.
                    st.success("Payment recorded.")
                    st.warning(str(e))
                st.rerun()

    # Rendered outside the form so the download button is allowed here.
    if st.session_state.get("last_receipt"):
        receipt = st.session_state["last_receipt"]
        with open(receipt["file_path"], "rb") as f:
            st.download_button(
                "⬇️ Download receipt PDF", f, file_name=receipt["download_name"],
                mime="application/pdf", key=f"dl_{st.session_state['last_payment_id']}",
            )
        if st.button("Dismiss"):
            del st.session_state["last_receipt"]
            del st.session_state["last_payment_id"]
            st.rerun()

st.divider()
section_label("Payment history")

filter_options = {"All tenants": None}
filter_options.update({f"{t['full_name']} — {t['unit_name']}": t["id"] for t in list_tenants()})
filter_label = st.selectbox("Filter by tenant", list(filter_options.keys()), key="payment_history_filter")
payments = list_payments(tenant_id=filter_options[filter_label])

if not payments:
    empty_state("No payments recorded yet.", icon="💳")
else:
    for p in payments:
        receipt = get_receipt_for_payment(p["id"])
        cols = st.columns([3, 2, 2, 2, 2, 2])
        cols[0].write(f"**{p['full_name']}** — {p['property_name']}/{p['unit_name']}")
        cols[1].write(p["payment_date"])
        cols[2].write(f"{currency} {p['amount']:,.0f}")
        cols[3].write(p["payment_type"].title())
        method_display = p["method"].replace("_", " ").title()
        if p["momo_reference"]:
            method_display += f" ({p['momo_provider']}: {p['momo_reference']})"
        cols[4].write(method_display)
        if receipt:
            with open(receipt["file_path"], "rb") as f:
                cols[5].download_button(
                    "📄 Receipt", f, file_name=receipt.get("download_name") or f"{receipt['receipt_number']}.pdf",
                    mime="application/pdf", key=f"hist_dl_{p['id']}",
                )
