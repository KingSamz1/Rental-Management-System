"""
Authentication for LandlordPro.
Supports two flows — both coexist, users can use either:
  1. Username + password  (existing accounts, always available)
  2. Google OAuth 2.0     (requires [google_oauth] block in secrets.toml)

OAuth flow:
  - User clicks "Continue with Google" → redirected to Google
  - Google redirects back to redirect_uri with ?code=...&state=...
  - check_login() detects these params FIRST (before rendering any UI)
  - Exchanges the code for an access token, fetches userinfo, logs in
"""
import secrets
import urllib.parse
import streamlit as st
from utils.db import (
    get_account_by_username, verify_password, create_account,
    get_account, upsert_google_account,
)

SUPPORT_WHATSAPP = "https://wa.me/256793839816"
SUPPORT_NUMBER = "+256 793 839 816"

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_SCOPES = "openid email profile"


def _google_cfg():
    try:
        cfg = st.secrets["google_oauth"]
        cid = cfg.get("client_id", "")
        cs  = cfg.get("client_secret", "")
        ru  = cfg.get("redirect_uri", "http://localhost:8501/")
        if cid and cs and not cid.startswith("YOUR_"):
            return cid, cs, ru
    except Exception:
        pass
    return None


def google_is_configured():
    return _google_cfg() is not None


def build_google_auth_url():
    cfg = _google_cfg()
    if not cfg:
        return None, None
    client_id, _, redirect_uri = cfg
    state = secrets.token_urlsafe(16)
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    url = GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params)
    return url, state


def exchange_google_code(code):
    """Exchange an auth code for userinfo. Uses requests (always available)."""
    import requests as req
    cfg = _google_cfg()
    if not cfg:
        raise RuntimeError("Google OAuth not configured.")
    client_id, client_secret, redirect_uri = cfg

    token_resp = req.post(GOOGLE_TOKEN_URL, data={
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }, timeout=10)
    token_resp.raise_for_status()
    tokens = token_resp.json()

    if "error" in tokens:
        raise RuntimeError(f"Token exchange failed: {tokens.get('error_description', tokens['error'])}")

    info_resp = req.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        timeout=10,
    )
    info_resp.raise_for_status()
    return info_resp.json()


def _handle_oauth_callback():
    """
    Called at the very top of check_login(), before any UI is rendered.
    If ?code= is present in the URL, this is Google's redirect — exchange
    the code and log the user in. Returns True if handled (caller should stop),
    False if this is a normal page load.
    """
    params = st.query_params
    code  = params.get("code")
    state = params.get("state")

    if not code:
        return False

    # State check — warn but don't hard-block (state lives in session which
    # can reset if the server restarts between the redirect and the callback)
    stored_state = st.session_state.get("oauth_state")
    if stored_state and state != stored_state:
        st.error("OAuth state mismatch — please try signing in again.")
        st.query_params.clear()
        st.rerun()
        return True

    # Clear the code from the URL immediately so a browser refresh doesn't
    # re-attempt the exchange (codes are single-use)
    st.query_params.clear()

    with st.spinner("Signing you in with Google…"):
        try:
            userinfo = exchange_google_code(code)
            login_with_google_userinfo(userinfo)
            st.rerun()
        except Exception as e:
            st.error(f"Google sign-in failed: {e}")
            st.info("You can still log in with your username and password below.")

    return True


def login_with_google_userinfo(userinfo):
    email = userinfo.get("email", "")
    name  = userinfo.get("name", email.split("@")[0])
    account = upsert_google_account(email, name)
    from utils.db import get_conn
    with get_conn() as conn:
        existing_sub = conn.execute(
            "SELECT id FROM subscription WHERE account_id=?", (account["id"],)
        ).fetchone()
    if not existing_sub:
        from utils.subscription import create_subscription
        create_subscription(account["id"], name)
    st.session_state["authenticated"] = True
    st.session_state["account_id"]    = account["id"]
    st.session_state["username"]      = account["username"]
    st.session_state["google_picture"] = userinfo.get("picture", "")
    return account


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
        f'<span style="font-size:18px; font-weight:650; color:{c["BRAND_TEXT"]};">LandlordPro</span>'
        f'</div>'
        f'<p style="color:{c["TEXT_MUTED"]}; margin:0; font-size:13px;">{subtitle}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _google_button(c, auth_url):
    st.markdown(
        f'<a href="{auth_url}" target="_self" style="'
        f'display:flex; align-items:center; justify-content:center; gap:10px; '
        f'background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
        f'color:{c["BRAND_TEXT"]}; text-decoration:none; font-size:14px; font-weight:600; '
        f'padding:10px 16px; border-radius:10px; margin-bottom:0.5rem;">'
        f'<svg width="18" height="18" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">'
        f'<path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>'
        f'<path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>'
        f'<path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>'
        f'<path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>'
        f'</svg>Continue with Google</a>',
        unsafe_allow_html=True,
    )


