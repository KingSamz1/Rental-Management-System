import streamlit as st
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.theme import apply_theme, page_header, section_label, empty_state, metric_row
from utils.subscription import (
    MONTHLY_FEE, GRACE_DAYS,
    create_subscription, get_subscription, update_subscription_status,
    days_remaining, renew_subscription, subscription_payment_history,
    fast_forward, force_expire,
)

st.set_page_config(page_title="Subscription", page_icon="💼", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()
currency = (get_account(account_id) or {}).get("currency", "UGX")

page_header("LandlordPro Subscription", subtitle="Your Property. Your Tenants. Under Control.", icon="💼")
st.write("")

sub = update_subscription_status(account_id)

# ---------- Existing subscription ----------
status = sub["status"]
days = days_remaining(account_id)

if status == "TRIAL":
    if sub.get("past_due"):
        st.warning(f"⏳ Trial ended — {sub['grace_days_left']} day(s) left before the account locks")
    elif days <= 2:
        st.info(f"⏰ Free trial — {days} day(s) remaining, renew soon to avoid interruption")
    else:
        st.success(f"🎁 Free trial — {days} day(s) remaining")
elif status == "ACTIVE":
    if sub.get("past_due"):
        st.warning(f"⏳ Payment overdue — {sub['grace_days_left']} day(s) left before the account locks")
    elif days <= 2:
        st.info(f"⏰ Active — {days} day(s) remaining, renew soon to avoid interruption")
    else:
        st.success(f"🟢 Active — {days} day(s) remaining")
else:
    st.error("🔴 Subscription expired")
    st.warning("Your property, tenant, and payment data is safe. Renew below to restore full access.")

st.markdown(f"### {sub['landlord_name']}")

due_label = "Trial ends" if status == "TRIAL" else ("Next payment" if status == "ACTIVE" else "Status")
due_value = sub["trial_end"] if status == "TRIAL" else (sub["next_payment_date"] if status == "ACTIVE" else "Expired")

metric_row([
    {"label": "Status", "value": status, "tone": "accent" if status != "EXPIRED" else "danger"},
    {"label": "Days remaining", "value": str(days), "tone": "neutral"},
    {"label": "Monthly fee", "value": f"{currency} {MONTHLY_FEE:,.0f}", "tone": "neutral"},
    {"label": due_label, "value": due_value, "tone": "neutral"},
])

st.divider()
section_label("Renew subscription")
st.write(f"**{currency} {MONTHLY_FEE:,.0f}** / month")

with st.form("renew_form"):
    payment_method = st.selectbox("Payment method", ["MTN Mobile Money", "Airtel Money", "Bank", "Cash", "Other"])
    payment_reference = st.text_input("Transaction reference*")
    note = st.text_area("Note (optional)")
    submitted = st.form_submit_button(f"Renew for {currency} {MONTHLY_FEE:,.0f}", type="primary")
    if submitted:
        try:
            renewed = renew_subscription(account_id, payment_reference, payment_method, note)
            st.success(f"Subscription renewed. Next payment due {renewed['next_payment_date']}.")
            st.rerun()
        except ValueError as e:
            st.error(str(e))

st.divider()
section_label("Payment history")
history = subscription_payment_history(account_id)
if not history:
    empty_state("No subscription payments recorded yet.", icon="💼")
else:
    for p in history:
        with st.expander(f"{p['payment_date']} — {currency} {p['amount']:,.0f}"):
            st.write(f"**Method:** {p['payment_method']}")
            st.write(f"**Reference:** {p['transaction_reference']}")
            st.write(f"**Period:** {p['period_start']} → {p['period_end']}")
            if p["note"]:
                st.write(f"**Note:** {p['note']}")

st.divider()
with st.expander("🛠️ Developer / testing tools"):
    st.caption(
        f"Fast-forward your trial/billing date to test expiry behavior. "
        f"There's a {GRACE_DAYS}-day grace window after the due date before the account locks."
    )
    col_a, col_b = st.columns(2)
    with col_a:
        days_to_skip = st.number_input("Days to fast-forward", min_value=1, max_value=365, value=7, step=1)
        if st.button("Fast-forward subscription"):
            fast_forward(account_id, int(days_to_skip))
            st.rerun()
    with col_b:
        st.write("")
        st.write("")
        if st.button("Force expire now", type="secondary"):
            force_expire(account_id)
            st.rerun()
