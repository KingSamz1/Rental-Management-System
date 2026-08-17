import streamlit as st
from datetime import date
from utils.db import init_db, get_setting
from utils.auth import check_login, logout_button
from utils.logic import (
    list_units, add_tenant, list_tenants, get_tenant, vacate_tenant, tenant_balance,
    save_tenant_id_document, update_tenant_id_document, update_tenant,
)
from utils.theme import apply_theme, page_header, empty_state, subscription_banner, require_active_subscription

st.set_page_config(page_title="Tenants", page_icon="👤", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

currency = get_setting("currency", "UGX")

page_header("Tenants", icon="👤")
subscription_banner()
st.write("")

tab1, tab2 = st.tabs(["Add tenant", "All tenants"])

with tab1:
    vacant_units = [u for u in list_units() if u["status"] == "vacant"]
    if not vacant_units:
        empty_state("No vacant units available. Add a unit first, or vacate an existing tenant.", icon="🚪")
    else:
        with st.form("add_tenant_form", clear_on_submit=True):
            unit_options = {f"{u['property_name']} — {u['unit_name']} ({currency} {u['monthly_rent']:,.0f}/mo)": u["id"]
                             for u in vacant_units}
            unit_label = st.selectbox("Unit*", list(unit_options.keys()))
            full_name = st.text_input("Full name*")
            phone = st.text_input(
                "Phone (with country code)",
                value="+256",
                help="Keep the +256 prefix and add the rest of the Ugandan number, e.g. +256701234567",
            )
            email = st.text_input("Email")

            st.markdown("**Identification**")
            st.caption(
                "Record either a National ID or Passport number, and optionally attach a photo "
                "of the physical document (front page/data page) for your records."
            )
            id_number = st.text_input(
                "National ID number or Passport number",
                help="e.g. CM12345678ABCD for a Ugandan National ID, or the passport number from the data page.",
            )
            id_photo = st.file_uploader(
                "Photo of National ID or Passport (optional)",
                type=["png", "jpg", "jpeg", "pdf"],
            )

            move_in_date = st.date_input("Move-in date")
            submitted = st.form_submit_button("Add tenant")
            if submitted:
                if not require_active_subscription():
                    pass
                elif not full_name.strip():
                    st.error("Full name is required.")
                else:
                    tenant_id = add_tenant(
                        unit_options[unit_label], full_name.strip(), phone.strip(),
                        email.strip(), id_number.strip(), "", move_in_date.isoformat(),
                    )
                    if id_photo is not None:
                        path = save_tenant_id_document(tenant_id, id_photo)
                        update_tenant_id_document(tenant_id, path)
                    st.success(f"Added tenant '{full_name}'.")
                    st.rerun()

with tab2:
    status_filter = st.radio("Show", ["active", "vacated", "all"], horizontal=True)
    tenants = list_tenants(status=None if status_filter == "all" else status_filter)

    if not tenants:
        empty_state("No tenants found.", icon="👤")
    else:
        for t in tenants:
            bal = tenant_balance(t["id"])
            with st.expander(
                f"{t['full_name']} — {t['property_name']} / {t['unit_name']} "
                f"({t['status']}, balance: {currency} {bal['balance']:,.0f})"
            ):
                edit_mode_key = f"editing_{t['id']}"
                if st.session_state.get(edit_mode_key):
                    with st.form(f"edit_tenant_form_{t['id']}"):
                        e_full_name = st.text_input("Full name*", value=t["full_name"])
                        e_phone = st.text_input("Phone", value=t["phone"] or "")
                        e_email = st.text_input("Email", value=t["email"] or "")
                        e_id_number = st.text_input("National ID number or Passport number", value=t.get("id_number") or "")
                        e_move_in = st.date_input(
                            "Move-in date",
                            value=date.fromisoformat(t["move_in_date"]) if t.get("move_in_date") else date.today(),
                        )
                        col_save, col_cancel = st.columns(2)
                        save_clicked = col_save.form_submit_button("Save changes", type="primary")
                        cancel_clicked = col_cancel.form_submit_button("Cancel")

                        if save_clicked:
                            if not require_active_subscription():
                                pass
                            elif not e_full_name.strip():
                                st.error("Full name is required.")
                            else:
                                update_tenant(
                                    t["id"], e_full_name.strip(), e_phone.strip(),
                                    e_email.strip(), e_id_number.strip(), e_move_in.isoformat(),
                                )
                                st.session_state[edit_mode_key] = False
                                st.success("Tenant details updated.")
                                st.rerun()
                        if cancel_clicked:
                            st.session_state[edit_mode_key] = False
                            st.rerun()
                else:
                    if st.button("✏️ Edit tenant info", key=f"edit_btn_{t['id']}"):
                        st.session_state[edit_mode_key] = True
                        st.rerun()

                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Phone:** {t['phone'] or '—'}")
                    st.write(f"**Email:** {t['email'] or '—'}")
                    st.write(f"**ID/Passport number:** {t.get('id_number') or '—'}")
                with col2:
                    st.write(f"**Move-in:** {t['move_in_date'] or '—'}")
                    st.write(f"**Move-out:** {t['move_out_date'] or '—'}")
                    st.write(f"**Monthly rent:** {currency} {t['monthly_rent']:,.0f}")

                if t.get("id_document_path"):
                    st.write("**ID document on file:**")
                    doc_path = t["id_document_path"]
                    if doc_path.lower().endswith((".png", ".jpg", ".jpeg")):
                        st.image(doc_path, width=300)
                    else:
                        with open(doc_path, "rb") as f:
                            st.download_button(
                                "📄 Download ID document", f,
                                file_name=doc_path.split("/")[-1],
                                key=f"iddoc_{t['id']}",
                            )
                else:
                    uploaded = st.file_uploader(
                        "Attach ID/Passport photo", type=["png", "jpg", "jpeg", "pdf"],
                        key=f"upload_id_{t['id']}",
                    )
                    if uploaded is not None:
                        path = save_tenant_id_document(t["id"], uploaded)
                        update_tenant_id_document(t["id"], path)
                        st.success("ID document attached.")
                        st.rerun()

                st.write(f"**Total charged:** {currency} {bal['total_charged']:,.0f}")
                st.write(f"**Total paid:** {currency} {bal['total_paid']:,.0f}")
                st.write(f"**Balance:** {currency} {bal['balance']:,.0f} ({bal['balance_status']})")

                if t["status"] == "active":
                    if st.button("Mark as vacated", key=f"vacate_{t['id']}"):
                        vacate_tenant(t["id"])
                        st.warning(f"{t['full_name']} marked as vacated. Unit is now vacant.")
                        st.rerun()
