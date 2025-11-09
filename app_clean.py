# app_clean.py — IC-LicAI Expert Console (clean version)
import io
import json
from datetime import date
from pathlib import Path

import streamlit as st

# exporters (using ic_licai/exporters_clean.py for latest stable exports)
from ic_licai.exporters_clean import export_pdf, export_xlsx, export_json

# --- Page setup ---
st.set_page_config(page_title="IC-LicAI Expert Console", layout="centered")
ss = st.session_state

# --- Safe defaults (prevent page crashes before analysis) ---
ss.setdefault("case_name", "Untitled Case")
ss.setdefault("company_size", "Micro (1–10)")
ss.setdefault("sector", "")
ss.setdefault("notes", "")
ss.setdefault("assessment", {})  # placeholder if analyzer not yet wired


# --- UI constants ---
SECTORS = [
    "Food & Beverage", "MedTech", "GreenTech", "AgriTech", "Biotech",
    "Software/SaaS", "FinTech", "EdTech", "Manufacturing", "Creative/Digital",
    "Professional Services", "Mobility/Transport", "Energy", "Other",
]
COMPANY_SIZES = ["Micro (1–10)", "Small (11–50)", "Medium (51–250)", "Large (250+)"]


# --- Company Info Form ---
st.header("Case Information")

with st.form("case_info_form"):
    ss["case_name"] = st.text_input("Case / Company name", value=ss.get("case_name", "Untitled Case"))
    ss["company_size"] = st.selectbox(
        "Company size",
        ["Micro (1–10)", "Small (11–50)", "Medium (51–250)", "Large (250+)"],
        index=["Micro (1–10)", "Small (11–50)", "Medium (51–250)", "Large (250+)"].index(ss.get("company_size", "Micro (1–10)"))
    )
    ss["sector"] = st.text_input("Sector / Industry", value=ss.get("sector", ""))
    ss["notes"] = st.text_area("Notes or description", value=ss.get("notes", ""), height=120)
    
    submitted = st.form_submit_button("Save details")
    if submitted:
        st.success(f"Case details saved for: {ss['case_name']} ({ss['company_size']})")

# --- Page setup ---
st.set_page_config(page_title="IC-LicAI Demo", layout="centered")
st.title("IC-LicAI Expert Console")
st.caption("Upload → Guide → Advisory → Exports (licensing-first, human-in-the-loop)")

ss = st.session_state

# --- Case capture (safe form with defaults) ---
default_sector_idx = ss.get("sector_idx", 0)
default_size_idx = ss.get("size_idx", 0)

with st.form("case_form"):
    col1, col2 = st.columns([2, 1])
    with col1:
        case_name = st.text_input("Company name *", ss.get("case_name", "Sandy Beach Foods Ltd."))
    with col2:
        size_sel = st.selectbox("Company size *", COMPANY_SIZES, index=default_size_idx, key="size_select")

    sector_sel = st.selectbox("Sector *", SECTORS, index=default_sector_idx, key="sector_select")
    notes = st.text_area("Notes / elevator pitch", ss.get("notes", ""), height=120)

    saved = st.form_submit_button("Save Case Details")

if saved:
    ss["case_name"] = (case_name or "").strip() or "Client"
    ss["sector_idx"] = SECTORS.index(sector_sel) if sector_sel in SECTORS else 0
    ss["size_idx"] = COMPANY_SIZES.index(size_sel) if size_sel in COMPANY_SIZES else 0
    ss["notes"] = notes or ""
    ss["case_state"] = {
        "name": ss["case_name"],
        "sector": SECTORS[ss["sector_idx"]],
        "company_size": COMPANY_SIZES[ss["size_idx"]],
        "notes": ss["notes"],
    }
    st.success("✅ Case details saved. You can proceed to Exports for a demo.")

# --- Safe analysis placeholders (so nothing crashes) ---
analysis = ss.get("analysis", {})
assessment = analysis.get("assessment", {})
ic_map = assessment.get("ic_map", {
    "Human Capital": ["Founder expertise", "Training notes"],
    "Customer Capital": ["Repeat buyers", "Partner restaurants"],
})
readiness = assessment.get("readiness", [
    {"step": "1", "name": "Identify", "score": 2, "tasks": ["List key artefacts", "Owner sign-off"]},
    {"step": "2", "name": "Separate", "score": 1, "tasks": ["Recipes vs brand", "Access rules"]},
])

# --- Narrative and licensing (safe defaults) ---
narrative = ss.get("narrative", "Advisory: focus on simple, FRAND-ready licensing with quick first revenue.")
licensing_options = ss.get("licensing", [
    {"model": "Fixed-fee starter licence", "notes": ["6–12 months term", "Uniform terms", "Audit on request"]},
    {"model": "Simple royalty licence", "notes": ["2% of net sales", "Annual cap", "MFN across micro licensees"]},
    {"model": "Co-creation licence", "notes": ["Shared IP", "Field of use", "Pre-agreed conversion path"]},
])

