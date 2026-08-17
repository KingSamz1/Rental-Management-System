import streamlit as st
from utils.db import init_db, get_setting
from utils.auth import check_login, logout_button
from utils.theme import apply_theme, page_header, section_label, empty_state, metric_row
from utils.subscription import (
    SETUP_FEE, MONTHLY_FEE, GRACE_DAYS,
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

currency = get_setting("currency", "UGX")

page_header("LandlordPro Subscription", subtitle="Your Property. Your Tenants. Under Control.", icon="💼")
st.write("")

sub = update_subscription_status()

# ---------- No subscription yet: onboarding ----------
if sub is None:
    st.markdown("### Welcome to LandlordPro")
    st.write("Set up your account and get a full month free, starting today.")

    col1, col2 = st.columns(2)
    col1.metric("One-time setup fee", f"{currency} {SETUP_FEE:,.0f}")
    col2.metric("First month", "Free")

    st.divider()
    section_label("Create your account")

    with st.form("create_subscription_form"):
        landlord_name = st.text_input("Landlord / business name*")
        st.caption(f"Collect the one-time setup fee of {currency} {SETUP_FEE:,.0f} before creating the account.")
        payment_method = st.selectbox("Setup payment method", ["MTN Mobile Money", "Airtel Money", "Bank", "Cash", "Other"])
        payment_reference = st.text_input("Setup payment reference*")
        submitted = st.form_submit_button("Create account & start free trial", type="primary")

        if submitted:
            if not landlord_name.strip():
                st.error("Landlord/business name is required.")
            elif not payment_reference.strip():
                st.error("Setup payment reference is required.")
            else:
                create_subscription(landlord_name.strip(), payment_reference, payment_method)
                st.success("Account created. Your free trial month has started.")
                st.balloons()
                st.rerun()

    st.stop()

# ---------- Existing subscription ----------
status = sub["status"]
days = days_remaining()

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
    st.warning(
        "Your property, tenant, and payment data is safe and has not been deleted. "
        "Renew below to restore full access to adding/editing records."
    )

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
    payment_method = st.selectbox("Payment method", ["MTN Mobile Money", "Airtel Money", "Bank", "Cash", "Other"], key="renewal_method")
    payment_reference = st.text_input("Transaction reference*", key="renewal_reference")
    note = st.text_area("Note (optional)", key="renewal_note")
    submitted = st.form_submit_button(f"Renew for {currency} {MONTHLY_FEE:,.0f}", type="primary")

    if submitted:
        try:
            renewed = renew_subscription(payment_reference, payment_method, note)
            st.success(f"Subscription renewed. Next payment due {renewed['next_payment_date']}.")
            st.rerun()
        except ValueError as e:
            st.error(str(e))

st.divider()
section_label("Subscription payment history")
history = subscription_payment_history()
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
        "Only visible to whoever is logged in as the admin. Lets you exercise trial, "
        "grace-period, and expiry behavior without waiting for real time to pass. "
        f"Currently there's a {GRACE_DAYS}-day grace window after a due date before the "
        "account actually locks."
    )
    col_a, col_b = st.columns(2)
    with col_a:
        days_to_skip = st.number_input("Days to fast-forward", min_value=1, max_value=365, value=7, step=1)
        if st.button("Fast-forward subscription"):
            fast_forward(int(days_to_skip))
            st.rerun()
    with col_b:
        st.write("")
        st.write("")
        if st.button("Force expire now", type="secondary"):
            force_expire()
            st.rerun()
