"""
Basic username/password login using Streamlit secrets.
Not production-grade auth (no hashing, no lockouts, no sessions beyond
Streamlit's own session_state) — good enough for a single-landlord MVP
running locally or behind another access layer.
"""
import streamlit as st
from utils.theme import apply_theme, login_header


def check_login():
    """Renders a card-style login form if not authenticated. Returns True once logged in."""
    if st.session_state.get("authenticated"):
        return True

    apply_theme()  # ensure styling applies even though pages call this before their own apply_theme()
    login_header()

    try:
        valid_user = st.secrets["auth"]["username"]
        valid_pass = st.secrets["auth"]["password"]
    except (KeyError, FileNotFoundError):
        st.markdown('<div style="max-width:380px; margin:0 auto;">', unsafe_allow_html=True)
        st.error(
            "No login configured. Copy `.streamlit/secrets.toml.example` to "
            "`.streamlit/secrets.toml` and set a username/password."
        )
        st.markdown('</div>', unsafe_allow_html=True)
        st.stop()

    st.markdown('<div style="max-width:380px; margin:-1.75rem auto 0;">', unsafe_allow_html=True)
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="admin")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Log in", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        if username == valid_user and password == valid_pass:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.markdown('<div style="max-width:380px; margin:0 auto;">', unsafe_allow_html=True)
            st.error("Invalid username or password.")
            st.markdown('</div>', unsafe_allow_html=True)

    st.stop()


def logout_button():
    if st.sidebar.button("Log out"):
        st.session_state["authenticated"] = False
        st.rerun()
