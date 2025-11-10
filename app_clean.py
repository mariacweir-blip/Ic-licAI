# app_clean.py — IC-LicAI Expert Console (licensing-first, DOCX/XLSX/JSON exports)
import io
import json
from datetime import date
from pathlib import Path
import streamlit as st

from ic_licai.exporters_clean import (
    export_advisory_docx,
    export_ia_register_xlsx,
    export_case_json,
)

# ---- Page + Session ----
st.set_page_config(page_title="IC-LicAI Expert Console", layout="centered")
ss = st.session_state

# Safe defaults so the page never breaks if forms not submitted yet
ss.setdefault("case_name", "Untitled Case")
ss.setdefault("company_size", "Micro (1–10)")
ss.setdefault("sector", "Other")
ss.setdefault("notes", "")
ss.setdefault("uploaded_names", [])
ss.setdefault("four_leaf_human", "")
ss.setdefault("four_leaf_structural", "")
ss.setdefault("four_leaf_customer", "")
ss.setdefault("four_leaf_strategic", "")
ss.setdefault("intent_text", "")
ss.setdefault("frand_notes", "")
ss.setdefault("analysis_locked", False)
ss.setdefault("case_bundle", {})  # the object we use for exports

# ---- UI constants (ASCII only) ----
SIZES = [
    "Micro (1–10)",
    "Small (11–50)",
    "Medium (51–250)",
    "Large (250+)",
]

SECTORS = [
    "Food & Beverage", "MedTech", "GreenTech", "AgriTech", "Biotech",
    "Software/SaaS", "FinTech", "EdTech", "Manufacturing", "Creative/Digital",
    "Professional Services", "Mobility/Transport", "Energy", "Other",
]

# ---- Sidebar Navigation ----
st.sidebar.title("IC-LicAI")
page = st.sidebar.radio(
    "Navigate",
    ["Case", "Checklist", "Analysis", "Reports"],
    index=0,
    key="nav",
)

def _build_case_bundle_from_session() -> dict:
    """Create a simple case bundle structure consumed by exporters_clean."""
    ten_steps = [
        {"label": "1. Identify", "notes": ""},
        {"label": "2. Separate", "notes": ""},
        {"label": "3. Protect", "notes": ""},
        {"label": "4. Safeguard", "notes": ""},
        {"label": "5. Manage", "notes": ""},
        {"label": "6. Control", "notes": ""},
        {"label": "7. Evidence", "notes": ""},
        {"label": "8. Governance", "notes": ""},
        {"label": "9. Monetise", "notes": ""},
        {"label": "10. Reassess", "notes": ""},
    ]
    bundle = {
        "case_name": ss.get("case_name", "Untitled Case"),
        "company_size": ss.get("company_size", "Micro (1–10)"),
        "sector": ss.get("sector", "Other"),
        "notes": ss.get("notes", ""),
        "uploaded_names": ss.get("uploaded_names", []),
        "four_leaf": {
            "human": ss.get("four_leaf_human", ""),
            "structural": ss.get("four_leaf_structural", ""),
            "customer": ss.get("four_leaf_customer", ""),
            "strategic": ss.get("four_leaf_strategic", ""),
        },
        "ten_steps": ten_steps,
        "licensing": {
            "intent": ss.get("intent_text", ""),
            "frand_notes": ss.get("frand_notes", ""),
        },
        # You can wire ESG mapping later. Keep flag for exporters.
        "esg_rows": 0,
    }
    return bundle