def _divider_or(c):
    st.markdown(
        f'<div style="display:flex; align-items:center; gap:10px; margin:0.5rem 0;">'
        f'<div style="flex:1; height:1px; background:{c["BORDER"]};"></div>'
        f'<span style="font-size:12px; color:{c["TEXT_MUTED"]};">or</span>'
        f'<div style="flex:1; height:1px; background:{c["BORDER"]};"></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _app_summary(c):
    features = [
        ("\U0001f3e2", "Properties & units", "Add buildings and individual units in seconds."),
        ("\U0001f464", "Tenant management", "Store contacts, move-in dates, and documents."),
        ("\U0001f4b0", "Rent & water bills", "Charge rent or water per tenant each month."),
        ("\U0001f4b3", "Payments & receipts", "Record cash or MoMo payments, auto-generate PDF receipts."),
        ("\U0001f510", "Deposits & advance rent", "Track security deposits and prepaid months separately."),
        ("\U0001f4f2", "WhatsApp reminders", "One-tap reminder links sent straight to tenants."),
        ("\U0001f4ca", "Reports", "Monthly income, outstanding balances, and tenant history."),
    ]
    items_html = "".join(
        f'<div style="display:flex; align-items:flex-start; gap:10px; padding:7px 0; border-bottom:1px solid {c["BORDER"]};">'
        f'<span style="font-size:16px; line-height:1.4;">{icon}</span>'
        f'<div><span style="font-size:13px; font-weight:600; color:{c["BRAND_TEXT"]};">{title}</span>'
        f'<span style="font-size:12px; color:{c["TEXT_MUTED"]};"> \u2014 {desc}</span></div></div>'
        for icon, title, desc in features
    )
    st.markdown(
        f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
        f'border-radius:14px; padding:1rem 1.25rem; margin-top:0.75rem;">'
        f'<p style="margin:0 0 10px; font-size:13px; font-weight:700; color:{c["BRAND_TEXT"]}; '
        f'letter-spacing:0.02em; text-transform:uppercase;">What LandlordPro does</p>'
        f'{items_html}'
        f'<p style="margin:10px 0 0; font-size:12px; color:{c["TEXT_MUTED"]}; font-style:italic;">'
        f'First month free \u00b7 No setup fee \u00b7 Works on any device</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def check_login():
    if st.session_state.get("authenticated"):
        return True

    # Handle Google's redirect BEFORE rendering any UI.
    # If ?code= is in the URL this is the OAuth callback — process it and stop.
    if _handle_oauth_callback():
        st.stop()

    if st.query_params.get("page") == "signup":
        _show_signup_page()
        st.stop()

    from utils.theme import apply_theme, colors
    apply_theme()
    c = colors()

    st.markdown('<div style="max-width:420px; margin: 2.5rem auto 0;">', unsafe_allow_html=True)
    _brand_header(c, subtitle="Sign in to manage your properties")

    if google_is_configured():
        auth_url, state = build_google_auth_url()
        st.session_state["oauth_state"] = state
        _google_button(c, auth_url)
        _divider_or(c)

    with st.form("login_form"):
        username = st.text_input("Username", placeholder="your username")
        password = st.text_input("Password", type="password", placeholder="\u00b7\u00b7\u00b7\u00b7\u00b7\u00b7\u00b7\u00b7")
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
            st.session_state["account_id"] = account["id"]
            st.session_state["username"] = account["username"]
            st.rerun()
        else:
            st.error("Invalid username or password.")

    st.stop()


def _show_signup_page():
    from utils.theme import apply_theme, colors
    apply_theme()
    c = colors()

    _DIAL_CODES = [
        ("\U0001f1fa\U0001f1ec UG  +256", "+256"), ("\U0001f1f0\U0001f1ea KE  +254", "+254"),
        ("\U0001f1f9\U0001f1ff TZ  +255", "+255"), ("\U0001f1f7\U0001f1fc RW  +250", "+250"),
        ("\U0001f1f3\U0001f1ec NG  +234", "+234"), ("\U0001f1ec\U0001f1ed GH  +233", "+233"),
        ("\U0001f1ff\U0001f1e6 ZA  +27", "+27"), ("\U0001f1ec\U0001f1e7 GB  +44", "+44"),
        ("\U0001f1fa\U0001f1f8 US  +1", "+1"), ("Other", ""),
    ]
    _CURRENCIES = [
        ("\U0001f1fa\U0001f1ec UGX \u2014 Ugandan Shilling", "UGX"),
        ("\U0001f1f0\U0001f1ea KES \u2014 Kenyan Shilling", "KES"),
        ("\U0001f1f9\U0001f1ff TZS \u2014 Tanzanian Shilling", "TZS"),
        ("\U0001f1f7\U0001f1fc RWF \u2014 Rwandan Franc", "RWF"),
        ("\U0001f1f3\U0001f1ec NGN \u2014 Nigerian Naira", "NGN"),
        ("\U0001f1fa\U0001f1f8 USD \u2014 US Dollar", "USD"),
        ("\U0001f1ec\U0001f1e7 GBP \u2014 British Pound", "GBP"),
        ("Other (type below)", None),
    ]
    dc_labels = [l for l, _ in _DIAL_CODES]
    dc_values = {l: v for l, v in _DIAL_CODES}
    cu_labels = [l for l, _ in _CURRENCIES]
    cu_values = {l: v for l, v in _CURRENCIES}

    st.markdown('<div style="max-width:420px; margin: 2.5rem auto 0;">', unsafe_allow_html=True)
    _brand_header(c, subtitle="Create your account \u2014 first month free, no setup fee")

    if google_is_configured():
        auth_url, state = build_google_auth_url()
        st.session_state["oauth_state"] = state
        _google_button(c, auth_url)
        _divider_or(c)

    with st.form("signup_form"):
        new_username  = st.text_input("Username *", placeholder="e.g. johndoe")
        new_password  = st.text_input("Password *", type="password", placeholder="at least 6 characters")
        confirm_pass  = st.text_input("Confirm password *", type="password", placeholder="\u00b7\u00b7\u00b7\u00b7\u00b7\u00b7\u00b7\u00b7")
        business_name = st.text_input("Business / landlord name *", placeholder="e.g. Nakawa Rentals")
        st.markdown("**Currency**")
        cu_label = st.selectbox("Currency", cu_labels, index=0, label_visibility="collapsed")
        cu_code  = cu_values[cu_label]
        currency = st.text_input("Enter currency code", value="UGX") if cu_code is None else cu_code
        st.markdown("**Contact phone (optional)**")
        sc1, sc2 = st.columns([1, 2])
        with sc1:
            s_dial_label = st.selectbox("Code", dc_labels, index=0, label_visibility="collapsed")
        with sc2:
            s_phone_local = st.text_input("Number", placeholder="701 234 567", label_visibility="collapsed")
        phone = (dc_values[s_dial_label] + s_phone_local.strip()).strip()
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
        if not new_username.strip(): errors.append("Username is required.")
        if len(new_password) < 6: errors.append("Password must be at least 6 characters.")
        if new_password != confirm_pass: errors.append("Passwords don't match.")
        if not business_name.strip(): errors.append("Business name is required.")
        if get_account_by_username(new_username.strip()): errors.append("That username is already taken.")
        if errors:
            for e in errors: st.error(e)
        else:
            from utils.subscription import create_subscription
            acct_id = create_account(new_username.strip(), new_password, business_name.strip(), currency.strip().upper(), phone.strip())
            create_subscription(acct_id, business_name.strip())
            st.session_state["authenticated"] = True
            st.session_state["account_id"] = acct_id
            st.session_state["username"] = new_username.strip()
            st.query_params.clear()
            st.success("Account created! Welcome to LandlordPro \U0001f389")
            st.rerun()

    st.stop()


def logout_button():
    """Sidebar account card: avatar initials (or Google picture), name, email, logout."""
    from utils.db import get_account
    from utils.theme import colors

    account_id = get_current_account_id()
    account    = get_account(account_id) or {}
    c = colors()

    username      = account.get("username", st.session_state.get("username", ""))
    business_name = account.get("business_name", "")
    google_email  = account.get("google_email", "")
    google_name   = account.get("google_name", "")
    auth_method   = account.get("auth_method", "password")

    # Display name: prefer Google name, fall back to business name, then username
    display_name = google_name or business_name or username
    # Sub-line: email if Google, otherwise username
    sub_line     = google_email if google_email else f"@{username}"
    # Avatar: first letter of display name
    initial      = (display_name[0] if display_name else "?").upper()
    # Badge colour: green for Google accounts, accent for password accounts
    badge_color  = "#22C55E" if "google" in auth_method else c["ACCENT"]

    # Google avatar URL if available (uses Google's people API picture field stored at login)
    google_picture = st.session_state.get("google_picture", "")

    with st.sidebar:
        if google_picture:
            # Round image via CSS
            st.markdown(
                f'<div style="display:flex; align-items:center; gap:10px; '
                f'padding:10px 0 6px;">'
                f'<img src="{google_picture}" width="38" height="38" '
                f'style="border-radius:50%; object-fit:cover; border:2px solid {badge_color};">'
                f'<div style="overflow:hidden;">'
                f'<div style="font-size:13px; font-weight:600; color:{c["BRAND_TEXT"]}; '
                f'white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{display_name}</div>'
                f'<div style="font-size:11px; color:{c["TEXT_MUTED"]}; '
                f'white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{sub_line}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="display:flex; align-items:center; gap:10px; '
                f'padding:10px 0 6px;">'
                f'<div style="width:38px; height:38px; border-radius:50%; '
                f'background:{badge_color}; display:flex; align-items:center; '
                f'justify-content:center; font-size:16px; font-weight:700; '
                f'color:#fff; flex-shrink:0;">{initial}</div>'
                f'<div style="overflow:hidden;">'
                f'<div style="font-size:13px; font-weight:600; color:{c["BRAND_TEXT"]}; '
                f'white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{display_name}</div>'
                f'<div style="font-size:11px; color:{c["TEXT_MUTED"]}; '
                f'white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{sub_line}</div>'
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