# --- Build bundle safely ---
case_dict = ss.get("case_state", {
    "name": "Client",
    "sector": SECTORS[0],
    "company_size": COMPANY_SIZES[0],
    "notes": ss.get("notes", ""),
})
case = case_dict.get("name", "Client")

bundle = {
    "case": case,
    "sector": case_dict["sector"],
    "company_size": case_dict["company_size"],
    "summary": case_dict["notes"],
    "ic_map": ic_map,
    "readiness": readiness,
    "licensing": licensing_options,
    "narrative": narrative,
}

# ------------------------------
# Reports & Exports
# ------------------------------
st.divider()
st.subheader("Generate Reports")

case_name = ss.get("case_name", "Untitled Case")
company_size = ss.get("company_size", "Micro (1–10)")
sector = ss.get("sector", "General")
notes = ss.get("notes", "No notes provided.")
assessment = ss.get("analysis", {}).get("assessment", {})

# --- 1. Expert Checklist ---
if st.button("🧩 Generate Expert Checklist (PDF)"):
    try:
        checklist_bundle = {
            "case": case_name,
            "summary": f"Expert readiness checklist for {case_name} ({sector}, {company_size}).",
            "ic_map": assessment.get("ic_map", {}),
            "readiness": [
                {"step": "1", "name": "Identify", "tasks": ["List core intangibles", "Tag as human, structural, customer, or strategic"]},
                {"step": "2", "name": "Protect", "tasks": ["Confirm NDAs, IP filings, trade secret coverage"]},
                {"step": "3", "name": "Value", "tasks": ["Apply 10-Step Areopa method", "Capture tacit/explicit proportions"]},
            ],
            "licensing": [],
            "narrative": "Checklist for experts guiding SMEs through IC identification and readiness.",
        }
        st.download_button(
            "⬇ Download Expert Checklist",
            data=export_pdf(checklist_bundle),
            file_name=f"{case_name}_Expert_Checklist.pdf",
            mime="application/pdf"
        )
     except Exception as e:
        st.error(f"Checklist export failed: {e}")

# --- 2. Licensing Report ---
if st.button("⚖️ Generate Licensing Report (PDF)"):
try:
        licensing_bundle = {
            "case": case_name,
            "summary": f"Licensing options and FRAND readiness for {case_name}.",
            "ic_map": assessment.get("ic_map", {}),
            "readiness": assessment.get("readiness", []),
            "licensing": [
                {"model": "Revenue Licence", "notes": ["Royalty-based licence", "FRAND-aligned terms", "Annual audit clause"]},
                {"model": "Defensive Licence", "notes": ["Protective IP pooling", "Non-assertion across cluster partners"]},
                {"model": "Co-Creation Licence", "notes": ["Shared ownership of Foreground IP", "Revenue-sharing"]},
            ],
            "narrative": "Licensing-first advisory report aligning IC assets with commercial models.",
        }
        st.download_button(
            "⬇ Download Licensing Report",
            data=export_pdf(licensing_bundle),
            file_name=f"{case_name}_Licensing_Report.pdf",
            mime="application/pdf"
        )
except Exception as e:
        st.error(f"Licensing report failed: {e}")

# --- 3. Full Intangible Capital Report ---
if st.button("📘 Generate Full Intangible Capital Report (PDF)"):
try:
        ic_bundle = {
            "case": case_name,
            "summary": f"Full intangible capital analysis for {case_name}.",
            "ic_map": assessment.get("ic_map", {}),
            "readiness": assessment.get("readiness", []),
            "licensing": assessment.get("licensing", []),
            "narrative": f"This report provides a structured valuation and readiness overview of {case_name}’s intangible assets across human, customer, structural, and strategic capital types, aligning with Areopa’s 4-Leaf Model and IAS 38 principles.",
        }
        st.download_button(
            "⬇ Download Intangible Capital Report",
            data=export_pdf(ic_bundle),
            file_name=f"{case_name}_Intangible_Capital_Report.pdf",
            mime="application/pdf"
        )
except Exception as e:
        st.error(f"IC report failed: {e}")

# --- 4. IA Register (XLSX) ---
try:
    xlsx_b = export_xlsx(assessment.get("ic_map", {}))
    st.download_button(
        "⬇ Download IA Register (XLSX)",
        data=xlsx_b,
        file_name=f"{case_name}_IA_Register.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
except Exception as e:
    st.error(f"IA Register export failed: {e}")

# --- 5. Case JSON (structured data export) ---
try:
    json_bytes = export_json({
        "case": case_name,
        "sector": sector,
        "size": company_size,
        "assessment": assessment,
        "notes": notes,
    })
    st.download_button(
        "⬇ Download Case JSON",
        data=json_bytes,
        file_name=f"{case_name}_ICLicAI_Case.json",
        mime="application/json"
    )
except Exception as e:
    st.error(f"JSON export failed: {e}")
