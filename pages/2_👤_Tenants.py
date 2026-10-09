import streamlit as st
from datetime import date
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.i18n import t
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

account_id = get_current_account_id()
currency = (get_account(account_id) or {}).get("currency", "UGX")

page_header(t("Tenants"), icon="👤")
subscription_banner()
st.write("")

DIAL_CODES = [
    ("🇺🇬 UG  +256", "+256"), ("🇰🇪 KE  +254", "+254"), ("🇹🇿 TZ  +255", "+255"),
    ("🇷🇼 RW  +250", "+250"), ("🇧🇮 BI  +257", "+257"), ("🇸🇸 SS  +211", "+211"),
    ("🇨🇩 CD  +243", "+243"), ("🇸🇴 SO  +252", "+252"), ("🇪🇹 ET  +251", "+251"),
    ("🇸🇩 SD  +249", "+249"), ("🇩🇯 DJ  +253", "+253"), ("🇪🇷 ER  +291", "+291"),
    ("🇳🇬 NG  +234", "+234"), ("🇬🇭 GH  +233", "+233"), ("🇸🇳 SN  +221", "+221"),
    ("🇨🇮 CI  +225", "+225"), ("🇧🇫 BF  +226", "+226"), ("🇲🇱 ML  +223", "+223"),
    ("🇳🇪 NE  +227", "+227"), ("🇹🇩 TD  +235", "+235"), ("🇧🇯 BJ  +229", "+229"),
    ("🇹🇬 TG  +228", "+228"), ("🇬🇳 GN  +224", "+224"), ("🇸🇱 SL  +232", "+232"),
    ("🇱🇷 LR  +231", "+231"), ("🇬🇲 GM  +220", "+220"), ("🇨🇲 CM  +237", "+237"),
    ("🇿🇦 ZA  +27",  "+27"),  ("🇿🇼 ZW  +263", "+263"), ("🇿🇲 ZM  +260", "+260"),
    ("🇲🇿 MZ  +258", "+258"), ("🇲🇼 MW  +265", "+265"), ("🇧🇼 BW  +267", "+267"),
    ("🇳🇦 NA  +264", "+264"), ("🇦🇴 AO  +244", "+244"), ("🇸🇿 SZ  +268", "+268"),
    ("🇱🇸 LS  +266", "+266"), ("🇪🇬 EG  +20",  "+20"),  ("🇱🇾 LY  +218", "+218"),
    ("🇹🇳 TN  +216", "+216"), ("🇩🇿 DZ  +213", "+213"), ("🇲🇦 MA  +212", "+212"),
    ("🇲🇬 MG  +261", "+261"), ("🇲🇺 MU  +230", "+230"), ("🇸🇨 SC  +248", "+248"),
    ("🇬🇧 GB  +44",  "+44"),  ("🇩🇪 DE  +49",  "+49"),  ("🇫🇷 FR  +33",  "+33"),
    ("🇮🇹 IT  +39",  "+39"),  ("🇪🇸 ES  +34",  "+34"),  ("🇵🇹 PT  +351", "+351"),
    ("🇺🇸 US  +1",   "+1"),   ("🇨🇦 CA  +1",   "+1"),
    ("🇮🇳 IN  +91",  "+91"),  ("🇨🇳 CN  +86",  "+86"),  ("🇯🇵 JP  +81",  "+81"),
    ("🇸🇦 SA  +966", "+966"), ("🇦🇪 AE  +971", "+971"), ("🇹🇷 TR  +90",  "+90"),
    ("🇦🇺 AU  +61",  "+61"),  ("🇳🇿 NZ  +64",  "+64"),
    ("Other", ""),
]
code_labels = [l for l, _ in DIAL_CODES]
code_values = {l: c for l, c in DIAL_CODES}

tab1, tab2 = st.tabs([t("Add tenant"), t("All tenants")])

with tab1:
    vacant_units = [u for u in list_units(account_id=account_id) if u["status"] == "vacant"]
    if not vacant_units:
        empty_state(t("No vacant units available. Add a unit first, or vacate an existing tenant."), icon="🚪")
    else:
        with st.form("add_tenant_form", clear_on_submit=True):
            unit_options = {f"{u['property_name']} — {u['unit_name']} ({currency} {u['monthly_rent']:,.0f}/mo)": u["id"]
                             for u in vacant_units}
            unit_label = st.selectbox(t("Unit*"), list(unit_options.keys()))
            full_name = st.text_input(t("Full name*"))
            st.markdown(f"**{t('Phone number')}**")
            pc1, pc2 = st.columns([1, 2])
            with pc1:
                dial_label = st.selectbox(t("Country code"), code_labels, index=0, label_visibility="collapsed")
            with pc2:
                phone_local = st.text_input(t("Phone number"), placeholder="701 234 567", label_visibility="collapsed")
            phone = (code_values[dial_label] + phone_local.strip()).strip()
            email = st.text_input(t("Email"))
            st.markdown(f"**{t('Identification')}**")
            st.caption(t("Record either a National ID or Passport number, and optionally attach a photo of the document."))
            id_number = st.text_input(t("National ID number or Passport number"))
            id_photo = st.file_uploader(t("ID/Passport document (photo or PDF, optional)"), type=["png", "jpg", "jpeg", "pdf"])
            move_in_date = st.date_input(t("Move-in date"))
            submitted = st.form_submit_button(t("Add tenant"))
            if submitted:
                if not require_active_subscription():
                    pass
                elif not full_name.strip():
                    st.error(t("Full name is required."))
                else:
                    tenant_id = add_tenant(
                        unit_options[unit_label], full_name.strip(), phone.strip(),
                        email.strip(), id_number.strip(), "", move_in_date.isoformat(),
                    )
                    if id_photo is not None:
                        path = save_tenant_id_document(tenant_id, id_photo)
                        update_tenant_id_document(tenant_id, path)
                    st.success(t("Added tenant") + f" '{full_name}'.")
                    st.rerun()

