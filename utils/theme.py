"""
Shared visual styling: CSS injection + HTML component helpers.

Streamlit's built-in widgets (st.metric, st.info, forms) recolor themselves
automatically from the [theme.light]/[theme.dark] tables in config.toml, and
Streamlit already picks the right table based on the viewer's OS/browser
preference (or their manual choice in the app menu). Native widgets need
nothing from us.

Our own raw-HTML components (metric tiles, status pills, the login card)
are not native widgets, so they don't get that switching for free — they
need to be told which palette to use. `st.context.theme.type` reports which
table Streamlit is *currently rendering with* ("light" or "dark"), so we
read it once per run and pick a matching hex palette in Python. This is
more reliable than a `prefers-color-scheme` CSS media query, because it
follows Streamlit's own active theme (including a manual override in the
app menu) rather than only the OS setting.

IMPORTANT — no leading whitespace in generated HTML: Streamlit's markdown
renderer treats a line that starts with 4+ spaces as an indented code
block, which dumps the HTML on screen as literal text instead of rendering
it. Every HTML string built here is written flush-left / single-line for
that reason — don't reintroduce pretty-printed indentation when editing
this file.

Usage at the top of every page, right after st.set_page_config():
    from utils.theme import apply_theme
    apply_theme()
"""
import streamlit as st

_PALETTES = {
    "light": dict(
        ACCENT="#2F6F4E",
        ACCENT_DARK="#1F4D37",
        ACCENT_SOFT="#EAF3EE",
        DANGER="#B3392E",
        DANGER_SOFT="#FBEAE8",
        NEUTRAL_SOFT="#F3F4F1",
        TEXT="#1F2A24",
        TEXT_MUTED="#6B7280",
        BORDER="#E7E9E6",
        CARD_BG="#FFFFFF",
        SIDEBAR_BG="#FBFBFA",
        BRAND_TEXT="#14261C",
    ),
    "dark": dict(
        ACCENT="#22C55E",
        ACCENT_DARK="#4ADE80",
        ACCENT_SOFT="#15301F",
        DANGER="#F87171",
        DANGER_SOFT="#3A1616",
        NEUTRAL_SOFT="#1E1F1E",
        TEXT="#F2F3F1",
        TEXT_MUTED="#9CA3A1",
        BORDER="#3A3C39",
        CARD_BG="#191A19",
        SIDEBAR_BG="#151615",
        BRAND_TEXT="#F2F3F1",
    ),
}

RADIUS = "14px"


def _mode():
    """Return 'light' or 'dark' — whichever palette Streamlit is currently rendering with."""
    try:
        return st.context.theme.type
    except Exception:
        # st.context.theme needs a live ScriptRunContext; fall back to light
        # if it's ever unavailable (e.g. imported outside a running app).
        return "light"


def colors():
    """Return the hex palette dict matching the active theme this run."""
    return _PALETTES[_mode()]


# Backwards-compatible module-level constants (light palette) for any code
# that imported these directly. Prefer colors() in new code — these don't
# switch with the theme.
ACCENT = _PALETTES["light"]["ACCENT"]
ACCENT_DARK = _PALETTES["light"]["ACCENT_DARK"]
ACCENT_SOFT = _PALETTES["light"]["ACCENT_SOFT"]
DANGER = _PALETTES["light"]["DANGER"]
DANGER_SOFT = _PALETTES["light"]["DANGER_SOFT"]
NEUTRAL_SOFT = _PALETTES["light"]["NEUTRAL_SOFT"]
TEXT_MUTED = _PALETTES["light"]["TEXT_MUTED"]
BORDER = _PALETTES["light"]["BORDER"]


