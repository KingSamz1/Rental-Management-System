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

# ── Dial codes reference (same list used across the app) ──────────────────────
DIAL_CODES = [
    # East Africa
    ("🇺🇬 UG  +256", "+256"), ("🇰🇪 KE  +254", "+254"), ("🇹🇿 TZ  +255", "+255"),
    ("🇷🇼 RW  +250", "+250"), ("🇧🇮 BI  +257", "+257"), ("🇸🇸 SS  +211", "+211"),
    ("🇨🇩 CD  +243", "+243"), ("🇸🇴 SO  +252", "+252"), ("🇪🇹 ET  +251", "+251"),
    ("🇸🇩 SD  +249", "+249"), ("🇩🇯 DJ  +253", "+253"), ("🇪🇷 ER  +291", "+291"),
    # West Africa
    ("🇳🇬 NG  +234", "+234"), ("🇬🇭 GH  +233", "+233"), ("🇸🇳 SN  +221", "+221"),
    ("🇨🇮 CI  +225", "+225"), ("🇧🇫 BF  +226", "+226"), ("🇲🇱 ML  +223", "+223"),
    ("🇳🇪 NE  +227", "+227"), ("🇹🇩 TD  +235", "+235"), ("🇧🇯 BJ  +229", "+229"),
    ("🇹🇬 TG  +228", "+228"), ("🇬🇳 GN  +224", "+224"), ("🇸🇱 SL  +232", "+232"),
    ("🇱🇷 LR  +231", "+231"), ("🇬🇲 GM  +220", "+220"), ("🇨🇲 CM  +237", "+237"),
    # Southern & Central Africa
    ("🇿🇦 ZA  +27",  "+27"),  ("🇿🇼 ZW  +263", "+263"), ("🇿🇲 ZM  +260", "+260"),
    ("🇲🇿 MZ  +258", "+258"), ("🇲🇼 MW  +265", "+265"), ("🇧🇼 BW  +267", "+267"),
    ("🇳🇦 NA  +264", "+264"), ("🇦🇴 AO  +244", "+244"), ("🇸🇿 SZ  +268", "+268"),
    ("🇱🇸 LS  +266", "+266"),
    # North Africa
    ("🇪🇬 EG  +20",  "+20"),  ("🇱🇾 LY  +218", "+218"), ("🇹🇳 TN  +216", "+216"),
    ("🇩🇿 DZ  +213", "+213"), ("🇲🇦 MA  +212", "+212"),
    # Indian Ocean
    ("🇲🇬 MG  +261", "+261"), ("🇲🇺 MU  +230", "+230"), ("🇸🇨 SC  +248", "+248"),
    # Europe
    ("🇬🇧 GB  +44",  "+44"),  ("🇩🇪 DE  +49",  "+49"),  ("🇫🇷 FR  +33",  "+33"),
    ("🇮🇹 IT  +39",  "+39"),  ("🇪🇸 ES  +34",  "+34"),  ("🇳🇱 NL  +31",  "+31"),
    ("🇵🇹 PT  +351", "+351"), ("🇸🇪 SE  +46",  "+46"),  ("🇳🇴 NO  +47",  "+47"),
    # Americas
    ("🇺🇸 US  +1",   "+1"),   ("🇨🇦 CA  +1",   "+1"),
    # Middle East & Asia
    ("🇮🇳 IN  +91",  "+91"),  ("🇵🇰 PK  +92",  "+92"),  ("🇧🇩 BD  +880", "+880"),
    ("🇨🇳 CN  +86",  "+86"),  ("🇸🇦 SA  +966", "+966"), ("🇦🇪 AE  +971", "+971"),
    ("🇶🇦 QA  +974", "+974"), ("🇹🇷 TR  +90",  "+90"),
    # Oceania
    ("🇦🇺 AU  +61",  "+61"),  ("🇳🇿 NZ  +64",  "+64"),
    ("Other", ""),
]
code_labels = [label for label, _ in DIAL_CODES]
code_values = {label: code for label, code in DIAL_CODES}

