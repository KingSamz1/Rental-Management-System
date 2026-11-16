"""
Authentication for GuesthousePro (username + password).
Includes language selector, forgot password, and t() translations.
"""
import urllib.parse
import streamlit as st
from utils.db import get_account_by_username, verify_password, create_account
from utils.currency import format_converted, rate_note, MONTHLY_FEE_UGX
from utils.i18n import t, language_selector, get_language

SUPPORT_WHATSAPP = "https://wa.me/256793839816"
SUPPORT_NUMBER   = "+256 793 839 816"


def _whatsapp_footer(c):
    st.markdown(
        f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
        f'border-radius:14px; padding:1rem 1.25rem; margin-top:0.75rem; text-align:center;">'
        f'<p style="margin:0 0 8px; font-size:13px; color:{c["TEXT_MUTED"]}; font-weight:500;">{t("Need Help?")}</p>'
        f'<a href="{SUPPORT_WHATSAPP}" target="_blank" '
        f'style="display:inline-flex; align-items:center; gap:8px; '
        f'background:#25D366; color:#fff; text-decoration:none; '
        f'font-size:13px; font-weight:600; padding:8px 18px; border-radius:9px;">'
        f'{t("Chat on WhatsApp")} \u00b7 {SUPPORT_NUMBER}'
        f'</a></div>',
        unsafe_allow_html=True,
    )


