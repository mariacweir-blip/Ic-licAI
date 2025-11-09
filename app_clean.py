# app_clean.py  — IC-LicAI Expert Console (licensing-first)
import io
import json
from datetime import date
from pathlib import Path
import streamlit as st

# ---- Optional: themed CSS (safe-noop if file missing)
def inject_eu_theme():
    css_path = Path("theme") / "eu.css"
    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
        st.markdown("<style>" + css + "</style>", unsafe_allow_html=True)

# ---- Import processing + exporters with tolerant fallbacks
try:
    from ic_licai.processing import parse_uploaded_files, draft_ic_assessment
except Exception:
    from processing import parse_uploaded_files, draft_ic_assessment  # type: ignore

try:
    from ic_licai.exporters_clean import export_pdf, export_xlsx, export_json
except Exception:
    from exporters_clean import export_pdf, export_xlsx, export_json  # type: ignore

# ---- Session defaults so first load never crashes
ss = st.session_state
ss.setdefault("case_name", "Untitled Case")
ss.setdefault("analysis", {})       # {"assessment": {...}, "case": "...", "notes": "..."}
ss.setdefault("guide", {})          # expert selections (booleans etc.)
ss.setdefault("narrative", "")      # final advisory text
ss.setdefault("licence_choice", "Fixed-Fee Starter")
ss.setdefault("sector", "")

# ---- Page + theme
st.set_page_config(page_title="IC-LicAI — Expert Console", layout="centered")
inject_eu_theme()

# ---- Tabs
tabs = st.tabs(["1) Case Setup", "2) Evidence & Checklist", "3) Expert Report"])

# =========================
# TAB 1 — Case Setup
# =========================
with tabs[0]:
    st.subheader("Case Setup")

    ss["case_name"] = st.text_input("Case / Company name", value=ss.get("case_name", "Untitled Case"))

    size = st.selectbox("Company size", ["Micro (1-10)", "SME (11-250)", "Large (250+)"], index=0)
    ss["sector"] = st.text_input("Sector (optional)", value=ss.get("sector", ""))

    uploads = st.file_uploader(
        "Upload evidence files (PDF, DOCX, TXT, CSV)",
        type=["pdf", "docx", "txt", "csv"],
        accept_multiple_files=True
    )
    notes = st.text_area("Paste interview notes or context (optional)", height=140)

    if st.button("Run IC + ESG Scan"):
        try:
            parsed = parse_uploaded_files(uploads or [])
        except Exception:
            parsed = {"texts": []}

        text_input = (notes.strip() + "\n" if notes else "")
        text_input += "\n".join(parsed.get("texts", []))

        assessment = {}
        try:
            assessment = draft_ic_assessment(text_input)
        except Exception:
            assessment = {}

        ss["analysis"] = {
            "assessment": assessment,
            "case": ss.get("case_name", "Untitled Case"),
            "notes": text_input
        }
        st.success("IC / ESG artefacts mapped. Continue to Evidence & Checklist.")

# =========================
# TAB 2 — Evidence & Checklist
# =========================
with tabs[1]:
    st.subheader("Evidence & Licensing Checklist")

    colA, colB = st.columns(2)
    with colA:
        lic_intent = st.radio(
            "Licensing intent",
            ["Defensive (protect IP)", "Revenue (licence income)", "Collaborative (co-creation)"],
            index=1
        )
        lic_type = st.selectbox(
            "Proposed licence structure",
            ["Fixed-Fee Starter", "Royalty with Cap", "Evaluation to Commercial", "Co-Creation & Shared-IP"],
            index=["Fixed-Fee Starter", "Royalty with Cap", "Evaluation to Commercial", "Co-Creation & Shared-IP"].index(
                ss.get("licence_choice", "Fixed-Fee Starter")
            )
        )

    guide_prev = ss.get("guide", {})
    with colB:
        assets_identified = st.checkbox("Key intangible assets identified", value=guide_prev.get("assets_identified", False))
        esg_confirmed = st.checkbox("ESG artefacts confirmed or mapped", value=guide_prev.get("esg_confirmed", False))
        contracts_reviewed = st.checkbox("Contracts/partnerships reviewed", value=guide_prev.get("contracts_reviewed", False))
        governance_ok = st.checkbox("Governance and sign-off documented", value=guide_prev.get("governance_ok", False))
        valuation_understood = st.checkbox("Valuation and risk tolerance understood", value=guide_prev.get("valuation_understood", False))

    if st.button("Save Expert Inputs"):
        ss["guide"] = {
            "lic_intent": lic_intent,
            "assets_identified": assets_identified,
            "esg_confirmed": esg_confirmed,
            "contracts_reviewed": contracts_reviewed,
            "governance_ok": governance_ok,
            "valuation_understood": valuation_understood,
        }
        ss["licence_choice"] = lic_type
        st.success("Expert inputs saved. Continue to Expert Report.")

