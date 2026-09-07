import streamlit as st
from utils.db import init_db, get_account, list_all_accounts, delete_account
from utils.auth import check_login, logout_button, get_current_account_id, SUPPORT_WHATSAPP, SUPPORT_NUMBER
from utils.theme import apply_theme, page_header, section_label, empty_state, metric_row
from utils.currency import get_supported_currencies, format_converted, rate_note
from utils.subscription import (
    MONTHLY_FEE, GRACE_DAYS,
    create_subscription, get_subscription, update_subscription_status,
    days_remaining, subscription_payment_history,
    fast_forward, force_expire,
    is_admin, generate_renewal_code, list_renewal_codes, redeem_renewal_code,
)

st.set_page_config(page_title="Subscription — SA", page_icon="💼", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()
account    = get_account(account_id) or {}
currency   = account.get("currency", "ZAR")
admin      = is_admin(account_id)

# ── Currency display selector ──────────────────────────────────────────────────
_all_currencies = get_supported_currencies()
_default_idx = _all_currencies.index(currency) if currency in _all_currencies else 0
display_currency = st.sidebar.selectbox(
    "💱 Display currency",
    _all_currencies,
    index=_default_idx,
    help="Converts the monthly fee for reference. Billing is always in ZAR.",
)

page_header("LandlordPro Subscription", subtitle="Your Property. Your Tenants. Under Control.", icon="💼")
st.write("")

# ── Guard: create subscription if somehow missing ──────────────────────────────
sub = update_subscription_status(account_id)
if not sub:
    create_subscription(account_id, account.get("business_name", "My Rentals"))
    sub = update_subscription_status(account_id)
if not sub:
    st.error("Could not load subscription. Please contact support.")
    st.stop()

# ── Status banner ──────────────────────────────────────────────────────────────
status = sub["status"]
days   = days_remaining(account_id)

if status == "TRIAL":
    if sub.get("past_due"):
        st.warning(f"⏳ Trial ended — {sub['grace_days_left']} day(s) left before the account locks")
    elif days <= 2:
        st.info(f"⏰ Free trial — {days} day(s) remaining, renew soon to avoid interruption")
    else:
        st.success(f"🎁 Free trial — {days} day(s) remaining")
elif status == "ACTIVE":
    if sub.get("past_due"):
        st.warning(f"⏳ Payment overdue — {sub['grace_days_left']} day(s) left before the account locks")
    elif days <= 2:
        st.info(f"⏰ Active — {days} day(s) remaining, renew soon to avoid interruption")
    else:
        st.success(f"🟢 Active — {days} day(s) remaining")
else:
    st.error("🔴 Subscription expired")
    st.warning("Your property, tenant, and payment data is safe. Renew below to restore full access.")

st.markdown(f"### {sub['landlord_name']}")

due_label = "Trial ends" if status == "TRIAL" else ("Next payment" if status == "ACTIVE" else "Status")
due_value = sub["trial_end"] if status == "TRIAL" else (sub["next_payment_date"] if status == "ACTIVE" else "Expired")

metric_row([
    {"label": "Status",        "value": status,                              "tone": "accent" if status != "EXPIRED" else "danger"},
    {"label": "Days remaining","value": str(days),                           "tone": "neutral"},
    {"label": "Monthly fee",   "value": format_converted(MONTHLY_FEE, display_currency),   "tone": "neutral"},
    {"label": due_label,       "value": due_value,                           "tone": "neutral"},
])

_note = rate_note(display_currency)
if _note:
    st.caption(f"💱 {_note}")
st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN VIEW
# ═══════════════════════════════════════════════════════════════════════════════
if admin:
    section_label("🔑 Generate renewal codes")
    st.caption("Generate one-time codes to give to clients after they've paid. Each code is single-use.")

    col_months, col_btn = st.columns([2, 3])
    with col_months:
        months = st.selectbox("Months to grant", [1, 2, 3, 6, 12], index=0)
    with col_btn:
        st.write("")
        st.write("")
        if st.button("Generate new code", type="primary"):
            try:
                code = generate_renewal_code(account_id, months)
                st.success(f"✅ New code generated:")
                st.code(code, language=None)
                st.caption(f"Give this code to the client. It grants **{months} month(s)**. It can only be used once.")
            except Exception as e:
                st.error(str(e))

    st.divider()
    section_label("📋 All renewal codes")

    try:
        codes = list_renewal_codes(account_id)
        if not codes:
            empty_state("No codes generated yet.", icon="🔑")
        else:
            from utils.theme import colors
            c = colors()
            for row in codes:
                used = row["used_by"] is not None
                badge_color = c["TEXT_MUTED"] if used else c["ACCENT"]
                badge_label = f"Used by {row['used_by_username']} on {row['used_at'][:10]}" if used else "Available"
                st.markdown(
                    f'<div style="display:flex; justify-content:space-between; align-items:center; '
                    f'padding:9px 12px; margin-bottom:6px; border-radius:10px; '
                    f'background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]};">'
                    f'<div>'
                    f'<code style="font-size:15px; letter-spacing:2px;">{row["code"]}</code>'
                    f'<span style="font-size:12px; color:{c["TEXT_MUTED"]}; margin-left:12px;">'
                    f'{row["months"]} month(s) · created {row["created_at"][:10]}</span>'
                    f'</div>'
                    f'<span style="font-size:12px; font-weight:600; color:{badge_color};">{badge_label}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
    except Exception as e:
        st.error(str(e))

    st.divider()
    section_label("👥 All registered users")
    st.caption("View and manage all LandlordPro accounts. You cannot delete your own admin account.")

    try:
        all_accounts = list_all_accounts()
        for acc in all_accounts:
            is_self = acc["id"] == account_id
            label = f"{'🔑 Admin — ' if is_self else ''}{acc['username']} · {acc['business_name']} · {acc['currency']}"
            with st.expander(label):
                st.write(f"**ID:** {acc['id']}")
                st.write(f"**Username:** {acc['username']}")
                st.write(f"**Business name:** {acc['business_name']}")
                st.write(f"**Currency:** {acc['currency']}")
                st.write(f"**Phone:** {acc['business_phone'] or '—'}")
                st.write(f"**Created:** {acc['created_at'][:10] if acc['created_at'] else '—'}")
                if not is_self:
                    confirm_key = f"confirm_delete_{acc['id']}"
                    if st.session_state.get(confirm_key):
                        st.warning(f"⚠️ Are you sure you want to delete **{acc['username']}**? This will erase ALL their data permanently.")
                        col_yes, col_no = st.columns(2)
                        if col_yes.button("Yes, delete account", key=f"yes_del_{acc['id']}", type="primary"):
                            delete_account(acc["id"])
                            st.session_state.pop(confirm_key, None)
                            st.success(f"Account '{acc['username']}' deleted.")
                            st.rerun()
                        if col_no.button("Cancel", key=f"no_del_{acc['id']}"):
                            st.session_state.pop(confirm_key, None)
                            st.rerun()
                    else:
                        if st.button(f"🗑️ Delete {acc['username']}", key=f"del_{acc['id']}"):
                            st.session_state[confirm_key] = True
                            st.rerun()
    except Exception as e:
        st.error(str(e))

    st.divider()
    with st.expander("🛠️ Developer / testing tools"):
        st.caption(
            f"Fast-forward trial/billing dates to test expiry. "
            f"There's a {GRACE_DAYS}-day grace window after the due date."
        )
        col_a, col_b = st.columns(2)
        with col_a:
            days_to_skip = st.number_input("Days to fast-forward", min_value=1, max_value=365, value=7, step=1)
            if st.button("Fast-forward subscription"):
                fast_forward(account_id, int(days_to_skip))
                st.rerun()
        with col_b:
            st.write("")
            st.write("")
            if st.button("Force expire now", type="secondary"):
                force_expire(account_id)
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# CLIENT VIEW
# ═══════════════════════════════════════════════════════════════════════════════
else:
    from utils.theme import colors
    c = colors()

    section_label("Renew subscription")

    # WhatsApp CTA
    wa_msg = (
        f"Hello, I would like to renew my LandlordPro subscription. "
        f"Account: {account.get('username', '')} / {account.get('business_name', '')}. "
        f"Please send me a renewal code."
    )
    import urllib.parse
    wa_url = f"https://wa.me/27718726504?text={urllib.parse.quote(wa_msg)}"

    st.markdown(
        f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
        f'border-radius:14px; padding:1.25rem 1.5rem; margin-bottom:1rem;">'
        f'<p style="margin:0 0 6px; font-size:15px; font-weight:600; color:{c["BRAND_TEXT"]};">'
        f'Want to renew your subscription?</p>'
        f'<p style="margin:0 0 14px; font-size:13px; color:{c["TEXT_MUTED"]}; line-height:1.55;">'
        f'Send us a message on WhatsApp and we\'ll process your payment and send you a renewal code. '
        f'Monthly fee: <strong>{format_converted(MONTHLY_FEE, display_currency)}</strong>.</p>'
        f'<a href="{wa_url}" target="_blank" '
        f'style="display:inline-flex; align-items:center; gap:8px; '
        f'background:#25D366; color:#fff; text-decoration:none; '
        f'font-size:13px; font-weight:600; padding:9px 20px; '
        f'border-radius:9px;">'
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
        f'Chat on WhatsApp · {SUPPORT_NUMBER}'
        f'</a>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Code redemption
    st.markdown(
        f'<p style="font-size:13px; font-weight:600; color:{c["BRAND_TEXT"]}; margin:0 0 4px;">Have a renewal code?</p>',
        unsafe_allow_html=True,
    )
    with st.form("redeem_form"):
        code_input = st.text_input("Enter your code", placeholder="e.g. A3BX7KQ2MN", max_chars=20)
        redeemed = st.form_submit_button("Activate code", type="primary")
        if redeemed:
            try:
                updated = redeem_renewal_code(account_id, code_input)
                st.success(f"✅ Subscription activated! Next payment due {updated['next_payment_date']}.")
                st.rerun()
            except (ValueError, PermissionError) as e:
                st.error(str(e))

    st.divider()
    section_label("Payment history")
    history = subscription_payment_history(account_id)
    if not history:
        empty_state("No subscription payments recorded yet.", icon="💼")
    else:
        for p in history:
            with st.expander(f"{p['payment_date']} — {currency} {p['amount']:,.0f}"):
                st.write(f"**Reference / Code:** {p['transaction_reference']}")
                st.write(f"**Period:** {p['period_start']} → {p['period_end']}")
                if p["note"]:
                    st.write(f"**Note:** {p['note']}")