def _brand_header(c, subtitle="Sign in to manage your property"):
    st.markdown(
        f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
        f'border-radius:18px; padding:1.5rem 1.75rem 1rem; margin-bottom:0.75rem;">'
        f'<div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">'
        f'<div style="width:36px; height:36px; border-radius:10px; background:{c["ACCENT_SOFT"]}; '
        f'display:flex; align-items:center; justify-content:center; font-size:18px;">\U0001f3e8</div>'
        f'<span style="font-size:18px; font-weight:650; color:{c["BRAND_TEXT"]};">GuesthousePro</span>'
        f'</div>'
        f'<p style="color:{c["TEXT_MUTED"]}; margin:0; font-size:13px;">{t(subtitle)}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _app_summary(c, currency="UGX"):
    features = [
        ("\U0001f3e2", t("Units & Rooms"),          t("Manage all your apartments with live status.")),
        ("\U0001f4c5", t("Reservations & Calendar"), t("Visual booking grid, check-in/check-out.")),
        ("\U0001f464", t("Guest Profiles"),          t("Store contacts, IDs, and stay history.")),
        ("\U0001f4b0", t("Billing & Payments"),      t("Guest bill, extra charges, MoMo, cash, bank.")),
        ("\U0001f9f9", t("Housekeeping"),            t("Room status board — dirty, cleaning, ready.")),
        ("\U0001f527", t("Maintenance"),             t("Log issues, assign staff, block bookings.")),
        ("\U0001f4ca", t("Reports"),                 t("Monthly income, outstanding balances, and tenant history.")),
    ]
    items_html = "".join(
        f'<div style="display:flex; align-items:flex-start; gap:10px; padding:7px 0; border-bottom:1px solid {c["BORDER"]};">'
        f'<span style="font-size:16px; line-height:1.4;">{icon}</span>'
        f'<div><span style="font-size:13px; font-weight:600; color:{c["BRAND_TEXT"]};">{title}</span>'
        f'<span style="font-size:12px; color:{c["TEXT_MUTED"]};">\u00a0\u2014 {desc}</span></div></div>'
        for icon, title, desc in features
    )
    fee_str = format_converted(MONTHLY_FEE_UGX, currency)
    _rnote  = rate_note(currency)
    pricing_note = (
        f'{t("First month free")} \u00b7 {t("then")} <strong>{fee_str}/month</strong>'
        + (f' <em>({_rnote})</em>' if _rnote else "")
        + f' \u00b7 {t("No setup fee")} \u00b7 {t("Works on any device")}'
    )
    st.markdown(
        f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
        f'border-radius:14px; padding:1rem 1.25rem; margin-top:0.75rem;">'
        f'<p style="margin:0 0 10px; font-size:13px; font-weight:700; color:{c["BRAND_TEXT"]}; '
        f'letter-spacing:0.02em; text-transform:uppercase;">{t("What GuesthousePro does")}</p>'
        f'<p style="margin:0 0 10px; font-size:13px; color:{c["TEXT_MUTED"]}; line-height:1.55;">'
        f'{t("A smart, all-in-one Property Management System built for guesthouses and serviced apartments in Africa. Reservations, housekeeping, billing — all in one place.")}</p>'
        f'{items_html}'
        f'<p style="margin:10px 0 0; font-size:12px; color:{c["TEXT_MUTED"]};">'
        f'{pricing_note}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def check_login():
    if st.session_state.get("authenticated"):
        return True

    page = st.query_params.get("page", "")

    if page == "signup":
        _show_signup_page()
        st.stop()

    if page == "forgot":
        _show_forgot_page(username_hint=st.query_params.get("username", ""))
        st.stop()

    from utils.theme import apply_theme, colors
    apply_theme()
    c = colors()

    st.markdown('<div style="max-width:420px; margin: 2.5rem auto 0;">', unsafe_allow_html=True)

    language_selector(location="inline")
    _brand_header(c, subtitle="Sign in to manage your property")

    with st.form("login_form"):
        username  = st.text_input(t("Username"), placeholder=t("your username"))
        password  = st.text_input(t("Password"), type="password", placeholder="\u00b7\u00b7\u00b7\u00b7\u00b7\u00b7\u00b7\u00b7")
        submitted = st.form_submit_button(t("Log in"), type="primary", use_container_width=True)

    _forgot_user = st.session_state.get("_login_username_hint", "")
    _lang_param = get_language()
    _forgot_url = f"?page=forgot&lang={_lang_param}" + (f"&username={urllib.parse.quote(_forgot_user)}" if _forgot_user else "")
    st.markdown(
        f'<div style="display:flex; justify-content:space-between; align-items:center; '
        f'font-size:13px; color:{c["TEXT_MUTED"]}; margin-top:0.4rem; margin-bottom:0.2rem;">'
        f'<span>{t("No account?")} <a href="?page=signup&lang={get_language()}" target="_self" style="color:{c["ACCENT"]}; font-weight:600;">{t("Create one")} \u2192</a></span>'
        f'<a href="{_forgot_url}" target="_self" style="color:{c["TEXT_MUTED"]}; text-decoration:underline; font-size:12px;">{t("Forgot password?")}</a>'
        f'</div>',
        unsafe_allow_html=True,
    )

    error_slot = st.empty()
    _app_summary(c, currency="UGX")
    _whatsapp_footer(c)
    st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        st.session_state["_login_username_hint"] = username.strip()
        account = get_account_by_username(username.strip())
        if account and verify_password(password, account["password_hash"]):
            st.session_state["authenticated"] = True
            st.session_state["account_id"]    = account["id"]
            st.session_state["username"]      = account["username"]
            st.rerun()
        else:
            error_slot.error(t("Invalid username or password."))

    st.stop()


def _show_forgot_page(username_hint=""):
    _lang = st.query_params.get("lang", "en")
    if _lang != "en":
        st.session_state["app_lang"] = _lang
        
    from utils.subscription import redeem_password_reset_code
    from utils.db import update_account_password, get_account_by_username
    from utils.theme import apply_theme, colors
    apply_theme()
    c = colors()

    step = st.session_state.get("forgot_step", 1)

    st.markdown('<div style="max-width:420px; margin: 2.5rem auto 0;">', unsafe_allow_html=True)

    language_selector(location="inline")
    _brand_header(c, subtitle="Reset your password")

    if step == 1:
        st.markdown(
            f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
            f'border-radius:14px; padding:1.1rem 1.4rem; margin-bottom:0.75rem;">'
            f'<p style="margin:0 0 6px; font-size:14px; font-weight:600; color:{c["BRAND_TEXT"]};">{t("Step 1 of 2 — Enter your username")}</p>'
            f'<p style="margin:0; font-size:13px; color:{c["TEXT_MUTED"]}; line-height:1.55;">'
            f'{t("Enter the username you use to log in. We\'ll show you a WhatsApp button to contact support and get a reset code.")}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
        with st.form("forgot_step1"):
            entered_username = st.text_input(t("Your username"), value=username_hint, placeholder="e.g. ronniemanager")
            go = st.form_submit_button(t("Continue"), type="primary", use_container_width=True)
            if go:
                uname = entered_username.strip()
                if not uname:
                    st.error(t("Please enter your username."))
                else:
                    acc = get_account_by_username(uname)
                    if not acc:
                        st.error(t("No account found with that username. Check the spelling."))
                    else:
                        st.session_state["forgot_step"]    = 2
                        st.session_state["forgot_username"] = uname
                        st.rerun()

    elif step == 2:
        uname   = st.session_state.get("forgot_username", "")
        wa_msg_template = t("Hello, I forgot my GuesthousePro password. My username is: {username}. Please send me a reset code.")
        wa_msg  = wa_msg_template.format(username=uname) if "{username}" in wa_msg_template else wa_msg_template + f" {uname}"
        wa_url  = f"{SUPPORT_WHATSAPP}?text={urllib.parse.quote(wa_msg)}"

        st.markdown(
            f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
            f'border-radius:14px; padding:1.1rem 1.4rem; margin-bottom:0.75rem;">'
            f'<p style="margin:0 0 4px; font-size:13px; font-weight:600; color:{c["BRAND_TEXT"]};">{t("Step 2 of 2 — Get your reset code")}</p>'
            f'<p style="margin:0 0 12px; font-size:13px; color:{c["TEXT_MUTED"]}; line-height:1.55;">'
            f'{t("Contact support on WhatsApp with your username")} <strong>{uname}</strong>. '
            f'{t("They will generate a reset code for you. Enter it below with your new password.")}</p>'
            f'<a href="{wa_url}" target="_blank" '
            f'style="display:inline-flex; align-items:center; justify-content:center; gap:8px; '
            f'background:#25D366; color:#fff; text-decoration:none; '
            f'font-size:13px; font-weight:600; padding:9px 18px; border-radius:9px; width:100%; box-sizing:border-box;">'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="currentColor">'
            f'<path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966'
            f'-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059'
            f'-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371'
            f'-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01'
            f'-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 '
            f'2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 '
            f'2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>'
            f'<path d="M12 0C5.373 0 0 5.373 0 12c0 2.123.554 4.116 1.526 5.845L.057 23.852a.5.5 0 0 0 .614.635'
            f'l6.218-1.635A11.94 11.94 0 0 0 12 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 21.818a9.794 9.794 0 '
            f'0 1-5.006-1.373l-.36-.213-3.695.97.987-3.607-.234-.371A9.79 9.79 0 0 1 2.182 12C2.182 6.57 6.57 '
            f'2.182 12 2.182S21.818 6.57 21.818 12 17.43 21.818 12 21.818z"/></svg>'
            f'{t("Contact Support on WhatsApp")} \u00b7 {SUPPORT_NUMBER}'
            f'</a></div>',
            unsafe_allow_html=True,
        )

        with st.form("forgot_step2"):
            reset_code = st.text_input(t("Reset code (from support)"), placeholder="e.g. A3BX7KQ2", max_chars=12)
            new_pw     = st.text_input(t("New password *"), type="password", placeholder=t("at least 6 characters"))
            confirm_pw = st.text_input(t("Confirm new password *"), type="password")
            do_reset   = st.form_submit_button(t("Reset my password"), type="primary", use_container_width=True)
            if do_reset:
                if len(new_pw) < 6:
                    st.error(t("Password must be at least 6 characters."))
                elif new_pw != confirm_pw:
                    st.error(t("Passwords don't match."))
                else:
                    try:
                        acc_id = redeem_password_reset_code(uname, reset_code)
                        update_account_password(acc_id, new_pw)
                        st.session_state["forgot_step"] = 3
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))

        if st.button(t("← Change username"), use_container_width=False):
            st.session_state["forgot_step"] = 1
            st.rerun()

    elif step == 3:
        st.success(t("✅ Password reset successfully! You can now log in with your new password."))
        if st.button(t("← Back to login"), type="primary", use_container_width=True):
            for k in ["forgot_step", "forgot_username"]:
                st.session_state.pop(k, None)
            st.query_params.clear()
            st.rerun()

    st.markdown(
        f'<p style="text-align:center; font-size:13px; color:{c["TEXT_MUTED"]}; margin-top:0.75rem;">'
        f'<a href="/" target="_self" style="color:{c["ACCENT"]}; font-weight:600;">{t("← Back to login")}</a></p>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)


def _show_signup_page():
    from utils.theme import apply_theme, colors
    apply_theme()
    c = colors()

    _DIAL_CODES = [
        ("\U0001f1fa\U0001f1ec UG  +256", "+256"), ("\U0001f1f0\U0001f1ea KE  +254", "+254"),
        ("\U0001f1f9\U0001f1ff TZ  +255", "+255"), ("\U0001f1f7\U0001f1fc RW  +250", "+250"),
        ("\U0001f1f3\U0001f1ec NG  +234", "+234"), ("\U0001f1ec\U0001f1ed GH  +233", "+233"),
        ("\U0001f1ff\U0001f1e6 ZA  +27",  "+27"),  ("\U0001f1ec\U0001f1e7 GB  +44",  "+44"),
        ("\U0001f1fa\U0001f1f8 US  +1",   "+1"),   ("Other", ""),
    ]
    _CURRENCIES = [
        ("\U0001f1fa\U0001f1ec UGX \u2014 Ugandan Shilling",   "UGX"),
        ("\U0001f1f0\U0001f1ea KES \u2014 Kenyan Shilling",    "KES"),
        ("\U0001f1f9\U0001f1ff TZS \u2014 Tanzanian Shilling", "TZS"),
        ("\U0001f1f7\U0001f1fc RWF \u2014 Rwandan Franc",      "RWF"),
        ("\U0001f1f3\U0001f1ec NGN \u2014 Nigerian Naira",     "NGN"),
        ("\U0001f1fa\U0001f1f8 USD \u2014 US Dollar",          "USD"),
        ("\U0001f1ec\U0001f1e7 GBP \u2014 British Pound",      "GBP"),
        ("\U0001f1ff\U0001f1e6 ZAR \u2014 South African Rand", "ZAR"),
        ("\U0001f1e6\U0001f1ea AED \u2014 UAE Dirham",         "AED"),
        ("Other (type below)", None),
    ]
    dc_labels = [l for l, _ in _DIAL_CODES]
    dc_values = {l: v for l, v in _DIAL_CODES}
    cu_labels = [l for l, _ in _CURRENCIES]
    cu_values = {l: v for l, v in _CURRENCIES}

    st.markdown('<div style="max-width:420px; margin: 2.5rem auto 0;">', unsafe_allow_html=True)
    language_selector(location="inline")
    _brand_header(c, subtitle="Create your account — first month free, no setup fee")

    with st.form("signup_form"):
        new_username  = st.text_input(t("Username *"),             placeholder="e.g. ronniemanager")
        new_password  = st.text_input(t("Password *"),             type="password", placeholder=t("at least 6 characters"))
        confirm_pass  = st.text_input(t("Confirm password *"),     type="password", placeholder="\u00b7\u00b7\u00b7\u00b7\u00b7\u00b7\u00b7\u00b7")
        property_name = st.text_input(t("Property name *"),        placeholder="e.g. Ronnie Skyline Residences")
        st.markdown(f"**{t('Currency')}**")
        cu_label = st.selectbox(t("Currency"), cu_labels, index=0, label_visibility="collapsed")
        cu_code  = cu_values[cu_label]
        currency = st.text_input(t("Enter currency code"), value="UGX") if cu_code is None else cu_code
        st.markdown(f"**{t('Contact phone (optional)')}**")
        sc1, sc2 = st.columns([1, 2])
        with sc1:
            s_dial_label  = st.selectbox(t("Code"), dc_labels, index=0, label_visibility="collapsed")
        with sc2:
            s_phone_local = st.text_input(t("Number"), placeholder="701 234 567", label_visibility="collapsed")
        phone     = (dc_values[s_dial_label] + s_phone_local.strip()).strip()
        submitted = st.form_submit_button(t("Create account & start free trial"), type="primary", use_container_width=True)

    st.markdown(
        f'<p style="text-align:center; font-size:13px; color:{c["TEXT_MUTED"]}; margin-top:0.5rem;">'
        f'{t("Already have an account?")} <a href="/" target="_self" style="color:{c["ACCENT"]}; font-weight:600;">\u2190 {t("Back to login")}</a></p>',
        unsafe_allow_html=True,
    )
    _preview_currency = cu_code if cu_code else "UGX"
    _app_summary(c, currency=_preview_currency)
    _whatsapp_footer(c)
    st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        errors = []
        if not new_username.strip():               errors.append(t("Username is required."))
        if len(new_password) < 6:                  errors.append(t("Password must be at least 6 characters."))
        if new_password != confirm_pass:           errors.append(t("Passwords don't match."))
        if not property_name.strip():             errors.append(t("Business name is required."))
        if get_account_by_username(new_username.strip()): errors.append(t("That username is already taken."))
        if errors:
            for e in errors: st.error(e)
        else:
            from utils.subscription import create_subscription
            acct_id = create_account(
                new_username.strip(), new_password,
                property_name.strip(), currency.strip().upper(), phone.strip(),
            )
            create_subscription(acct_id, property_name.strip())
            st.session_state["authenticated"] = True
            st.session_state["account_id"]    = acct_id
            st.session_state["username"]      = new_username.strip()
            st.query_params.clear()
            st.success(t("Account created! Welcome to GuesthousePro 🎉"))
            st.rerun()

    st.stop()


def logout_button():
    from utils.db import get_account
    from utils.theme import colors

    account_id    = get_current_account_id()
    account       = get_account(account_id) or {}
    c             = colors()
    username      = account.get("username", st.session_state.get("username", ""))
    property_name = account.get("property_name", "")
    display_name  = property_name or username
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
        language_selector(location="sidebar")
        if st.button(t("Log out"), use_container_width=True):
            st.session_state.clear()
            st.rerun()


def get_current_account_id() -> int:
    return st.session_state.get("account_id", 1)