# =========================
# Page: Case
# =========================
if page == "Case":
    st.header("Case details")
    with st.form("case_form"):
        c1, c2 = st.columns(2)
        with c1:
            case_name = st.text_input("Case / Company name", value=ss["case_name"])
            company_size = st.selectbox("Company size", SIZES, index=SIZES.index(ss["company_size"]))
        with c2:
            sector = st.selectbox("Sector", SECTORS, index=SECTORS.index(ss["sector"]))
            notes = st.text_area("Quick notes (optional)", value=ss["notes"], height=100)

        uploads = st.file_uploader(
            "Upload evidence (optional)",
            type=["pdf", "docx", "txt", "csv", "xlsx", "pptx", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="uploader",
        )
# --- Evidence importer & auto-analysis ---
from ic_licai.importers import combine_uploads

if uploads:
    st.success(f"{len(uploads)} evidence files uploaded.")
    combined_text = combine_uploads(uploads)
    st.session_state["combined_text"] = combined_text

    if st.checkbox("Preview extracted text", key="preview_text"):
        st.text_area("Extracted Evidence (first 5000 chars):",
                     combined_text[:5000],
                     height=300)

    # Simple auto-analyzer placeholder (4-Leaf + 10-Steps tags)
    if st.button("🔍 Run Auto-Analysis", key="btn_analyze"):
        st.session_state["analysis_result"] = {
            "4_leaf": {
                "Human Capital": "Detected references to training, leadership, and R&D staff.",
                "Structural Capital": "Detected references to process documentation or patents.",
                "Customer Capital": "Mentions of contracts, clients, or partnerships.",
                "Strategic Alliance Capital": "Mentions of collaborations, co-development, or clusters."
            },
            "10_steps_summary": "Initial mapping complete. Ready for expert verification."
        }
        st.success("✅ Auto-Analysis complete. Go to Checklist to verify details.")
else:
    st.info("Upload Pitch Decks, WhatsApp .txt exports, or other relevant evidence files before running analysis.")
        submitted = st.form_submit_button("Save case")
        if submitted:
            ss["case_name"] = case_name or "Untitled Case"
            ss["company_size"] = company_size
            ss["sector"] = sector
            ss["notes"] = notes or ""
            ss["uploaded_names"] = [f.name for f in uploads] if uploads else []
            st.success("Saved case details.")

    st.info("Proceed to Checklist to guide your expert discovery, then to Analysis to assemble the narrative and exports.")


# =========================
# Page: Checklist (on-screen only)
# =========================
elif page == "Checklist":
    st.header("Expert Checklist (guide only)")
    with st.expander("Four-Leaf Model"):
        ss["four_leaf_human"] = st.text_area("Human Capital: roles, skills, know-how, training materials", value=ss["four_leaf_human"])
        ss["four_leaf_structural"] = st.text_area("Structural Capital: processes, software, data, methods", value=ss["four_leaf_structural"])
        ss["four_leaf_customer"] = st.text_area("Customer Capital: contracts, testimonials, brand assets", value=ss["four_leaf_customer"])
        ss["four_leaf_strategic"] = st.text_area("Strategic Alliance Capital: partnerships, JV, licences", value=ss["four_leaf_strategic"])

    with st.expander("Licensing Intent and FRAND"):
        ss["intent_text"] = st.text_area("Licensing intent (target markets, geographies, model)", value=ss["intent_text"])
        ss["frand_notes"] = st.text_area("FRAND notes (fee corridor, audit, MFN, termination)", value=ss["frand_notes"])

    st.info("When ready, go to Analysis and click Build Narrative Preview.")


# =========================
# Page: Analysis (preview + lock)
# =========================
elif page == "Analysis":
    st.header("Analysis and Narrative Preview")
    st.write("This builds a simple advisory narrative and bundles data for exports.")

    if st.button("Build Narrative Preview", key="btn_build"):
        bundle = _build_case_bundle_from_session()
        ss["case_bundle"] = bundle
        ss["analysis_locked"] = True

        # Very simple narrative for now
        narrative = (
            f"{bundle['case_name']} is a {bundle['company_size']} in {bundle['sector']}. "
            f"Focus areas:\n"
            f"- Human: {bundle['four_leaf']['human'] or 'TBD'}\n"
            f"- Structural: {bundle['four_leaf']['structural'] or 'TBD'}\n"
            f"- Customer: {bundle['four_leaf']['customer'] or 'TBD'}\n"
            f"- Strategic Alliance: {bundle['four_leaf']['strategic'] or 'TBD'}\n\n"
            f"Licensing intent: {bundle['licensing']['intent'] or 'TBD'}\n"
            f"FRAND notes: {bundle['licensing']['frand_notes'] or 'TBD'}\n"
        )
        ss["narrative"] = narrative

    if ss.get("analysis_locked"):
        st.subheader("Preview")
        st.text_area("Narrative (copyable)", value=ss.get("narrative", ""), height=220, key="narrative_preview")
        st.success("Analysis locked. Go to Reports to generate files.")

    else:
        st.warning("Build the narrative to lock analysis before exporting.")


# =========================
# Page: Reports (exports)
# =========================
elif page == "Reports":
    st.header("Reports and Templates")

    if not ss.get("analysis_locked") or not ss.get("case_bundle"):
        st.warning("No locked analysis found. Go to Analysis and click Build Narrative Preview.")
    else:
        bundle = ss["case_bundle"]

        st.subheader("Generate advisory and data files")
        c1, c2, c3 = st.columns(3)

        # Advisory DOCX
        with c1:
            try:
                b, path_str = export_advisory_docx(bundle, mode="ADVISORY")
                st.download_button(
                    "Download Advisory (DOCX)",
                    data=b, file_name=f"Advisory_{bundle['case_name']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="dl_docx"
                )
                st.caption(f"Saved to: {path_str}")
            except Exception as e:
                st.error(f"Advisory export failed: {e}")

        # IA Register XLSX
        with c2:
            try:
                b, path_str = export_ia_register_xlsx(bundle)
                st.download_button(
                    "Download IA Register (XLSX)",
                    data=b, file_name=f"IA_Register_{bundle['case_name']}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_xlsx"
                )
                st.caption(f"Saved to: {path_str}")
            except Exception as e:
                st.error(f"IA Register export failed: {e}")

        # Case JSON
        with c3:
            try:
                b, path_str = export_case_json(bundle)
                st.download_button(
                    "Download Case (JSON)",
                    data=b, file_name=f"Case_{bundle['case_name']}.json",
                    mime="application/json",
                    key="dl_json"
                )
                st.caption(f"Saved to: {path_str}")
            except Exception as e:
                st.error(f"JSON export failed: {e}")

        st.subheader("Licensing templates")
        t1, t2, t3 = st.columns(3)

        with t1:
            try:
                b, path_str = export_advisory_docx(bundle, mode="TEMPLATE_FRAND")
                st.download_button(
                    "Template FRAND (DOCX)",
                    data=b, file_name=f"Template_FRAND_{bundle['case_name']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="dl_tpl_frand"
                )
                st.caption(f"Saved to: {path_str}")
            except Exception as e:
                st.error(f"FRAND template failed: {e}")

        with t2:
            try:
                b, path_str = export_advisory_docx(bundle, mode="TEMPLATE_CO_CREATION")
                st.download_button(
                    "Template Co-creation (DOCX)",
                    data=b, file_name=f"Template_CoCreation_{bundle['case_name']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="dl_tpl_cocreate"
                )
                st.caption(f"Saved to: {path_str}")
            except Exception as e:
                st.error(f"Co-creation template failed: {e}")

        with t3:
            try:
                b, path_str = export_advisory_docx(bundle, mode="TEMPLATE_NON_TRADITIONAL")
                st.download_button(
                    "Template Non-traditional (DOCX)",
                    data=b, file_name=f"Template_NonTraditional_{bundle['case_name']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="dl_tpl_nontrad"
                )
                st.caption(f"Saved to: {path_str}")
            except Exception as e:
                st.error(f"Non-traditional template failed: {e}"). 
