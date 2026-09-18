"""
Authentication for LandlordPro SA (username + password).
"""
import streamlit as st
from utils.db import get_account_by_username, verify_password, create_account

SUPPORT_WHATSAPP = "https://wa.me/27718726504"
SUPPORT_NUMBER   = "+27 71 872 6504"


def _whatsapp_footer(c):
    st.markdown(
        f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
        f'border-radius:14px; padding:1rem 1.25rem; margin-top:0.75rem; text-align:center;">'
        f'<p style="margin:0 0 8px; font-size:13px; color:{c["TEXT_MUTED"]}; font-weight:500;">Need Assistance?</p>'
        f'<a href="{SUPPORT_WHATSAPP}" target="_blank" '
        f'style="display:inline-flex; align-items:center; gap:8px; '
        f'background:#25D366; color:#fff; text-decoration:none; '
        f'font-size:13px; font-weight:600; padding:8px 18px; border-radius:9px;">'
        f'Chat on WhatsApp \u00b7 {SUPPORT_NUMBER}'
        f'</a></div>',
        unsafe_allow_html=True,
    )


def _brand_header(c, subtitle="Sign in to manage your properties"):
    st.markdown(
        f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
        f'border-radius:18px; padding:1.5rem 1.75rem 1rem; margin-bottom:0.75rem;">'
        f'<div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">'
        f'<div style="width:36px; height:36px; border-radius:10px; background:{c["ACCENT_SOFT"]}; '
        f'display:flex; align-items:center; justify-content:center; font-size:18px;">\U0001f3e0</div>'
        f'<span style="font-size:18px; font-weight:650; color:{c["BRAND_TEXT"]};">LandlordPro SA</span>'
        f'</div>'
        f'<p style="color:{c["TEXT_MUTED"]}; margin:0; font-size:13px;">{subtitle}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _app_summary(c):
    features = [
        ("\U0001f3e2", "Properties & units",     "Add buildings and individual units in seconds."),
        ("\U0001f464", "Tenant management",       "Store contacts, move-in dates, and documents."),
        ("\U0001f4b0", "Rent & utilities",        "Charge rent or utilities per tenant each month."),
        ("\U0001f4b3", "Payments & receipts",     "Record EFT or cash payments, auto-generate PDF receipts."),
        ("\U0001f510", "Deposits & advance rent", "Track security deposits and prepaid months separately."),
        ("\U0001f4f2", "WhatsApp reminders",      "One-tap reminder links sent straight to tenants."),
        ("\U0001f4ca", "Reports",                 "Monthly income, outstanding balances, and tenant history."),
    ]
    items_html = "".join(
        f'<div style="display:flex; align-items:flex-start; gap:10px; padding:7px 0; border-bottom:1px solid {c["BORDER"]};">'
        f'<span style="font-size:16px; line-height:1.4;">{icon}</span>'
        f'<div><span style="font-size:13px; font-weight:600; color:{c["BRAND_TEXT"]};">{title}</span>'
        f'<span style="font-size:12px; color:{c["TEXT_MUTED"]};">\u00a0\u2014 {desc}</span></div></div>'
        for icon, title, desc in features
    )
    st.markdown(
        f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
        f'border-radius:14px; padding:1rem 1.25rem; margin-top:0.75rem;">'
        f'<p style="margin:0 0 10px; font-size:13px; font-weight:700; color:{c["BRAND_TEXT"]}; '
        f'letter-spacing:0.02em; text-transform:uppercase;">What LandlordPro SA does</p>'
        f'<p style="margin:0 0 10px; font-size:13px; color:{c["TEXT_MUTED"]}; line-height:1.55;">'
        f'A simple, all-in-one tool built for landlords in South Africa (and anywhere else). '
        f'Manage every property, tenant, and payment from one place \u2014 no spreadsheets, no paper.</p>'
        f'{items_html}'
        f'<p style="margin:10px 0 0; font-size:12px; color:{c["TEXT_MUTED"]}; font-style:italic;">'
        f'First month free \u00b7 No setup fee \u00b7 Works on any device</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def check_login():
    if st.session_state.get("authenticated"):
        return True

    if st.query_params.get("page") == "signup":
        _show_signup_page()
        st.stop()

    from utils.theme import apply_theme, colors
    apply_theme()
    c = colors()

    st.markdown('<div style="max-width:420px; margin: 2.5rem auto 0;">', unsafe_allow_html=True)
    _brand_header(c, subtitle="Sign in to manage your properties")

    with st.form("login_form"):
        username  = st.text_input("Username", placeholder="your username")
        password  = st.text_input("Password", type="password", placeholder="\u00b7\u00b7\u00b7\u00b7\u00b7\u00b7\u00b7\u00b7")
        submitted = st.form_submit_button("Log in", type="primary", use_container_width=True)

    st.markdown(
        f'<p style="text-align:center; font-size:13px; color:{c["TEXT_MUTED"]}; margin-top:0.5rem;">'
        f'No account? <a href="?page=signup" target="_self" style="color:{c["ACCENT"]}; font-weight:600;">Create one \u2192</a></p>',
        unsafe_allow_html=True,
    )
    _app_summary(c)
    _whatsapp_footer(c)
    st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        account = get_account_by_username(username.strip())
        if account and verify_password(password, account["password_hash"]):
            st.session_state["authenticated"] = True
            st.session_state["account_id"]    = account["id"]
            st.session_state["username"]      = account["username"]
            st.rerun()
        else:
            st.error("Invalid username or password.")

    st.stop()


def _show_signup_page():
    from utils.theme import apply_theme, colors
    apply_theme()
    c = colors()

    _DIAL_CODES = [
        ("\U0001f1ff\U0001f1e6 ZA  +27",  "+27"),  ("\U0001f1f3\U0001f1ff NA  +264", "+264"),
        ("\U0001f1ff\U0001f1fc ZW  +263", "+263"), ("\U0001f1ff\U0001f1f2 ZM  +260", "+260"),
        ("\U0001f1f2\U0001f1fc MW  +265", "+265"), ("\U0001f1f2\U0001f1ff MZ  +258", "+258"),
        ("\U0001f1e7\U0001f1fc BW  +267", "+267"), ("\U0001f1f8\U0001f1ff SZ  +268", "+268"),
        ("\U0001f1f1\U0001f1f8 LS  +266", "+266"), ("\U0001f1ec\U0001f1e7 GB  +44",  "+44"),
        ("\U0001f1fa\U0001f1f8 US  +1",   "+1"),   ("Other", ""),
    ]
    _CURRENCIES = [
        ("\U0001f1ff\U0001f1e6 ZAR \u2014 South African Rand",  "ZAR"),
        ("\U0001f1f3\U0001f1ff NAD \u2014 Namibian Dollar",     "NAD"),
        ("\U0001f1ff\U0001f1fc ZWL \u2014 Zimbabwean Dollar",   "ZWL"),
        ("\U0001f1ff\U0001f1f2 ZMW \u2014 Zambian Kwacha",      "ZMW"),
        ("\U0001f1f2\U0001f1fc MWK \u2014 Malawian Kwacha",     "MWK"),
        ("\U0001f1fa\U0001f1f8 USD \u2014 US Dollar",           "USD"),
        ("\U0001f1ec\U0001f1e7 GBP \u2014 British Pound",       "GBP"),
        ("Other (type below)", None),
    ]
    dc_labels = [l for l, _ in _DIAL_CODES]
    dc_values = {l: v for l, v in _DIAL_CODES}
    cu_labels = [l for l, _ in _CURRENCIES]
    cu_values = {l: v for l, v in _CURRENCIES}

    st.markdown('<div style="max-width:420px; margin: 2.5rem auto 0;">', unsafe_allow_html=True)
    _brand_header(c, subtitle="Create your account \u2014 first month free, no setup fee")

    with st.form("signup_form"):
        new_username  = st.text_input("Username *",                placeholder="e.g. johndoe")
        new_password  = st.text_input("Password *",                type="password", placeholder="at least 6 characters")
        confirm_pass  = st.text_input("Confirm password *",        type="password", placeholder="\u00b7\u00b7\u00b7\u00b7\u00b7\u00b7\u00b7\u00b7")
        business_name = st.text_input("Business / landlord name *", placeholder="e.g. Cape Town Rentals")
        st.markdown("**Currency**")
        cu_label = st.selectbox("Currency", cu_labels, index=0, label_visibility="collapsed")
        cu_code  = cu_values[cu_label]
        currency = st.text_input("Enter currency code", value="ZAR") if cu_code is None else cu_code
        st.markdown("**Contact phone (optional)**")
        sc1, sc2 = st.columns([1, 2])
        with sc1:
            s_dial_label  = st.selectbox("Code",   dc_labels, index=0, label_visibility="collapsed")
        with sc2:
            s_phone_local = st.text_input("Number", placeholder="71 872 6504", label_visibility="collapsed")
        phone     = (dc_values[s_dial_label] + s_phone_local.strip()).strip()
        submitted = st.form_submit_button("Create account & start free trial", type="primary", use_container_width=True)

    st.markdown(
        f'<p style="text-align:center; font-size:13px; color:{c["TEXT_MUTED"]}; margin-top:0.5rem;">'
        f'Already have an account? <a href="/" target="_self" style="color:{c["ACCENT"]}; font-weight:600;">\u2190 Back to login</a></p>',
        unsafe_allow_html=True,
    )
    _app_summary(c)
    _whatsapp_footer(c)
    st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        errors = []
        if not new_username.strip():                       errors.append("Username is required.")
        if len(new_password) < 6:                         errors.append("Password must be at least 6 characters.")
        if new_password != confirm_pass:                   errors.append("Passwords don't match.")
        if not business_name.strip():                      errors.append("Business name is required.")
        if get_account_by_username(new_username.strip()):  errors.append("That username is already taken.")
        if errors:
            for e in errors: st.error(e)
        else:
            from utils.subscription import create_subscription
            acct_id = create_account(
                new_username.strip(), new_password,
                business_name.strip(), currency.strip().upper(), phone.strip(),
            )
            create_subscription(acct_id, business_name.strip())
            st.session_state["authenticated"] = True
            st.session_state["account_id"]    = acct_id
            st.session_state["username"]      = new_username.strip()
            st.query_params.clear()
            st.success("Account created! Welcome to LandlordPro SA \U0001f389")
            st.rerun()

    st.stop()


def logout_button():
    from utils.db import get_account
    from utils.theme import colors

    account_id    = get_current_account_id()
    account       = get_account(account_id) or {}
    c             = colors()
    username      = account.get("username", st.session_state.get("username", ""))
    business_name = account.get("business_name", "")
    display_name  = business_name or username
    initial       = (display_name[0] if display_name else "?").upper()

    with st.sidebar:
        st.markdown(
            f'<div style="display:flex; align-items:center; gap:10px; padding:10px 0 6px;">'
            f'<div style="width:38px; height:38px; border-radius:50%; '
            f'background:{c["ACCENT"]}; display:flex; align-items:center; '
            f'justify-content:center; font-size:16px; font-weight:700; color:#fff; flex-shrink:0;">{initial}</div>'
            f'<div style="overflow:hidden;">'
            f'<div style="font-size:13px; font-weight:600; color:{c["BRAND_TEXT"]}; '
            f'white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{display_name}</div>'
            f'<div style="font-size:11px; color:{c["TEXT_MUTED"]}; '
            f'white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">@{username}</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="height:1px; background:{c["BORDER"]}; margin:4px 0 8px;"></div>',
            unsafe_allow_html=True,
        )
        if st.button("Log out", use_container_width=True):
            st.session_state.clear()
            st.rerun()


def get_current_account_id() -> int:
    return st.session_state.get("account_id", 1)
