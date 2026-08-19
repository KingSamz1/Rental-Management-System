"""
Multi-account authentication for LandlordPro.
Each account has its own username + hashed password stored in the DB.
Session state tracks account_id so every page query is scoped to the
logged-in landlord.
"""
import streamlit as st
from utils.db import get_account_by_username, verify_password, create_account, get_account

SUPPORT_WHATSAPP = "https://wa.me/256793839816"
SUPPORT_NUMBER = "+256 793 839 816"

# ── shared WhatsApp footer ────────────────────────────────────────────────────

def _whatsapp_footer(c):
    """Renders the 'Need Assistance?' WhatsApp block."""
    st.markdown(
        f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
        f'border-radius:14px; padding:1rem 1.25rem; margin-top:0.75rem; text-align:center;">'
        f'<p style="margin:0 0 8px; font-size:13px; color:{c["TEXT_MUTED"]}; font-weight:500;">Need Assistance?</p>'
        f'<a href="{SUPPORT_WHATSAPP}" target="_blank" '
        f'style="display:inline-flex; align-items:center; gap:8px; '
        f'background:#25D366; color:#fff; text-decoration:none; '
        f'font-size:13px; font-weight:600; padding:8px 18px; '
        f'border-radius:9px; transition:opacity 0.15s;">'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" '
        f'fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-'
        f'471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-'
        f'.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.'
        f'298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-'
        f'1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-'
        f'.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096'
        f' 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758'
        f'-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>'
        f'<path d="M12 0C5.373 0 0 5.373 0 12c0 2.123.554 4.116 1.526 5.845L.057 23.852a.5.5 0 0'
        f' 0 .614.635l6.218-1.635A11.94 11.94 0 0 0 12 24c6.627 0 12-5.373 12-12S18.627 0 12 0z'
        f'm0 21.818a9.794 9.794 0 0 1-5.006-1.373l-.36-.213-3.695.97.987-3.607-.234-.371A9.79 9'
        f'.79 0 0 1 2.182 12C2.182 6.57 6.57 2.182 12 2.182S21.818 6.57 21.818 12 17.43 21.818 '
        f'12 21.818z"/></svg>'
        f'Chat on WhatsApp · {SUPPORT_NUMBER}'
        f'</a>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── brand header ──────────────────────────────────────────────────────────────

def _brand_header(c, subtitle="Sign in to manage your properties"):
    st.markdown(
        f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
        f'border-radius:18px; padding:1.5rem 1.75rem 1rem; margin-bottom:0.75rem;">'
        f'<div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">'
        f'<div style="width:36px; height:36px; border-radius:10px; background:{c["ACCENT_SOFT"]}; '
        f'display:flex; align-items:center; justify-content:center; font-size:18px;">🏠</div>'
        f'<span style="font-size:18px; font-weight:650; color:{c["BRAND_TEXT"]};">LandlordPro</span>'
        f'</div>'
        f'<p style="color:{c["TEXT_MUTED"]}; margin:0; font-size:13px;">{subtitle}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── login ─────────────────────────────────────────────────────────────────────

def check_login():
    """
    Renders the login card if not authenticated.
    Returns True when the user is logged in so pages can gate their content.
    Always call this before rendering any page content.
    """
    if st.session_state.get("authenticated"):
        return True

    # Route to signup page if ?page=signup
    if st.query_params.get("page") == "signup":
        _show_signup_page()
        st.stop()

    from utils.theme import apply_theme, colors
    apply_theme()
    c = colors()

    st.markdown('<div style="max-width:420px; margin: 2.5rem auto 0;">', unsafe_allow_html=True)

    _brand_header(c, subtitle="Sign in to manage your properties")

    with st.form("login_form"):
        username = st.text_input("Username", placeholder="your username")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Log in", type="primary", use_container_width=True)

    # Sign-up link
    st.markdown(
        f'<p style="text-align:center; font-size:13px; color:{c["TEXT_MUTED"]}; margin-top:0.5rem;">'
        f'No account? '
        f'<a href="?page=signup" target="_self" style="color:{c["ACCENT"]}; font-weight:600;">'
        f'Create one →</a></p>',
        unsafe_allow_html=True,
    )

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


# ── signup ────────────────────────────────────────────────────────────────────

def _show_signup_page():
    """Full-page signup — shown when ?page=signup is in the URL."""
    from utils.theme import apply_theme, colors
    apply_theme()
    c = colors()

    st.markdown('<div style="max-width:420px; margin: 2.5rem auto 0;">', unsafe_allow_html=True)

    _brand_header(c, subtitle="Create your account — first month free, no setup fee")

    with st.form("signup_form"):
        new_username   = st.text_input("Username *", placeholder="e.g. johndoe")
        new_password   = st.text_input("Password *", type="password", placeholder="at least 6 characters")
        confirm_pass   = st.text_input("Confirm password *", type="password", placeholder="••••••••")
        business_name  = st.text_input("Business / landlord name *", placeholder="e.g. Nakawa Rentals")
        currency       = st.text_input("Currency code", value="UGX", placeholder="UGX, KES, USD …")
        phone          = st.text_input("Contact phone (optional)", placeholder="+256 7xx xxx xxx")

        submitted = st.form_submit_button(
            "Create account & start free trial",
            type="primary",
            use_container_width=True,
        )

    # Back to login link
    st.markdown(
        f'<p style="text-align:center; font-size:13px; color:{c["TEXT_MUTED"]}; margin-top:0.5rem;">'
        f'Already have an account? '
        f'<a href="/" target="_self" style="color:{c["ACCENT"]}; font-weight:600;">'
        f'← Back to login</a></p>',
        unsafe_allow_html=True,
    )

    _whatsapp_footer(c)

    st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        errors = []
        if not new_username.strip():
            errors.append("Username is required.")
        if len(new_password) < 6:
            errors.append("Password must be at least 6 characters.")
        if new_password != confirm_pass:
            errors.append("Passwords don't match.")
        if not business_name.strip():
            errors.append("Business name is required.")
        if get_account_by_username(new_username.strip()):
            errors.append("That username is already taken.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            from utils.subscription import create_subscription
            acct_id = create_account(
                new_username.strip(), new_password,
                business_name.strip(), currency.strip().upper(), phone.strip(),
            )
            create_subscription(acct_id, business_name.strip())
            st.session_state["authenticated"] = True
            st.session_state["account_id"] = acct_id
            st.session_state["username"] = new_username.strip()
            st.query_params.clear()
            st.success("Account created! Welcome to LandlordPro 🎉")
            st.rerun()

    st.stop()


# ── logout ────────────────────────────────────────────────────────────────────

def logout_button():
    username = st.session_state.get("username", "")
    label = f"Log out ({username})" if username else "Log out"
    if st.sidebar.button(label):
        st.session_state.clear()
        st.rerun()


def get_current_account_id() -> int:
    """Return the account_id of whoever is logged in. Raises if not authenticated."""
    return st.session_state.get("account_id", 1)