with tab2:
    status_filter = st.radio(t("Show"), ["active", "vacated", "all"], horizontal=True)
    tenants = list_tenants(status=None if status_filter == "all" else status_filter, account_id=account_id)

    if not tenants:
        empty_state(t("No tenants found."), icon="👤")
    else:
        for ten in tenants:
            bal = tenant_balance(ten["id"])
            with st.expander(
                f"{ten['full_name']} — {ten['property_name']} / {ten['unit_name']} "
                f"({ten['status']}, {t('balance')}: {currency} {bal['balance']:,.0f})"
            ):
                edit_mode_key = f"editing_{ten['id']}"
                if st.session_state.get(edit_mode_key):
                    with st.form(f"edit_tenant_form_{ten['id']}"):
                        e_full_name = st.text_input(t("Full name*"), value=ten["full_name"])
                        st.markdown(f"**{t('Phone number')}**")
                        existing_phone = ten["phone"] or ""
                        default_code_idx = 0
                        for idx, (lbl, code) in enumerate(DIAL_CODES):
                            if code and existing_phone.startswith(code):
                                default_code_idx = idx
                                break
                        ec1, ec2 = st.columns([1, 2])
                        with ec1:
                            e_dial_label = st.selectbox(t("Code"), code_labels, index=default_code_idx,
                                                         label_visibility="collapsed", key=f"ecode_{ten['id']}")
                        with ec2:
                            e_dial_code = code_values[e_dial_label]
                            local_part = existing_phone[len(e_dial_code):] if e_dial_code and existing_phone.startswith(e_dial_code) else existing_phone
                            e_phone_local = st.text_input(t("Number"), value=local_part,
                                                           label_visibility="collapsed", key=f"ephone_{ten['id']}")
                        e_phone = (e_dial_code + e_phone_local.strip()).strip()
                        e_email = st.text_input(t("Email"), value=ten["email"] or "")
                        e_id_number = st.text_input(t("National ID number or Passport number"), value=ten.get("id_number") or "")
                        e_move_in = st.date_input(t("Move-in date"),
                            value=date.fromisoformat(ten["move_in_date"]) if ten.get("move_in_date") else date.today())
                        col_save, col_cancel = st.columns(2)
                        save_clicked = col_save.form_submit_button(t("Save changes"), type="primary")
                        cancel_clicked = col_cancel.form_submit_button(t("Cancel"))
                        if save_clicked:
                            if not require_active_subscription():
                                pass
                            elif not e_full_name.strip():
                                st.error(t("Full name is required."))
                            else:
                                update_tenant(ten["id"], e_full_name.strip(), e_phone.strip(),
                                              e_email.strip(), e_id_number.strip(), e_move_in.isoformat())
                                st.session_state[edit_mode_key] = False
                                st.success(t("Tenant details updated."))
                                st.rerun()
                        if cancel_clicked:
                            st.session_state[edit_mode_key] = False
                            st.rerun()
                else:
                    if st.button(f"✏️ {t('Edit tenant info')}", key=f"edit_btn_{ten['id']}"):
                        st.session_state[edit_mode_key] = True
                        st.rerun()

                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**{t('Phone')}:** {ten['phone'] or '—'}")
                    st.write(f"**{t('Email')}:** {ten['email'] or '—'}")
                    st.write(f"**{t('ID/Passport number')}:** {ten.get('id_number') or '—'}")
                with col2:
                    st.write(f"**{t('Move-in')}:** {ten['move_in_date'] or '—'}")
                    st.write(f"**{t('Move-out')}:** {ten['move_out_date'] or '—'}")
                    st.write(f"**{t('Monthly rent')}:** {currency} {ten['monthly_rent']:,.0f}")

                if ten.get("id_document_path"):
                    st.write(f"**{t('ID/Passport document on file')}:**")
                    doc_path = ten["id_document_path"]
                    if doc_path.lower().endswith((".png", ".jpg", ".jpeg")):
                        st.image(doc_path, width=300)
                    else:
                        with open(doc_path, "rb") as f:
                            st.download_button(f"📄 {t('Download ID document')}", f,
                                file_name=doc_path.split("/")[-1], key=f"iddoc_{ten['id']}")
                else:
                    uploaded = st.file_uploader(t("Attach ID/Passport document (photo or PDF)"),
                        type=["png", "jpg", "jpeg", "pdf"], key=f"upload_id_{ten['id']}")
                    if uploaded is not None:
                        path = save_tenant_id_document(ten["id"], uploaded)
                        update_tenant_id_document(ten["id"], path)
                        st.success(t("ID document attached."))
                        st.rerun()

                st.write(f"**{t('Total charged')}:** {currency} {bal['total_charged']:,.0f}")
                st.write(f"**{t('Total paid')}:** {currency} {bal['total_paid']:,.0f}")
                st.write(f"**{t('Balance')}:** {currency} {bal['balance']:,.0f} ({t(bal['balance_status'].title())})")

                if ten["status"] == "active":
                    if st.button(t("Mark as vacated"), key=f"vacate_{ten['id']}"):
                        vacate_tenant(ten["id"])
                        st.warning(f"{ten['full_name']} {t('marked as vacated. Unit is now vacant.')}")
                        st.rerun()
