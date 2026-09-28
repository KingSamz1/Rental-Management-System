import streamlit as st
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.i18n import t
from utils.logic import all_tenant_balances, current_period, period_label
from utils.whatsapp import build_reminder_url
from utils.theme import apply_theme, page_header, empty_state, section_label, subscription_banner, require_active_subscription

st.set_page_config(page_title="Reminders", page_icon="📲", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()
account = get_account(account_id) or {}
currency = account.get("currency", "UGX")
business_name = account.get("business_name", "Your Landlord")

page_header(t("WhatsApp Reminders"), icon="📲")
subscription_banner()
st.write("")

period = current_period()
view_period = st.text_input(t("Period (YYYY-MM)"), value=period)

section_label(t("Tenants with outstanding balances"))
balances = all_tenant_balances(account_id=account_id)
owing = [b for b in balances if b["balance"] > 0]

if not owing:
    empty_state(t("No tenants with outstanding balances. 🎉"), icon="✅")
else:
    st.caption(t("Click a WhatsApp button to open a pre-filled reminder message for that tenant."))
    for b in owing:
        with st.expander(f"{b['full_name']} — {currency} {b['balance']:,.0f} {t('owing')}"):
            phone = b.get("phone", "")
            if not phone:
                st.warning(t("No phone number on file for this tenant."))
            else:
                msg = (
                    f"Hello {b['full_name']}, this is a reminder from {business_name}. "
                    f"Your outstanding balance for {period_label(view_period)} is "
                    f"{currency} {b['balance']:,.0f}. "
                    f"Please make payment at your earliest convenience. Thank you."
                )
                wa_url = build_reminder_url(phone, msg)
                st.write(f"**{t('Phone')}:** {phone}")
                st.write(f"**{t('Balance')}:** {currency} {b['balance']:,.0f}")
                st.write(f"**{t('Property')}:** {b['property_name']} / {b['unit_name']}")
                st.markdown(
                    f'<a href="{wa_url}" target="_blank" style="'
                    f'display:inline-block; background:#25D366; color:#fff; '
                    f'padding:8px 18px; border-radius:8px; text-decoration:none; '
                    f'font-weight:600; font-size:13px; margin-top:6px;">'
                    f'📲 {t("Send WhatsApp reminder")}</a>',
                    unsafe_allow_html=True,
                )
