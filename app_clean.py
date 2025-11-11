# app_clean.py — IC-LicAI Expert Console (single-paste version)
# UK English (“Analyse”). Robust to missing libs. No PDFs generated (DOCX/TXT only).

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Dict, List, Any

import streamlit as st

# ---------- Optional libraries ----------
HAVE_DOCX = False
try:
    from docx import Document  # python-docx
    HAVE_DOCX = True
except Exception:
    HAVE_DOCX = False

HAVE_PYPDF2 = False
try:
    from PyPDF2 import PdfReader
    HAVE_PYPDF2 = True
except Exception:
    HAVE_PYPDF2 = False

HAVE_PANDAS = False
try:
    import pandas as pd
    HAVE_PANDAS = True
except Exception:
    HAVE_PANDAS = False


# =========================================================
#                 Evidence extraction helpers
# =========================================================

TEXT_EXT = {".txt"}
DOCX_EXT = {".docx"}
PDF_EXT  = {".pdf"}

def _safe_decode(b: bytes) -> str:
    try:
        return b.decode("utf-8", errors="ignore")
    except Exception:
        try:
            return b.decode("latin-1", errors="ignore")
    except Exception:
            return ""

def read_file_content(uploaded_file) -> str:
    """Return plain text from a supported upload. Fall back to filename."""
    name = uploaded_file.name.lower()
    suffix = Path(name).suffix
    # TXT
    if suffix in TEXT_EXT:
        return _safe_decode(uploaded_file.read())
    # DOCX
    if suffix in DOCX_EXT and HAVE_DOCX:
        try:
            bio = io.BytesIO(uploaded_file.read())
            doc = Document(bio)
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            return f"(docx could not be parsed) {uploaded_file.name}"
    # PDF
    if suffix in PDF_EXT and HAVE_PYPDF2:
        try:
            bio = io.BytesIO(uploaded_file.read())
            reader = PdfReader(bio)
            pages = []
            for p in reader.pages:
                try:
                    pages.append(p.extract_text() or "")
                except Exception:
                    pages.append("")
            return "\n".join(pages)
        except Exception:
            return f"(pdf could not be parsed) {uploaded_file.name}"
    # Fallback
    return f"(unparsed) {uploaded_file.name}"

def combine_text_from_uploads(files: List[Any], advisor_notes: str = "") -> str:
    chunks: List[str] = []
    if advisor_notes:
        chunks.append(advisor_notes)
    for f in files or []:
        try:
            chunks.append(read_file_content(f))
        except Exception:
            # if anything goes wrong, still keep the filename
            chunks.append(f"(unreadable) {getattr(f, 'name', '')}")
    return "\n\n".join([c for c in chunks if c and c.strip()])


# ---------- Very light heuristic extractors (demo-safe) ----------
def _contains_any(text: str, words: List[str]) -> bool:
    t = text.lower()
    return any(w in t for w in words)

def extract_four_leaf(text: str) -> Dict[str, str]:
    """Return short notes for each leaf from raw text."""
    notes = {}
    # Human
    if _contains_any(text, ["team", "training", "skills", "mentor", "employee", "hiring"]):
        notes["Human"] = "Signals of Human Capital (roles, skills, training, tacit know-how)."
    else:
        notes["Human"] = "No strong Human Capital cues detected."
    # Structural
    if _contains_any(text, ["process", "standard", "system", "software", "method", "ip policy", "quality"]):
        notes["Structural"] = "Signals of Structural Capital (processes, methods, QC, systems, IP policy)."
    else:
        notes["Structural"] = "No strong Structural Capital cues detected."
    # Customer
    if _contains_any(text, ["client", "customer", "pipeline", "contract", "channel", "partner"]):
        notes["Customer"] = "Signals of Customer Capital (relationships, contracts, channels)."
    else:
        notes["Customer"] = "No strong Customer Capital cues detected."
    # Strategic Alliance
    if _contains_any(text, ["mou", "alliance", "joint", "collaboration", "consortium", "license"]):
        notes["Strategic Alliance"] = "Signals of Strategic Alliance Capital (MoU, JV, co-dev, licensing)."
    else:
        notes["Strategic Alliance"] = "No strong Strategic Alliance cues detected."
    return notes