# =========================
# TAB 3 — Expert Report (licensing-first)
# =========================
with tabs[2]:
    st.subheader("Licensing Advisory Report")

    analysis = ss.get("analysis", {}).get("assessment", {})
    guide = ss.get("guide", {})
    lic_choice = ss.get("licence_choice", "Fixed-Fee Starter")

    if not isinstance(analysis, dict) or not analysis:
        st.info("Run IC + ESG Scan on Case Setup, then save Expert Inputs on the Checklist tab.")
    else:
        # Build a concise, licensing-first narrative
        ic_map = analysis.get("ic_map", {}) if isinstance(analysis.get("ic_map", {}), dict) else {}
        esg_map = analysis.get("esg_map", {}) if isinstance(analysis.get("esg_map", {}), dict) else {}
        artefact_count = sum(len(v) for v in ic_map.values()) if ic_map else 0

        intent = guide.get("lic_intent", "Collaborative (co-creation)")
        readiness_score = (
            (1 if guide.get("assets_identified") else 0) +
            (1 if guide.get("esg_confirmed") else 0) +
            (1 if guide.get("contracts_reviewed") else 0) +
            (1 if guide.get("governance_ok") else 0) +
            (1 if guide.get("valuation_understood") else 0)
        )
        readiness = "strong" if readiness_score >= 4 else ("emerging" if readiness_score >= 2 else "early")

        frand_block = {
            "Fixed-Fee Starter": [
                "Fixed-fee licence for 6 to 12 months, uniform FRAND terms.",
                "MFN for similarly situated micro licensees.",
                "Audit on notice; no more than once per year."
            ],
            "Royalty with Cap": [
                "Royalty 2.0 percent of Net Sales with annual cap.",
                "Clear Net Sales definition; MFN across comparable licensees.",
                "Quarterly statements and right to audit."
            ],
            "Evaluation to Commercial": [
                "60-day evaluation for internal uses only.",
                "Pre-agreed conversion corridor: fee or 1.5 to 2.5 percent royalty.",
                "On conversion, adopt short-form commercial licence."
            ],
            "Co-Creation & Shared-IP": [
                "Joint Steering Committee and shared Foreground IP.",
                "Background IP licensed for project uses on FRAND terms.",
                "Commercial exploitation requires joint agreement."
            ],
        }
        frand_lines = frand_block.get(lic_choice, [])

        report_lines = []
        report_lines.append("LICENSING READINESS SUMMARY")
        report_lines.append("The organisation shows " + readiness + " readiness for " + intent.lower() + " licensing activities as of " + date.today().strftime("%d %b %Y") + ".")
        report_lines.append("")
        report_lines.append("EVIDENCE BASE (IC AND ESG)")
        report_lines.append("Intangible artefacts mapped: " + str(artefact_count) + ".")
        if esg_map:
            report_lines.append("ESG artefacts present and mapped for alignment.")
        else:
            report_lines.append("ESG artefacts not confirmed; consider mapping for partner expectations.")
        report_lines.append("")
        report_lines.append("FRAND STRATEGY — " + lic_choice)
        for line in frand_lines:
            report_lines.append("- " + line)
        report_lines.append("")
        report_lines.append("RISK AND GOVERNANCE")
        report_lines.append("- Maintain a short IA register with owner sign-off.")
        report_lines.append("- Keep a renewal diary and evidence snapshots.")
        report_lines.append("- Include audit and MFN terms appropriate to cohort.")
        report_lines.append("")
        report_lines.append("NEXT STEPS")
        report_lines.append("- Prepare short-form templates and publish a rate card.")
        report_lines.append("- Update IA register under IAS 38 and align with controls.")
        report_lines.append("- Identify first partner candidates and set pilot metrics.")

        narrative = "\n".join(report_lines).strip()
        ss["narrative"] = narrative

        st.text_area("Generated report (editable)", value=narrative, height=360, key="lic_report_text")

        bundle = {
            "case": ss.get("case_name", "Untitled Case"),
            "narrative": ss.get("lic_report_text", narrative),
            "assessment": analysis,
            "guide": guide,
            "licence_choice": lic_choice,
            "sector": ss.get("sector", ""),
            "company_size": size if "size" in locals() else ""
        }

        c1, c2, c3 = st.columns(3)
        with c1:
            try:
                pdf_bytes = export_pdf(bundle)
                st.download_button("Download PDF", data=pdf_bytes, file_name="ICLicAI_Licensing_Report.pdf", mime="application/pdf")
            except Exception as e:
                st.error("PDF export failed: " + str(e))
        with c2:
            try:
                xlsx_bytes = export_xlsx(bundle)
                st.download_button("Download XLSX", data=xlsx_bytes, file_name="ICLicAI_IA_Register.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except Exception as e:
                st.error("XLSX export failed: " + str(e))
        with c3:
            try:
                json_bytes = export_json(bundle)
                st.download_button("Download JSON", data=json_bytes, file_name="ICLicAI_Case.json", mime="application/json")
            except Exception as e:
                st.error("JSON export failed: " + str(e))
