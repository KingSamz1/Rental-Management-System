import streamlit as st
from utils.db import init_db, get_account, update_account_settings, update_account_password, verify_password
from utils.auth import check_login, logout_button, get_current_account_id
from utils.theme import apply_theme, page_header, section_label

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()
account = get_account(account_id) or {}

page_header("Account Settings", icon="⚙️")
st.caption("These values appear on receipts and in reminder messages.")
st.write("")

section_label("Business details")
with st.form("settings_form"):
    business_name = st.text_input("Business / landlord name", value=account.get("business_name", ""))
    business_phone = st.text_input("Contact phone", value=account.get("business_phone", ""))
    currency = st.text_input("Currency code (e.g. UGX, KES, USD)", value=account.get("currency", "UGX"))
    submitted = st.form_submit_button("Save settings", type="primary")
    if submitted:
        update_account_settings(account_id, business_name.strip(), currency.strip().upper(), business_phone.strip())
        st.success("Settings saved.")

st.divider()
section_label("Change password")
with st.form("change_password_form"):
    current_pw = st.text_input("Current password", type="password")
    new_pw = st.text_input("New password", type="password")
    confirm_pw = st.text_input("Confirm new password", type="password")
    pw_submitted = st.form_submit_button("Update password")
    if pw_submitted:
        fresh = get_account(account_id)
        if not verify_password(current_pw, fresh["password_hash"]):
            st.error("Current password is incorrect.")
        elif len(new_pw) < 6:
            st.error("New password must be at least 6 characters.")
        elif new_pw != confirm_pw:
            st.error("Passwords don't match.")
        else:
            update_account_password(account_id, new_pw)
            st.success("Password updated.")