# Common currencies
CURRENCIES = [
    ("🇺🇬 UGX — Ugandan Shilling",     "UGX"),
    ("🇰🇪 KES — Kenyan Shilling",       "KES"),
    ("🇹🇿 TZS — Tanzanian Shilling",    "TZS"),
    ("🇷🇼 RWF — Rwandan Franc",          "RWF"),
    ("🇸🇸 SSP — South Sudanese Pound",  "SSP"),
    ("🇨🇩 CDF — Congolese Franc",        "CDF"),
    ("🇪🇹 ETB — Ethiopian Birr",         "ETB"),
    ("🇳🇬 NGN — Nigerian Naira",         "NGN"),
    ("🇬🇭 GHS — Ghanaian Cedi",          "GHS"),
    ("🇿🇦 ZAR — South African Rand",     "ZAR"),
    ("🇿🇲 ZMW — Zambian Kwacha",         "ZMW"),
    ("🇲🇿 MZN — Mozambican Metical",     "MZN"),
    ("🇲🇼 MWK — Malawian Kwacha",        "MWK"),
    ("🇧🇼 BWP — Botswana Pula",          "BWP"),
    ("🇳🇦 NAD — Namibian Dollar",        "NAD"),
    ("🇪🇬 EGP — Egyptian Pound",         "EGP"),
    ("🇲🇦 MAD — Moroccan Dirham",        "MAD"),
    ("🇹🇳 TND — Tunisian Dinar",         "TND"),
    ("🇸🇦 SAR — Saudi Riyal",            "SAR"),
    ("🇦🇪 AED — UAE Dirham",             "AED"),
    ("🇶🇦 QAR — Qatari Riyal",           "QAR"),
    ("🇬🇧 GBP — British Pound",          "GBP"),
    ("🇪🇺 EUR — Euro",                   "EUR"),
    ("🇺🇸 USD — US Dollar",              "USD"),
    ("🇨🇦 CAD — Canadian Dollar",        "CAD"),
    ("🇦🇺 AUD — Australian Dollar",      "AUD"),
    ("🇮🇳 INR — Indian Rupee",           "INR"),
    ("🇨🇳 CNY — Chinese Yuan",           "CNY"),
    ("Other (type below)", None),
]
currency_labels = [label for label, _ in CURRENCIES]
currency_values = {label: code for label, code in CURRENCIES}

section_label("Business details")
with st.form("settings_form"):
    business_name = st.text_input("Business / landlord name", value=account.get("business_name", ""))

    # ── Phone with country code picker ───────────────────────────────────────
    st.markdown("**Contact phone**")
    existing_phone = account.get("business_phone", "") or ""
    # Detect existing dial code
    default_code_idx = 0
    for idx, (lbl, code) in enumerate(DIAL_CODES):
        if code and existing_phone.startswith(code):
            default_code_idx = idx
            break
    sp1, sp2 = st.columns([1, 2])
    with sp1:
        dial_label = st.selectbox("Country code", code_labels, index=default_code_idx, label_visibility="collapsed")
    with sp2:
        dial_code = code_values[dial_label]
        local_part = existing_phone[len(dial_code):] if dial_code and existing_phone.startswith(dial_code) else existing_phone
        phone_local = st.text_input("Phone number", value=local_part, placeholder="701 234 567", label_visibility="collapsed")
    business_phone = (dial_code + phone_local.strip()).strip()

    # ── Currency picker ───────────────────────────────────────────────────────
    st.markdown("**Currency**")
    current_currency = account.get("currency", "UGX")
    # Find matching label
    default_curr_idx = len(CURRENCIES) - 1  # "Other"
    for idx, (lbl, code) in enumerate(CURRENCIES):
        if code == current_currency:
            default_curr_idx = idx
            break
    curr_label = st.selectbox("Currency", currency_labels, index=default_curr_idx, label_visibility="collapsed")
    selected_currency_code = currency_values[curr_label]
    if selected_currency_code is None:
        currency = st.text_input("Enter currency code", value=current_currency, placeholder="e.g. XOF")
    else:
        currency = selected_currency_code
        st.caption(f"Selected: **{currency}**")

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
