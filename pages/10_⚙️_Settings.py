import streamlit as st
from utils.db import init_db, get_setting, set_setting
from utils.auth import check_login, logout_button
from utils.theme import apply_theme, page_header, section_label

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

page_header("Landlord Settings", icon="⚙️")
st.caption("These values appear on receipts and in reminder messages.")
st.write("")

with st.form("settings_form"):
    business_name = st.text_input("Business / landlord name", value=get_setting("business_name", ""))
    business_phone = st.text_input("Contact phone", value=get_setting("business_phone", ""))
    currency = st.text_input("Currency code (e.g. UGX, KES, USD)", value=get_setting("currency", "UGX"))
    submitted = st.form_submit_button("Save settings", type="primary")
    if submitted:
        set_setting("business_name", business_name.strip())
        set_setting("business_phone", business_phone.strip())
        set_setting("currency", currency.strip().upper())
        st.success("Settings saved.")

st.divider()
section_label("Change login credentials")
st.caption(
    "Login credentials come from `.streamlit/secrets.toml`, not this page. "
    "Edit that file directly and restart the app to change your username/password:"
)
st.code(
    '[auth]\nusername = "your_username"\npassword = "your_new_password"',
    language="toml",
)

st.divider()
section_label("About this system")
st.markdown(
    "This is a working MVP foundation. Before using it commercially with real "
    "landlords/tenants, consider strengthening:\n"
    "- **Authentication**: hashed passwords, multi-user support, session expiry\n"
    "- **Backups**: automatic backups of the SQLite database file\n"
    "- **Audit logs**: who changed what and when\n"
    "- **Deployment security**: HTTPS, environment-based secrets, not committing `secrets.toml`\n"
    "- **WhatsApp**: connecting a real provider in `utils/whatsapp.py`\n"
    "- **Payments**: Mobile Money API integration for automatic reconciliation instead of manual reference entry"
)
