import streamlit as st
from utils.db import init_db, get_account, update_account_settings, update_account_password, verify_password
from utils.auth import check_login, logout_button, get_current_account_id
from utils.i18n import t, language_selector
from utils.theme import apply_theme, page_header, section_label, subscription_banner

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()
account_id = get_current_account_id()
account = get_account(account_id) or {}

page_header(t("Settings"), icon="⚙️")
subscription_banner()
st.write("")

tab1, tab2, tab3 = st.tabs([t("Business info"), t("Change password"), t("Language")])

with tab1:
    section_label(t("Business information"))
    CURRENCIES = [
        ("🇺🇬 UGX — Ugandan Shilling",    "UGX"),
        ("🇰🇪 KES — Kenyan Shilling",      "KES"),
        ("🇹🇿 TZS — Tanzanian Shilling",   "TZS"),
        ("🇷🇼 RWF — Rwandan Franc",        "RWF"),
        ("🇧🇮 BIF — Burundian Franc",      "BIF"),
        ("🇸🇸 SSP — South Sudanese Pound", "SSP"),
        ("🇨🇩 CDF — Congolese Franc",      "CDF"),
        ("🇳🇬 NGN — Nigerian Naira",       "NGN"),
        ("🇬🇭 GHS — Ghanaian Cedi",        "GHS"),
        ("🇿🇦 ZAR — South African Rand",   "ZAR"),
        ("🇺🇸 USD — US Dollar",            "USD"),
        ("🇬🇧 GBP — British Pound",        "GBP"),
        ("🇪🇺 EUR — Euro",                 "EUR"),
        (t("Other (type below)"),           None),
    ]
    cu_labels = [l for l, _ in CURRENCIES]
    cu_values = {l: v for l, v in CURRENCIES}
    current_currency = account.get("currency", "UGX")
    default_cu_label = next((l for l, v in CURRENCIES if v == current_currency), t("Other (type below)"))
    with st.form("business_settings_form"):
        business_name = st.text_input(t("Business / landlord name"), value=account.get("business_name", ""))
        cu_label = st.selectbox(t("Currency"), cu_labels, index=cu_labels.index(default_cu_label))
        cu_code = cu_values[cu_label]
        if cu_code is None:
            currency = st.text_input(t("Enter currency code"), value=current_currency)
        else:
            currency = cu_code
        business_phone = st.text_input(t("Business phone"), value=account.get("business_phone", ""))
        submitted = st.form_submit_button(t("Save changes"))
        if submitted:
            if not business_name.strip():
                st.error(t("Business name is required."))
            else:
                update_account_settings(account_id, business_name.strip(), currency.strip().upper(), business_phone.strip())
                st.success(t("Settings saved."))
                st.rerun()

with tab2:
    section_label(t("Change password"))
    with st.form("change_password_form"):
        current_pw = st.text_input(t("Current password"), type="password")
        new_pw     = st.text_input(t("New password"), type="password")
        confirm_pw = st.text_input(t("Confirm new password"), type="password")
        submitted  = st.form_submit_button(t("Update password"))
        if submitted:
            if not verify_password(current_pw, account.get("password_hash", "")):
                st.error(t("Current password is incorrect."))
            elif len(new_pw) < 6:
                st.error(t("New password must be at least 6 characters."))
            elif new_pw != confirm_pw:
                st.error(t("Passwords don't match."))
            else:
                update_account_password(account_id, new_pw)
                st.success(t("Password updated successfully."))

with tab3:
    section_label(t("Interface language"))
    st.caption(t("Choose the language for the entire application."))
    language_selector(location="inline")
