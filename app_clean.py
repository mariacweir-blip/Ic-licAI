# app_clean.py — IC-LicAI Expert Console (minimal, safe, licensing-first)

from __future__ import annotations
import io
import json
from pathlib import Path
import streamlit as st
from ic_licai.exporters_clean import export_pdf, export_xlsx, export_json

# --- UI constants ---
SECTORS = [
    "Food & Beverage", "MedTech", "GreenTech", "AgriTech", "Biotech",
    "Software/SaaS", "FinTech", "EdTech", "Manufacturing", "Creative/Digital",
    "Professional Services", "Mobility/Transport", "Energy", "Other",
]
COMPANY_SIZES = ["Micro (1–10)", "Small (11–50)", "Medium (51–250)", "Large (250+)"]

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

st.divider()

# --- Exports (always available for smoke test) ---
st.subheader("Exports")
c1, c2, c3 = st.columns(3)

# PDF
with c1:
    try:
        pdf_b = export_pdf(bundle)
        st.download_button("⬇ PDF report", data=pdf_b, file_name="ICLicAI_Advisory_Report.pdf", mime="application/pdf", key="dl_pdf")
    except Exception as e:
        st.error(f"PDF export failed: {e}")

# XLSX
with c2:
    try:
        xlsx_b = export_xlsx(bundle.get("ic_map", {}))
        st.download_button("⬇ IA Register (XLSX)", data=xlsx_b, file_name="ICLicAI_IA_Register.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_xlsx")
    except Exception as e:
        st.error(f"XLSX export failed: {e}")

# JSON
with c3:
    try:
        json_b = export_json(bundle)
        st.download_button("⬇ Case JSON", data=json_b, file_name="ICLicAI_Case.json", mime="application/json", key="dl_json")
    except Exception as e:
        st.error(f"JSON export failed: {e}")
