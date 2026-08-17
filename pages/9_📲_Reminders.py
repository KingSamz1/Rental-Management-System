import streamlit as st
from utils.db import init_db, get_setting
from utils.auth import check_login, logout_button
from utils.logic import list_tenants, tenant_balance, current_period, period_label
from utils.whatsapp import build_reminder_message, prepare_and_log_reminder, list_reminders, whatsapp_click_to_chat_link
from utils.theme import apply_theme, page_header, empty_state

st.set_page_config(page_title="Reminders", page_icon="📲", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

currency = get_setting("currency", "UGX")

page_header("WhatsApp Rent Reminders", icon="📲")
st.write("")

st.info(
    "No WhatsApp Business API is connected yet, so reminders are **prepared**, not auto-sent. "
    "Each reminder below gets a ready-made message and a click-to-chat link that opens WhatsApp "
    "with the text pre-filled, so you can send manually today. When you're ready to automate "
    "sending, wire `utils/whatsapp.py:send_via_provider()` to the WhatsApp Business Cloud API "
    "(or Twilio/another aggregator) — the message preparation and logging already work as-is."
)

period = st.text_input("Reminder period (YYYY-MM)", value=current_period())

tenants_active = list_tenants(status="active")
owing_tenants = []
for t in tenants_active:
    bal = tenant_balance(t["id"])
    if bal["balance"] > 0:
        owing_tenants.append({**t, **bal})

st.subheader(f"Tenants with outstanding balance — {period_label(period)}")

if not owing_tenants:
    st.success("No active tenants currently owe a balance.")
else:
    for t in owing_tenants:
        with st.expander(f"{t['full_name']} — {currency} {t['balance']:,.0f} owed"):
            message = build_reminder_message(t["id"], period)
            st.text_area("Message preview", value=message, height=100, key=f"msg_{t['id']}", disabled=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Prepare & log reminder", key=f"prep_{t['id']}"):
                    prepare_and_log_reminder(t["id"], period)
                    st.success("Reminder prepared and logged.")
                    st.rerun()
            with col2:
                if t["phone"]:
                    link = whatsapp_click_to_chat_link(t["phone"], message)
                    st.link_button("Open in WhatsApp", link)
                else:
                    st.caption("No phone number on file for this tenant.")

st.divider()
st.subheader("Reminder log")
reminders = list_reminders()
if not reminders:
    empty_state("No reminders prepared yet.", icon="📲")
else:
    import pandas as pd
    df = pd.DataFrame([{
        "Tenant": r["full_name"],
        "Period": r["period"],
        "Channel": r["channel"],
        "Status": r["status"],
        "Prepared at": r["created_at"],
    } for r in reminders])
    st.dataframe(df, use_container_width=True, hide_index=True)
