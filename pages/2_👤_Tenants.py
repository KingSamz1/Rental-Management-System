import streamlit as st
from datetime import date
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
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

page_header("Tenants", icon="👤")
subscription_banner()
st.write("")

tab1, tab2 = st.tabs(["Add tenant", "All tenants"])

with tab1:
    vacant_units = [u for u in list_units(account_id=account_id) if u["status"] == "vacant"]
    if not vacant_units:
        empty_state("No vacant units available. Add a unit first, or vacate an existing tenant.", icon="🚪")
    else:
        with st.form("add_tenant_form", clear_on_submit=True):
            unit_options = {f"{u['property_name']} — {u['unit_name']} ({currency} {u['monthly_rent']:,.0f}/mo)": u["id"]
                             for u in vacant_units}
            unit_label = st.selectbox("Unit*", list(unit_options.keys()))
            full_name = st.text_input("Full name*")

            st.markdown("**Phone number**")
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
                ("🇱🇷 LR  +231", "+231"), ("🇬🇲 GM  +220", "+220"), ("🇬🇼 GW  +245", "+245"),
                ("🇨🇻 CV  +238", "+238"), ("🇲🇷 MR  +222", "+222"), ("🇨🇲 CM  +237", "+237"),
                # Southern & Central Africa
                ("🇿🇦 ZA  +27",  "+27"),  ("🇿🇼 ZW  +263", "+263"), ("🇿🇲 ZM  +260", "+260"),
                ("🇲🇿 MZ  +258", "+258"), ("🇲🇼 MW  +265", "+265"), ("🇧🇼 BW  +267", "+267"),
                ("🇳🇦 NA  +264", "+264"), ("🇦🇴 AO  +244", "+244"), ("🇨🇫 CF  +236", "+236"),
                ("🇬🇶 GQ  +240", "+240"), ("🇬🇦 GA  +241", "+241"), ("🇨🇬 CG  +242", "+242"),
                ("🇸🇿 SZ  +268", "+268"), ("🇱🇸 LS  +266", "+266"), ("🇰🇲 KM  +269", "+269"),
                # North Africa
                ("🇪🇬 EG  +20",  "+20"),  ("🇱🇾 LY  +218", "+218"), ("🇹🇳 TN  +216", "+216"),
                ("🇩🇿 DZ  +213", "+213"), ("🇲🇦 MA  +212", "+212"),
                # Indian Ocean Africa
                ("🇲🇬 MG  +261", "+261"), ("🇲🇺 MU  +230", "+230"), ("🇸🇨 SC  +248", "+248"),
                # Europe
                ("🇬🇧 GB  +44",  "+44"),  ("🇩🇪 DE  +49",  "+49"),  ("🇫🇷 FR  +33",  "+33"),
                ("🇮🇹 IT  +39",  "+39"),  ("🇪🇸 ES  +34",  "+34"),  ("🇳🇱 NL  +31",  "+31"),
                ("🇧🇪 BE  +32",  "+32"),  ("🇨🇭 CH  +41",  "+41"),  ("🇵🇹 PT  +351", "+351"),
                ("🇸🇪 SE  +46",  "+46"),  ("🇳🇴 NO  +47",  "+47"),  ("🇩🇰 DK  +45",  "+45"),
                ("🇫🇮 FI  +358", "+358"),
                # North America
                ("🇺🇸 US  +1",   "+1"),   ("🇨🇦 CA  +1",   "+1"),
                # Middle East & Asia
                ("🇮🇳 IN  +91",  "+91"),  ("🇵🇰 PK  +92",  "+92"),  ("🇧🇩 BD  +880", "+880"),
                ("🇨🇳 CN  +86",  "+86"),  ("🇯🇵 JP  +81",  "+81"),  ("🇸🇦 SA  +966", "+966"),
                ("🇦🇪 AE  +971", "+971"), ("🇶🇦 QA  +974", "+974"), ("🇴🇲 OM  +968", "+968"),
                ("🇰🇼 KW  +965", "+965"), ("🇧🇭 BH  +973", "+973"), ("🇮🇱 IL  +972", "+972"),
                ("🇯🇴 JO  +962", "+962"), ("🇱🇧 LB  +961", "+961"), ("🇾🇪 YE  +967", "+967"),
                ("🇮🇷 IR  +98",  "+98"),  ("🇹🇷 TR  +90",  "+90"),
                # Oceania
                ("🇦🇺 AU  +61",  "+61"),  ("🇳🇿 NZ  +64",  "+64"),
                ("Other", ""),
            ]
            code_labels = [label for label, _ in DIAL_CODES]
            code_values = {label: code for label, code in DIAL_CODES}
            pc1, pc2 = st.columns([1, 2])
            with pc1:
                dial_label = st.selectbox("Country code", code_labels, index=0, label_visibility="collapsed")
            with pc2:
                phone_local = st.text_input("Phone number", placeholder="701 234 567", label_visibility="collapsed")
            dial_code = code_values[dial_label]
            phone = (dial_code + phone_local.strip()).strip()

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
                "ID/Passport document (photo or PDF, optional)",
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
    tenants = list_tenants(status=None if status_filter == "all" else status_filter, account_id=account_id)

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
                        st.markdown("**Phone number**")
                        DIAL_CODES_E = [
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
                            ("🇱🇷 LR  +231", "+231"), ("🇬🇲 GM  +220", "+220"), ("🇬🇼 GW  +245", "+245"),
                            ("🇨🇻 CV  +238", "+238"), ("🇲🇷 MR  +222", "+222"), ("🇨🇲 CM  +237", "+237"),
                            # Southern & Central Africa
                            ("🇿🇦 ZA  +27",  "+27"),  ("🇿🇼 ZW  +263", "+263"), ("🇿🇲 ZM  +260", "+260"),
                            ("🇲🇿 MZ  +258", "+258"), ("🇲🇼 MW  +265", "+265"), ("🇧🇼 BW  +267", "+267"),
                            ("🇳🇦 NA  +264", "+264"), ("🇦🇴 AO  +244", "+244"), ("🇨🇫 CF  +236", "+236"),
                            ("🇬🇶 GQ  +240", "+240"), ("🇬🇦 GA  +241", "+241"), ("🇨🇬 CG  +242", "+242"),
                            ("🇸🇿 SZ  +268", "+268"), ("🇱🇸 LS  +266", "+266"), ("🇰🇲 KM  +269", "+269"),
                            # North Africa
                            ("🇪🇬 EG  +20",  "+20"),  ("🇱🇾 LY  +218", "+218"), ("🇹🇳 TN  +216", "+216"),
                            ("🇩🇿 DZ  +213", "+213"), ("🇲🇦 MA  +212", "+212"),
                            # Indian Ocean Africa
                            ("🇲🇬 MG  +261", "+261"), ("🇲🇺 MU  +230", "+230"), ("🇸🇨 SC  +248", "+248"),
                            # Europe
                            ("🇬🇧 GB  +44",  "+44"),  ("🇩🇪 DE  +49",  "+49"),  ("🇫🇷 FR  +33",  "+33"),
                            ("🇮🇹 IT  +39",  "+39"),  ("🇪🇸 ES  +34",  "+34"),  ("🇳🇱 NL  +31",  "+31"),
                            ("🇧🇪 BE  +32",  "+32"),  ("🇨🇭 CH  +41",  "+41"),  ("🇵🇹 PT  +351", "+351"),
                            ("🇸🇪 SE  +46",  "+46"),  ("🇳🇴 NO  +47",  "+47"),  ("🇩🇰 DK  +45",  "+45"),
                            ("🇫🇮 FI  +358", "+358"),
                            # North America
                            ("🇺🇸 US  +1",   "+1"),   ("🇨🇦 CA  +1",   "+1"),
                            # Middle East & Asia
                            ("🇮🇳 IN  +91",  "+91"),  ("🇵🇰 PK  +92",  "+92"),  ("🇧🇩 BD  +880", "+880"),
                            ("🇨🇳 CN  +86",  "+86"),  ("🇯🇵 JP  +81",  "+81"),  ("🇸🇦 SA  +966", "+966"),
                            ("🇦🇪 AE  +971", "+971"), ("🇶🇦 QA  +974", "+974"), ("🇴🇲 OM  +968", "+968"),
                            ("🇰🇼 KW  +965", "+965"), ("🇧🇭 BH  +973", "+973"), ("🇮🇱 IL  +972", "+972"),
                            ("🇯🇴 JO  +962", "+962"), ("🇱🇧 LB  +961", "+961"), ("🇾🇪 YE  +967", "+967"),
                            ("🇮🇷 IR  +98",  "+98"),  ("🇹🇷 TR  +90",  "+90"),
                            # Oceania
                            ("🇦🇺 AU  +61",  "+61"),  ("🇳🇿 NZ  +64",  "+64"),
                            ("Other", ""),
                        ]
                        existing_phone = t["phone"] or ""
                        # Try to pre-select dial code from stored phone
                        default_code_idx = 0
                        for idx, (lbl, code) in enumerate(DIAL_CODES_E):
                            if code and existing_phone.startswith(code):
                                default_code_idx = idx
                                break
                        ec1, ec2 = st.columns([1, 2])
                        with ec1:
                            e_dial_label = st.selectbox("Code", [l for l, _ in DIAL_CODES_E],
                                                         index=default_code_idx, label_visibility="collapsed",
                                                         key=f"ecode_{t['id']}")
                        with ec2:
                            e_dial_code = {l: c for l, c in DIAL_CODES_E}[e_dial_label]
                            local_part = existing_phone[len(e_dial_code):] if e_dial_code and existing_phone.startswith(e_dial_code) else existing_phone
                            e_phone_local = st.text_input("Number", value=local_part,
                                                           label_visibility="collapsed", key=f"ephone_{t['id']}")
                        e_phone = (e_dial_code + e_phone_local.strip()).strip()
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
                    st.write("**ID/Passport document on file:**")
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
                        "Attach ID/Passport document (photo or PDF)", type=["png", "jpg", "jpeg", "pdf"],
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