TEN_STEP_TITLES = {
    1: "Identify",
    2: "Protect",
    3: "Separate",
    4: "Safeguard",
    5: "Manage",
    6: "Control",
    7: "Measure",
    8: "Monetise",
    9: "Reassess",
    10:"Govern"
}

def extract_ten_steps(text: str) -> Dict[int, str]:
    """Very light hints for each step, to be edited by experts."""
    hints: Dict[int, str] = {}
    t = text.lower()
    hints[1] = "List core intangibles hinted in evidence; split tacit/explicit."
    hints[2] = "NDAs, trade secret coverage, filings: copyright/trademark/GTI/know-how."
    hints[3] = "Separate company vs personal vs partner assets; evidence trail."
    hints[4] = "Safeguards: access control, versioning, backups, quality gates."
    hints[5] = "Assign owners; add to IA register; link to processes and KPIs."
    hints[6] = "Rights & obligations; FRAND intent if ecosystem/cluster is involved."
    hints[7] = "Define metrics for value growth; risk discount; useful-life assumption."
    hints[8] = "Licensing, co-creation, service bundling, royalty base."
    hints[9] = "Reassess on change (milestone, risk, partner, release)."
    hints[10]= "Board oversight, auditability, evidence inbox (Vault)."
    # small evidence-reactive add-ons
    if "frand" in t or "fair" in t:
        hints[6] += " (FRAND mentioned in sources)."
    if "nda" in t:
        hints[2] += " (NDA mentioned in sources)."
    if "trademark" in t or "™" in t:
        hints[2] += " (Trademark signals)."
    if "copyright" in t:
        hints[2] += " (Copyright signals)."
    if "trade secret" in t or "know-how" in t or "knowhow" in t:
        hints[2] += " (Trade secret / know-how signals)."
    return hints

def extract_market_and_innovation(text: str) -> Dict[str, str]:
    m = "Market: micro-SME signals, early traction or pilots likely."
    if _contains_any(text, ["pilot", "po", "trial", "grant", "sdg"]):
        m = "Market: early pilots/PoCs or SDG-aligned grant activity noted."
    inn = "Innovation: incremental improvements inferred."
    if _contains_any(text, ["patent", "novel", "new material", "algorithm", "platform"]):
        inn = "Innovation: non-trivial R&D/tech signals detected."
    return {"market": m, "innovation": inn}

def build_analysis_bundle(case_name: str, sector: str, size: str, combined_text: str) -> Dict[str, Any]:
    four_leaf = extract_four_leaf(combined_text)
    ten_steps = extract_ten_steps(combined_text)
    mk_in = extract_market_and_innovation(combined_text)
    licensing_suggestions = [
        {"model": "FRAND Standard", "notes": ["Fair/Reasonable/Non-discriminatory intent", "Annual conformance check"]},
        {"model": "Co-creation (Joint Development)", "notes": ["Foreground IP split rules", "Revenue-share or access-fees"]},
        {"model": "Knowledge (Non-traditional)", "notes": ["Codified know-how, training, copyright"]},
    ]
    return {
        "case": case_name,
        "sector": sector,
        "company_size": size,
        "ic_map": four_leaf,
        "ten_steps": ten_steps,
        "market": mk_in.get("market", ""),
        "innovation": mk_in.get("innovation", ""),
        "licensing": licensing_suggestions,
        "narrative": "Draft advisory narrative to be refined by an expert.",
        "combined_excerpt": combined_text[:4000]  # keep it lean
    }


# =========================================================
#                       UI / THEME
# =========================================================

st.set_page_config(page_title="IC-LicAI Expert Console", layout="wide")

