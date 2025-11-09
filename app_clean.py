# app_clean.py — IC-LicAI Expert Console (clean rebuild)
import io
import json
from pathlib import Path
import streamlit as st

# Import your exporter functions
from ic_licai.exporters import export_pdf, export_xlsx, export_json

# Add local text saver (new)
try:
    from ic_licai.exporters_clean import save_to_local
except Exception:
    from ic_licai.exporters import save_to_local  # fallback

st.set_page_config(page_title="IC-LicAI Expert Console", layout="centered")
ss = st.session_state

st.set_page_config(page_title="IC-LicAI Expert Console", layout="centered")
ss = st.session_state

# ---------- UI CONSTANTS ----------
SECTORS = [
    "Food & Beverage", "MedTech", "GreenTech", "AgriTech", "Biotech",
    "Software/SaaS", "FinTech", "EdTech", "Manufacturing", "Creative/Digital",
    "Professional Services", "Mobility/Transport", "Energy", "Other",
]
COMPANY_SIZES = ["Micro (1–10)", "Small (11–50)", "Medium (51–250)", "Large (250+)"]

# ---------- SESSION DEFAULTS ----------
ss.setdefault("case_name", "Untitled Case")
ss.setdefault("company_size", COMPANY_SIZES[0])
ss.setdefault("sector", SECTORS[0])
ss.setdefault("notes", "")
ss.setdefault("assessment", {})   # Placeholder for AI logic

# ---------- CASE FORM ----------
st.title("IC-LicAI Expert Console")
st.caption("Upload → Guide → Advisory → Exports (licensing-first, human-in-the-loop)")

with st.form("case_form_main"):
    col1, col2 = st.columns([2, 1])
    with col1:
        case_name = st.text_input("Company name *", ss["case_name"])
        sector = st.selectbox("Sector *", SECTORS, index=SECTORS.index(ss["sector"]))
        notes = st.text_area("Notes / elevator pitch", ss["notes"], height=120)
    with col2:
        company_size = st.selectbox("Company size *", COMPANY_SIZES,
                                    index=COMPANY_SIZES.index(ss["company_size"]))
    uploaded_files = st.file_uploader("Upload evidence files (PDF, DOCX, TXT, CSV, MD)",
                                      accept_multiple_files=True)
    saved = st.form_submit_button("💾 Save Case Details")

if saved:
    ss["case_name"] = case_name or "Untitled Case"
    ss["sector"] = sector
    ss["company_size"] = company_size
    ss["notes"] = notes
    ss["uploaded_files"] = [f.name for f in uploaded_files] if uploaded_files else []
    st.success("✅ Case details saved successfully")

st.divider()

# ---------- REPORT GENERATION ----------
st.subheader("Generate Reports")

case_name = ss.get("case_name", "Untitled Case")
sector = ss.get("sector", "")
company_size = ss.get("company_size", "")
notes = ss.get("notes", "")
assessment = ss.get("assessment", {})

# 1. Expert Checklist
if st.button("🧰 Generate Expert Checklist (PDF)"):
    try:
        checklist = {
            "case": case_name,
            "summary": f"Expert readiness checklist for {case_name} ({sector}, {company_size}).",
            "readiness": [
                {"step": "1", "name": "Identify", "tasks": ["List core intangibles", "Tag as human/structural/customer/strategic"]},
                {"step": "2", "name": "Protect", "tasks": ["Confirm NDAs, IP filings, trade-secret coverage"]},
                {"step": "3", "name": "Value", "tasks": ["Apply 10-Step Areopa method", "Capture tacit/explicit proportions"]}
            ],
            "narrative": "Checklist for experts guiding SMEs through IC identification and readiness."
        }
        st.download_button("⬇️ Download Expert Checklist",
                           data=export_pdf(checklist),
                           file_name=f"{case_name}_Expert_Checklist.pdf",
                           mime="application/pdf")
    except Exception as e:
        st.error(f"Checklist export failed: {e}")

# 2. Licensing Report
if st.button("📄 Generate Licensing Report (PDF)"):
    try:
        licensing = {
            "case": case_name,
            "summary": f"Licensing options and FRAND readiness for {case_name}.",
            "licensing": [
                {"model": "Revenue Licence", "notes": ["Royalty-based licence", "FRAND-aligned terms", "Annual audit clause"]},
                {"model": "Defensive Licence", "notes": ["Protective IP pooling", "Non-assertion across cluster partners"]},
                {"model": "Co-Creation Licence", "notes": ["Shared ownership of Foreground IP", "Revenue-sharing"]}
            ],
            "narrative": "Licensing-first advisory report aligning IC assets with commercial models."
        }
        st.download_button("⬇️ Download Licensing Report",
                           data=export_pdf(licensing),
                           file_name=f"{case_name}_Licensing_Report.pdf",
                           mime="application/pdf")
    except Exception as e:
        st.error(f"Licensing report failed: {e}")

# 3. Intangible Capital Report
if st.button("📘 Generate Intangible Capital Report (PDF)"):
    try:
        ic_report = {
            "case": case_name,
            "summary": f"Full intangible capital analysis for {case_name}.",
            "narrative": f"This report provides a structured valuation and readiness overview of {case_name}'s intangible assets."
        }
        st.download_button("⬇️ Download Intangible Capital Report",
                           data=export_pdf(ic_report),
                           file_name=f"{case_name}_Intangible_Capital_Report.pdf",
                           mime="application/pdf")
    except Exception as e:
        st.error(f"IC report failed: {e}")

# 4. IA Register (XLSX)
if st.button("📊 Download IA Register (XLSX)"):
    try:
        xlsx_b = export_xlsx(assessment.get("ic_map", {}))
        st.download_button("⬇️ IA Register",
                           data=xlsx_b,
                           file_name=f"{case_name}_IA_Register.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.error(f"IA Register export failed: {e}")

# 5. JSON Export
if st.button("🧾 Download Case JSON"):
    try:
        json_b = export_json({
            "case": case_name,
            "sector": sector,
            "company_size": company_size,
            "notes": notes,
            "assessment": assessment
        })
        st.download_button("⬇️ Case JSON",
                           data=json_b,
                           file_name=f"{case_name}_Case.json",
                           mime="application/json")
    except Exception as e:
        st.error(f"JSON export failed: {e}")