def apply_theme():
    """Inject shared CSS for the currently active theme. Safe to call at the top of every page."""
    c = colors()
    st.markdown(
        f"""
        <style>
        .block-container {{
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 900px;
        }}
        h1, h2, h3 {{ letter-spacing: -0.01em; font-weight: 650; }}
        p, label, .stMarkdown {{ color: {c['TEXT']}; }}

        section[data-testid="stSidebar"] {{
            background-color: {c['SIDEBAR_BG']};
            border-right: 1px solid {c['BORDER']};
        }}
        section[data-testid="stSidebar"] .stButton button {{ border-radius: 10px; }}

        .stButton button, .stDownloadButton button, .stFormSubmitButton button, .stLinkButton a {{
            border-radius: 10px;
            border: 1px solid {c['BORDER']};
            font-weight: 500;
            padding: 0.5rem 1.1rem;
            transition: all 0.15s ease;
        }}
        .stButton button:hover, .stDownloadButton button:hover, .stFormSubmitButton button:hover {{
            border-color: {c['ACCENT']};
            color: {c['ACCENT']};
        }}
        button[kind="primary"] {{ background-color: {c['ACCENT']} !important; border: none !important; }}
        button[kind="primary"]:hover {{ background-color: {c['ACCENT_DARK']} !important; color: {c['CARD_BG']} !important; }}

        /* Native inputs share the config.toml secondaryBackgroundColor with
        the sidebar and with our own CARD_BG-filled containers (forms,
        cards) — when an input sits inside one of those it can end up the
        same color as its container and become invisible. Force a visible
        border on every input regardless of what's behind it. */
        .stTextInput input, .stNumberInput input, .stDateInput input,
        .stSelectbox div[data-baseweb="select"] > div, .stTextArea textarea {{
            border-radius: 10px !important;
            border: 1px solid {c['BORDER']} !important;
        }}

        /* Forms are just a border/frame, not a filled card — a filled
        background here is what was hiding the inputs above in dark mode
        (same fill color as the inputs' own native background). */
        div[data-testid="stForm"] {{
            border: 1px solid {c['BORDER']};
            border-radius: {RADIUS};
            padding: 1.5rem 1.5rem 0.5rem;
            background-color: transparent;
        }}

        div[data-testid="stExpander"] {{
            border: 1px solid {c['BORDER']};
            border-radius: {RADIUS};
            box-shadow: 0 1px 2px rgba(0,0,0,0.02);
        }}
        div[data-testid="stExpander"] summary {{ font-weight: 550; }}

        div[data-testid="stDataFrame"] {{
            border: 1px solid {c['BORDER']};
            border-radius: 10px;
            overflow: hidden;
        }}

        hr {{ margin: 1.75rem 0; border-color: {c['BORDER']}; }}
        div[data-testid="stAlert"] {{ border-radius: 10px; }}

        .login-card {{
            max-width: 380px;
            margin: 3rem auto 0;
            padding: 2rem 2rem 1.5rem;
            background: {c['CARD_BG']};
            border: 1px solid {c['BORDER']};
            border-radius: 18px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.04);
        }}
        .login-brand {{ display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }}
        .login-brand-icon {{
            width: 36px; height: 36px; border-radius: 10px;
            background: {c['ACCENT_SOFT']}; display: flex; align-items: center;
            justify-content: center; font-size: 18px;
        }}
        .login-brand-name {{ font-size: 18px; font-weight: 650; color: {c['BRAND_TEXT']}; }}
        .login-subtitle {{ font-size: 13px; color: {c['TEXT_MUTED']}; margin: 0 0 1.5rem; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title, subtitle=None, icon=None):
    """Consistent page title block: icon + title, optional muted subtitle."""
    c = colors()
    icon_html = f'<span style="margin-right:8px;">{icon}</span>' if icon else ""
    st.markdown(f'<h2 style="margin-bottom:0.15rem;">{icon_html}{title}</h2>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f"<p style='color:{c['TEXT_MUTED']}; margin-top:-0.4rem;'>{subtitle}</p>", unsafe_allow_html=True)


def section_label(text):
    """A small muted overline label above a section."""
    c = colors()
    st.markdown(
        f"<p style='color:{c['TEXT_MUTED']}; font-size:0.8rem; font-weight:600; "
        f"text-transform:uppercase; letter-spacing:0.06em; margin-bottom:0.3rem;'>{text}</p>",
        unsafe_allow_html=True,
    )


def empty_state(message, icon="📭"):
    """A friendlier empty state than a plain st.info."""
    c = colors()
    html = (
        f'<div style="text-align:center; padding:2.5rem 1rem; color:{c["TEXT_MUTED"]}; '
        f'background-color:{c["ACCENT_SOFT"]}; border-radius:{RADIUS}; border:1px dashed {c["BORDER"]};">'
        f'<div style="font-size:1.8rem; margin-bottom:0.4rem;">{icon}</div>'
        f'<div>{message}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def login_header(app_name="LandlordPro", icon="🏠"):
    """Card-style header for the login screen, shown above the login form."""
    html = (
        f'<div class="login-card">'
        f'<div class="login-brand">'
        f'<div class="login-brand-icon">{icon}</div>'
        f'<span class="login-brand-name">{app_name}</span>'
        f'</div>'
        f'<p class="login-subtitle">Sign in to manage your properties</p>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def metric_row(metrics):
    """Render a row of colored metric tiles as HTML.
    metrics: list of dicts with label (str), value (str), tone ('neutral'|'accent'|'danger')."""
    c = colors()
    tone_styles = {
        "neutral": (c["NEUTRAL_SOFT"], c["BRAND_TEXT"], c["TEXT_MUTED"]),
        "accent": (c["ACCENT_SOFT"], c["ACCENT_DARK"], c["ACCENT"]),
        "danger": (c["DANGER_SOFT"], c["DANGER"], c["DANGER"]),
    }
    tiles = ""
    for m in metrics:
        bg, value_color, label_color = tone_styles.get(m.get("tone", "neutral"), tone_styles["neutral"])
        tiles += (
            f'<div style="background:{bg}; border-radius:10px; padding:1rem 1.1rem; flex:1; min-width:140px;">'
            f'<p style="font-size:13px; color:{label_color}; margin:0 0 4px; font-weight:500;">{m["label"]}</p>'
            f'<p style="font-size:22px; font-weight:650; margin:0; color:{value_color};">{m["value"]}</p>'
            f'</div>'
        )
    st.markdown(f'<div style="display:flex; gap:12px; flex-wrap:wrap; margin-bottom:1rem;">{tiles}</div>', unsafe_allow_html=True)


def status_pill(text, tone="neutral"):
    """Return an HTML snippet for an inline colored status pill.
    tone: 'success' (green), 'danger' (red/coral), 'neutral' (gray)."""
    c = colors()
    styles = {
        "success": (c["ACCENT_SOFT"], c["ACCENT_DARK"]),
        "danger": (c["DANGER_SOFT"], c["DANGER"]),
        "neutral": (c["NEUTRAL_SOFT"], c["TEXT_MUTED"]),
    }
    bg, color = styles.get(tone, styles["neutral"])
    return (
        f'<span style="background:{bg}; color:{color}; font-size:12px; font-weight:600; '
        f'padding:3px 10px; border-radius:999px; white-space:nowrap;">{text}</span>'
    )


def subscription_banner():
    """Shows a small status banner. Call after check_login() so account_id exists."""
    from utils.subscription import update_subscription_status, days_remaining, is_admin
    from utils.auth import get_current_account_id
    account_id = get_current_account_id()
    if is_admin(account_id):
        return  # Admin always has full access — no banner needed
    sub = update_subscription_status(account_id)
    if not sub:
        return
    status = sub["status"]
    days = days_remaining(account_id)
    if status == "TRIAL":
        if sub.get("past_due"):
            st.warning(f"⏳ Your free trial ended — {sub['grace_days_left']} day(s) left before the account locks. Renew on the Subscription page to stay active.")
        elif days <= 2:
            st.info(f"⏰ Your free trial ends in {days} day(s). Renew on the Subscription page to avoid interruption.")
        else:
            st.info(f"🎁 LandlordPro free trial — {days} day(s) remaining")
    elif status == "ACTIVE":
        if sub.get("past_due"):
            st.warning(f"⏳ Payment overdue — {sub['grace_days_left']} day(s) left before the account locks. Renew on the Subscription page to stay active.")
        elif days <= 2:
            st.info(f"⏰ Your subscription renews in {days} day(s). Renew on the Subscription page to avoid interruption.")
    else:
        st.error("🔴 LandlordPro subscription expired — some actions are locked. Renew on the Subscription page.")


def require_active_subscription():
    """Call before a write action. Returns True if allowed to proceed."""
    from utils.subscription import system_active, is_admin
    from utils.auth import get_current_account_id
    account_id = get_current_account_id()
    if is_admin(account_id) or system_active(account_id):
        return True
    st.error("🔒 Your LandlordPro subscription has expired. Your data is safe — renew on the **Subscription** page to continue adding or editing records.")
    return False