def inject_theme():
    st.markdown(
        """
        <style>
        .stApp { background:#FFF3BF; }
        .block-container { padding-top: 1.0rem; max-width:1200px; }
        .ic-title-bar{
            background:#0F2F56; color:#FFFFFF; padding:18px 22px; border-radius:10px;
            font-weight:800; font-size:32px; letter-spacing:.2px; margin: 0 0 18px 0;
            box-shadow:0 2px 6px rgba(0,0,0,0.08);
        }
        .ic-card{
            background:#FFF8CF; border:1px solid rgba(0,0,0,0.06);
            border-radius:8px; padding:16px;
        }
        .ic-btn{
            background:#0F2F56; color:#FFF; border:0; border-radius:8px; padding:10px 14px;
        }
        .sidebar-title{
            color:#0F2F56; font-weight:700; margin:8px 0 4px 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

inject_theme()

# Sidebar nav
st.sidebar.markdown("**Navigate**")
page = st.sidebar.radio(
    "", options=["Customer", "Analyse Evidence", "Expert View", "Reports"], index=0
)
st.sidebar.caption("EU theme • Areopa/ARICC demo")

ss = st.session_state


# =========================================================
#                       CUSTOMER PAGE
# =========================================================
if page == "Customer":
    st.markdown('<div class="ic-title-bar">IC-LicAI Expert Console</div>', unsafe_allow_html=True)
    st.header("Customer details")
    with st.form("customer_form"):
        c1, c2 = st.columns(2)
        with c1:
            case_name = st.text_input("Customer / Company name", ss.get("case_name", "Untitled Customer"))
            size = st.selectbox("Company size", ["Micro (1–10)", "Small (11–50)", "Medium (51–250)", "Large (250+)"],
                                index=["Micro (1–10)", "Small (11–50)", "Medium (51–250)", "Large (250+)"].index(
                                    ss.get("company_size", "Micro (1–10)")
                                ))
        with c2:
            sector = st.selectbox(
                "Sector / Industry",
                ["Food & Beverage", "MedTech", "GreenTech", "AgriTech", "Biotech",
                 "Software/SaaS", "FinTech", "EdTech", "Manufacturing", "Creative/Digital",
                 "Professional Services", "Mobility/Transport", "Energy", "Other"],
                index=0 if not ss.get("sector") else
                ["Food & Beverage","MedTech","GreenTech","AgriTech","Biotech","Software/SaaS","FinTech","EdTech",
                 "Manufacturing","Creative/Digital","Professional Services","Mobility/Transport","Energy","Other"
                ].index(ss.get("sector"))
            )
            notes = st.text_area("Quick notes (optional)", ss.get("notes", ""), height=110)
        uploads = st.file_uploader(
            "Upload evidence (optional)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            key="uploader_main",
        )
        submitted = st.form_submit_button("Save details")
        if submitted:
            ss["case_name"] = case_name or "Untitled Customer"
            ss["company_size"] = size
            ss["sector"] = sector
            ss["notes"] = notes
            ss["uploaded_files"] = uploads
            st.success("Saved customer details.")


# =========================================================
#                 ANALYSE EVIDENCE PAGE
# =========================================================
elif page == "Analyse Evidence":
    st.markdown('<div class="ic-title-bar">IC-LicAI Expert Console</div>', unsafe_allow_html=True)
    st.header("Analyse & build narrative (preview)")
    st.caption("This runs a safe heuristic pass over the uploaded evidence to pre-populate expert fields.")

    cust = ss.get("case_name", "Untitled Customer")
    sector = ss.get("sector", "")
    size = ss.get("company_size", "Micro (1–10)")

    # combine text from uploads + notes
    combined_text = combine_text_from_uploads(ss.get("uploaded_files", []), ss.get("notes", ""))

    with st.expander("Preview extracted / combined evidence (first 4000 chars)"):
        st.text_area("Combined raw text", combined_text[:4000], height=220)

    if st.button("Run Analyse"):
        if not combined_text.strip():
            st.warning("No text available — upload a TXT/DOCX/PDF or add advisor notes.")
        else:
            ss["analysis"] = build_analysis_bundle(cust, sector, size, combined_text)
            st.success("Analyse complete. Open **Expert View** to refine or go to **Reports** to export.")


# =========================================================
#                      EXPERT VIEW PAGE
# =========================================================
elif page == "Expert View":
    st.markdown('<div class="ic-title-bar">IC-LicAI Expert Console</div>', unsafe_allow_html=True)
    st.header("Expert View (edit & refine)")

    a = ss.get("analysis")
    if not a:
        st.info("No analysis yet. Go to **Analyse Evidence** and click **Run Analyse** first.")
    else:
        with st.form("expert_edit"):
            st.subheader("Four-Leaf Model")
            c1, c2 = st.columns(2)
            with c1:
                a["ic_map"]["Human"] = st.text_area("Human Capital", a["ic_map"].get("Human", ""), height=120)
                a["ic_map"]["Customer"] = st.text_area("Customer Capital", a["ic_map"].get("Customer", ""), height=120)
            with c2:
                a["ic_map"]["Structural"] = st.text_area("Structural Capital", a["ic_map"].get("Structural", ""), height=120)
                a["ic_map"]["Strategic Alliance"] = st.text_area("Strategic Alliance Capital", a["ic_map"].get("Strategic Alliance", ""), height=120)

            st.subheader("10-Step Method (Areopa)")
            for step in range(1, 11):
                key = TEN_STEP_TITLES[step]
                a["ten_steps"][step] = st.text_area(f"{step}. {key}", a["ten_steps"].get(step, ""), height=90)

            st.subheader("Market & Innovation")
            a["market"] = st.text_area("Market analysis", a.get("market", ""), height=110)
            a["innovation"] = st.text_area("Innovation analysis", a.get("innovation", ""), height=110)

            st.subheader("Licensing intent & FRAND notes")
            # show defaults but allow edits
            models = a.get("licensing", [])
            if not isinstance(models, list): models = []
            for i, m in enumerate(models[:3]):
                models[i]["model"] = st.text_input(f"Licensing model {i+1} name", m.get("model", ""))
                joined = "\n".join(m.get("notes", []))
                edited = st.text_area(f"Licensing model {i+1} notes", joined, height=80)
                models[i]["notes"] = [ln for ln in edited.split("\n") if ln.strip()]
            a["licensing"] = models

            a["narrative"] = st.text_area("Draft advisory narrative", a.get("narrative", ""), height=120)

            saved = st.form_submit_button("Save expert edits")
            if saved:
                ss["analysis"] = a
                st.success("Expert edits saved.")


# =========================================================
#                         REPORTS PAGE
# =========================================================
elif page == "Reports":
    st.markdown('<div class="ic-title-bar">IC-LicAI Expert Console</div>', unsafe_allow_html=True)
    st.header("Reports & Downloads")

    a = ss.get("analysis")
    if not a:
        st.info("No analysis available. Run **Analyse** first.")
    else:
        # ---------- builders ----------
        def build_ic_report_text(a: Dict[str, Any]) -> (str, str):
            title = f"IC Report — {a.get('case','Customer')}"
            body = []
            body.append("# Cover")
            body.append(title)
            body.append("")
            body.append("# Disclaimer")
            body.append("This is an advisory draft, to be verified by subject-matter experts and the client.")
            body.append("")
            body.append("# Executive Summary")
            body.append(a.get("narrative", ""))
            body.append("")
            body.append("# Intellectual Asset Inventory (Four-Leaf)")
            ic = a.get("ic_map", {})
            for leaf in ["Human", "Structural", "Customer", "Strategic Alliance"]:
                body.append(f"## {leaf}")
                body.append(ic.get(leaf, ""))
                body.append("")
            body.append("# 10-Step Readiness")
            ts = a.get("ten_steps", {})
            for i in range(1, 11):
                body.append(f"## {i}. {TEN_STEP_TITLES[i]}")
                body.append(ts.get(i, ""))
                body.append("")
            body.append("# Market & Innovation")
            body.append("## Market")
            body.append(a.get("market", ""))
            body.append("## Innovation")
            body.append(a.get("innovation", ""))
            body.append("")
            body.append("# Action Plan (to be refined)")
            body.append("- Convert tacit → explicit where feasible")
            body.append("- Close protection gaps (NDA, trade secret, copyright, trademarks, GTI)")
            body.append("- Add items to IA Register; assign owners; set KPIs")
            body.append("- Prepare licensing/partner options and FRAND guardrails")
            return title, "\n".join(body)

        def build_lic_report_text(a: Dict[str, Any]) -> (str, str):
            title = f"Licensing Report — {a.get('case','Customer')}"
            body = []
            body.append("# Licensing Report")
            body.append(f"Customer: {a.get('case','')}")
            body.append(f"Sector: {a.get('sector','')}")
            body.append(f"Size: {a.get('company_size','')}")
            body.append("")
            body.append("## Evidence summary")
            body.append((a.get("combined_excerpt") or "")[:1000])
            body.append("")
            body.append("## Candidate models")
            for m in a.get("licensing", []):
                body.append(f"- **{m.get('model','')}**")
                for n in m.get("notes", []):
                    body.append(f"  - {n}")
            body.append("")
            body.append("## FRAND guardrails")
            body.append("- Transparency, fee corridor, non-discrimination")
            body.append("- Annual conformance check; audit right limited to scope")
            body.append("- Essentiality rationales recorded")
            body.append("")
            body.append("## Next steps")
            body.append("- Select model; draft template; agree term sheet")
            body.append("- Confirm IP boundaries (Foreground vs Background)")
            return title, "\n".join(body)

        def export_bytes_as_docx_or_txt(title: str, body: str) -> (bytes, str, str):
            """Return (bytes, filename, mimetype) as DOCX if available, else TXT."""
            safe_title = re.sub(r"[^A-Za-z0-9_.-]+", "_", title).strip("_")
            if HAVE_DOCX:
                doc = Document()
                for line in body.split("\n"):
                    doc.add_paragraph(line)
                bio = io.BytesIO()
                doc.save(bio)
                return bio.getvalue(), f"{safe_title}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            else:
                data = body.encode("utf-8")
                return data, f"{safe_title}.txt", "text/plain"

        # ---------- Downloads ----------
        st.subheader("Generate reports")
        c1, c2, c3 = st.columns(3)

        with c1:
            title, body = build_ic_report_text(a)
            data, fname, mime = export_bytes_as_docx_or_txt(title, body)
            st.download_button("⬇ IC Report (DOCX/TXT)", data=data, file_name=fname, mime=mime)

        with c2:
            title, body = build_lic_report_text(a)
            data, fname, mime = export_bytes_as_docx_or_txt(title, body)
            st.download_button("⬇ Licensing Report (DOCX/TXT)", data=data, file_name=fname, mime=mime)

        with c3:
            if HAVE_PANDAS:
                # very simple IA register from Four-Leaf
                rows: List[Dict[str, str]] = []
                for leaf, desc in (a.get("ic_map") or {}).items():
                    rows.append({"Capital": leaf, "Item/Notes": desc})
                df = pd.DataFrame(rows, columns=["Capital", "Item/Notes"])
                bio = io.BytesIO()
                with pd.ExcelWriter(bio, engine="xlsxwriter") as w:
                    df.to_excel(w, index=False, sheet_name="IA Register")
                st.download_button("⬇ IA Register (XLSX)", data=bio.getvalue(),
                                   file_name=f"{re.sub(r'[^A-Za-z0-9_.-]+','_', a.get('case','Customer'))}_IA_Register.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("Install pandas/xlsxwriter to enable XLSX export.")


# End
