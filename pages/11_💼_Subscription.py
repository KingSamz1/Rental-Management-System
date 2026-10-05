import streamlit as st
from utils.db import init_db, get_account, list_all_accounts
from utils.auth import check_login, logout_button, get_current_account_id
from utils.i18n import t
from utils.subscription import (
    get_subscription, redeem_renewal_code, subscription_payment_history,
    generate_renewal_code, list_renewal_codes,
)
from utils.theme import apply_theme, page_header, section_label, subscription_banner, colors

st.set_page_config(page_title="Subscription", page_icon="💼", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()
account_id = get_current_account_id()
account = get_account(account_id) or {}
username = account.get("username", "")
c = colors()

page_header(t("Subscription"), icon="💼")
st.write("")

sub = get_subscription(account_id)
if not sub:
    st.warning(t("No subscription found. Contact support."))
    st.stop()

status       = sub.get("status", "TRIAL")
trial_end    = sub.get("trial_end", "")
next_payment = sub.get("next_payment_date", "")
monthly_fee  = sub.get("monthly_fee", 30000)
currency     = account.get("currency", "UGX")

tone_map  = {"ACTIVE": "accent", "TRIAL": "neutral", "EXPIRED": "danger", "GRACE": "danger"}
color_map = {"accent": c["ACCENT_DARK"], "neutral": c["TEXT_MUTED"], "danger": "#e05"}
banner_color = color_map.get(tone_map.get(status, "neutral"), c["TEXT_MUTED"])

st.markdown(
    f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
    f'border-radius:14px; padding:1.1rem 1.4rem; margin-bottom:1rem;">'
    f'<p style="margin:0 0 4px; font-size:12px; color:{c["TEXT_MUTED"]}; text-transform:uppercase; letter-spacing:.05em;">{t("Subscription status")}</p>'
    f'<p style="margin:0; font-size:22px; font-weight:700; color:{banner_color};">{t(status)}</p>'
    + (f'<p style="margin:4px 0 0; font-size:13px; color:{c["TEXT_MUTED"]};">{t("Trial ends")}: {trial_end}</p>' if trial_end else "")
    + (f'<p style="margin:4px 0 0; font-size:13px; color:{c["TEXT_MUTED"]};">{t("Next payment")}: {next_payment}</p>' if next_payment else "")
    + f'<p style="margin:6px 0 0; font-size:13px; color:{c["TEXT_MUTED"]};">{t("Monthly fee")}: {currency} {monthly_fee:,.0f}</p>'
    f'</div>',
    unsafe_allow_html=True,
)

section_label(t("Redeem a renewal code"))
st.caption(t("Enter a code provided by LandlordPro support to extend your subscription."))
with st.form("redeem_code_form", clear_on_submit=True):
    code = st.text_input(t("Renewal code"), placeholder="e.g. ABC12345", max_chars=12)
    submitted = st.form_submit_button(t("Redeem code"), type="primary")
    if submitted:
        if not code.strip():
            st.error(t("Please enter a code."))
        else:
            try:
                months = redeem_renewal_code(account_id, code.strip().upper())
                st.success(f"✅ {t('Code redeemed!')} {months} {t('month(s) added to your subscription.')}")
                st.rerun()
            except ValueError as e:
                st.error(str(e))

st.divider()
section_label(t("Payment history"))
payments = subscription_payment_history(account_id)
if not payments:
    st.info(t("No subscription payments recorded yet."))
else:
    import pandas as pd
    df = pd.DataFrame([{
        t("Date"):      p["payment_date"],
        t("Amount"):    f"{currency} {p['amount']:,.0f}",
        t("Method"):    p.get("payment_method") or "—",
        t("Reference"): p.get("transaction_reference") or "—",
    } for p in payments])
    st.dataframe(df, use_container_width=True, hide_index=True)

ADMIN_USERNAME = "samzinov"
if username.lower() == ADMIN_USERNAME.lower():
    st.divider()
    section_label(t("Admin — Generate renewal codes"))
    with st.form("gen_code_form", clear_on_submit=True):
        months = st.number_input(t("Months"), min_value=1, max_value=24, value=1)
        gen = st.form_submit_button(t("Generate code"))
        if gen:
            try:
                code = generate_renewal_code(account_id, months)
                st.success(f"{t('Code generated')}: **{code}** — {months} {t('month(s)')}")
            except Exception as e:
                st.error(str(e))

    section_label(t("Admin — All renewal codes"))
    codes = list_renewal_codes(account_id)
    if codes:
        import pandas as pd
        df2 = pd.DataFrame([{
            t("Code"):    c["code"],
            t("Months"):  c["months"],
            t("Used"):    "✅" if c.get("used_at") else "⏳",
            t("Used at"): c.get("used_at") or "—",
        } for c in codes])
        st.dataframe(df2, use_container_width=True, hide_index=True)
