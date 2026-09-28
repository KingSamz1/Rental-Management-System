import streamlit as st
from datetime import date
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.i18n import t
from utils.subscription import (
    get_subscription, redeem_renewal_code, get_subscription_payments,
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

status = sub.get("status", "TRIAL")
trial_end = sub.get("trial_end", "")
next_payment = sub.get("next_payment_date", "")
monthly_fee = sub.get("monthly_fee", 30000)
currency = account.get("currency", "UGX")

# Status banner
tone_map = {"ACTIVE": "accent", "TRIAL": "neutral", "EXPIRED": "danger", "GRACE": "danger"}
tone = tone_map.get(status, "neutral")
color_map = {"accent": c["ACCENT_DARK"], "neutral": c["TEXT_MUTED"], "danger": "#e05"}
banner_color = color_map.get(tone, c["TEXT_MUTED"])

st.markdown(
    f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
    f'border-radius:14px; padding:1.1rem 1.4rem; margin-bottom:1rem;">'
    f'<p style="margin:0 0 4px; font-size:12px; color:{c["TEXT_MUTED"]}; text-transform:uppercase; letter-spacing:.05em;">{t("Subscription status")}</p>'
    f'<p style="margin:0; font-size:22px; font-weight:700; color:{banner_color};">{t(status)}</p>'
    f'{"<p style=margin:4px_0_0;font-size:13px;color:" + c["TEXT_MUTED"] + ";>" + t("Trial ends") + ": " + trial_end + "</p>" if trial_end else ""}'
    f'{"<p style=margin:4px_0_0;font-size:13px;color:" + c["TEXT_MUTED"] + ";>" + t("Next payment") + ": " + next_payment + "</p>" if next_payment else ""}'
    f'<p style="margin:6px 0 0; font-size:13px; color:{c["TEXT_MUTED"]};">{t("Monthly fee")}: {currency} {monthly_fee:,.0f}</p>'
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
payments = get_subscription_payments(sub["id"])
if not payments:
    st.info(t("No subscription payments recorded yet."))
else:
    import pandas as pd
    df = pd.DataFrame([{
        t("Date"):        p["payment_date"],
        t("Amount"):      f"{currency} {p['amount']:,.0f}",
        t("Method"):      p.get("payment_method") or "—",
        t("Reference"):   p.get("transaction_reference") or "—",
        t("Period"):      f"{p.get('period_start','')[:7] if p.get('period_start') else '—'}",
    } for p in payments])
    st.dataframe(df, use_container_width=True, hide_index=True)

# Admin section
ADMIN_USERNAME = "samzinov"
if username.lower() == ADMIN_USERNAME.lower():
    st.divider()
    section_label(t("Admin — Generate renewal codes"))
    from utils.db import list_all_accounts
    all_accounts = list_all_accounts()
    acct_options = {f"{a['username']} — {a['business_name']}": a["id"] for a in all_accounts if a["id"] != account_id}
    if acct_options:
        with st.form("gen_code_form", clear_on_submit=True):
            target_label = st.selectbox(t("Account to generate code for"), list(acct_options.keys()))
            months = st.number_input(t("Months"), min_value=1, max_value=24, value=1)
            gen = st.form_submit_button(t("Generate code"))
            if gen:
                code = generate_renewal_code(account_id, acct_options[target_label], months)
                st.success(f"{t('Code generated')}: **{code}** — {months} {t('month(s)')}")

    section_label(t("Admin — All renewal codes"))
    codes = list_renewal_codes(account_id)
    if codes:
        import pandas as pd
        df2 = pd.DataFrame([{
            t("Code"):       c["code"],
            t("Months"):     c["months"],
            t("For"):        c.get("target_username", "—"),
            t("Used"):       "✅" if c.get("used_at") else "⏳",
            t("Used at"):    c.get("used_at") or "—",
        } for c in codes])
        st.dataframe(df2, use_container_width=True, hide_index=True)
