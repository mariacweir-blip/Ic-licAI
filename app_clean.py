# app_clean.py — IC-LicAI Expert Console (Licensing-first, server-save)
# ---------------------------------------------------------------
# Features:
# - Upload evidence (PDF/DOCX/TXT/CSV/XLSX/IMG)
# - Extended analysis (4-Leaf, 10-Steps, Market/Innovation, IPR/ESG cues)
# - Exports: IC Report (DOCX), Licensing Report (DOCX), Expert Checklist (DOCX), IA Register (XLSX)
# - Saves to server path (configure SAVE_ROOT) and offers immediate download
# - EU theme (navy + yellow), Sidebar navigation

import io
import json
import re
import datetime as dt
from pathlib import Path
from typing import List, Dict, Any, Tuple

import streamlit as st
import pandas as pd

# Optional parsers (we guard imports so missing libs don’t crash the app)
try:
    from docx import Document
except Exception:
    Document = None

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import openpyxl
    from openpyxl import Workbook
except Exception:
    openpyxl = None
    Workbook = None

# =============== CONFIG ===============
# Change this to your shared server folder:
SAVE_ROOT = Path("/srv/shared/ICLicAI/reports")

# UI theme colors
NAVY = "#0B2A4A"
YELLOW = "#F7C600"
BG = "#FAFAFD"

st.set_page_config(page_title="IC-LicAI Expert Console", layout="wide")

# Minimal EU-style theming
st.markdown(
    f"""
    <style>
      .block-container {{ padding-top: 1.2rem; max-width: 1280px; }}
      .eutitle {{
         background:{NAVY}; color:white; padding:14px 18px; border-radius:6px;
         font-weight:700; letter-spacing:.2px; font-size:20px;
      }}
      .eubtn {{
         background:{NAVY}; color:white; padding:10px 14px; border-radius:6px;
         text-decoration:none; font-weight:600; display:inline-block;
      }}
      .eubadge {{
         background:{YELLOW}; color:black; padding:2px 8px; border-radius:10px;
         font-weight:700; margin-left:8px;
      }}
      .navwrap {{
         background:white; border:1px solid #E6E8EF; border-radius:10px; padding:12px 10px;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)

ss = st.session_state
for k, v in {
    "customer_name": "Untitled Customer",
    "company_size": "Micro (1–10)",
    "sector": "",
    "notes": "",
    "uploads": [],
    "parsed_texts": [],
    "assessment": {},
    "ic_map": {},
    "ten_steps": {},
    "market": {},
    "ipr": {},
    "narrative": "",
}.items():
    ss.setdefault(k, v)

SECTORS = [
    "Food & Beverage", "MedTech", "GreenTech", "AgriTech", "Biotech",
    "Software/SaaS", "FinTech", "EdTech", "Manufacturing", "Creative/Digital",
    "Professional Services", "Mobility/Transport", "Energy", "Other",
]

SIZES = ["Micro (1–10)", "Small (11–50)", "Medium (51–250)", "Large (250+)"]

# =============== HELPERS ===============
def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def _now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")

def _save_bytes_to_server(folder: Path, fname: str, data: bytes) -> Path:
    _ensure_dir(folder)
    out = folder / fname
    out.write_bytes(data)
    return out

def _save_text_to_server(folder: Path, fname: str, text: str) -> Path:
    _ensure_dir(folder)
    out = folder / fname
    out.write_text(text, encoding="utf-8")
    return out

def _server_folder_for_case(customer: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", customer.strip() or "Customer")
    return SAVE_ROOT / safe / _now_stamp()

def _read_file_to_text(name: str, bytes_data: bytes) -> str:
    name_lower = name.lower()
    # TXT
    if name_lower.endswith(".txt"):
        try:
            return bytes_data.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    # DOCX
    if name_lower.endswith(".docx") and Document:
        try:
            bio = io.BytesIO(bytes_data)
            doc = Document(bio)
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            return ""
    # PDF
    if name_lower.endswith(".pdf") and PdfReader:
        try:
            bio = io.BytesIO(bytes_data)
            reader = PdfReader(bio)
            out = []
            for page in reader.pages:
                try:
                    out.append(page.extract_text() or "")
                except Exception:
                    pass
            return "\n".join(out)
        except Exception:
            return ""
    # CSV
    if name_lower.endswith(".csv"):
        try:
            df = pd.read_csv(io.BytesIO(bytes_data))
            return df.to_csv(index=False)
        except Exception:
            return ""
    # XLSX
    if name_lower.endswith(".xlsx"):
        try:
            xls = pd.ExcelFile(io.BytesIO(bytes_data))
            txt = []
            for sheet in xls.sheet_names:
                df = xls.parse(sheet)
                txt.append(f"[Sheet: {sheet}]\n{df.to_csv(index=False)}")
            return "\n\n".join(txt)
        except Exception:
            return ""
    # Images: we don’t OCR, we record a marker
    if any(name_lower.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp")):
        return f"[Image file: {name}]"
    # PPTX (not parsing content here—placeholder)
    if name_lower.endswith(".pptx"):
        return f"[Presentation file: {name}]"
    # Fallback
    return ""

# =============== ANALYSIS (heuristics) ===============
def _extract_cues(text_blob: str) -> Dict[str, Any]:
    t = text_blob.lower()

    # 4-Leaf (very light heuristics)
    ic_map = {
        "Human": bool(re.search(r"training|skills|hiring|staff|capability|competence", t)),
        "Structural": bool(re.search(r"process|method|software|system|sop|governance|register", t)),
        "Customer": bool(re.search(r"customer|client|contract|pipeline|retention|crm", t)),
        "Strategic Alliance": bool(re.search(r"partner|alliance|mou|jv|consortium|co-creation|cooperation", t)),
    }

    # 10-Steps readiness (1-10 scale; crude)
    ten = {
        "Identify": 7 if re.search(r"asset|artefact|ip|knowledge|data", t) else 3,
        "Separate": 6 if re.search(r"separate|segregate|delineate|register", t) else 2,
        "Protect": 6 if re.search(r"nda|confidential|copyright|trademark|patent|trade secret", t) else 2,
        "Safeguard": 5 if re.search(r"backup|control|access|security", t) else 2,
        "Manage": 6 if re.search(r"governance|owner|approval|policy", t) else 2,
        "Control": 5 if re.search(r"audit|evidence|trace|log", t) else 2,
        "Use": 6 if re.search(r"exploit|deploy|license|commercialise|commercialize", t) else 3,
        "Monitor": 5 if re.search(r"kpi|metric|review|renewal", t) else 2,
        "Value": 4 if re.search(r"value|valuation|ias|frs|ifrs", t) else 1,
        "Report": 5 if re.search(r"report|board|quarterly|policy", t) else 2,
    }

    # Market & Innovation
    market = {
        "Sector Mentioned": any(s.lower() in t for s in [s.lower() for s in SECTORS]),
        "Innovation Signals": bool(re.search(r"prototype|pilot|innovation|novel|rd|r&d", t)),
        "Business Model Cues": bool(re.search(r"saas|subscription|royalty|licen[sc]e|frand|bundl", t)),
    }

    # IPR & ESG
    ipr = {
        "Copyright": bool(re.search(r"copyright|©|creative commons", t)),
        "Trademark": bool(re.search(r"™|®|trademark", t)),
        "Patent": bool(re.search(r"patent|pct|claims", t)),
        "Trade Secret": bool(re.search(r"trade secret|confidential know-how", t)),
        "ESG Mention": bool(re.search(r"esg|sdg|scope\s?(1|2|3)|csr|environmental|social|governance", t)),
    }

    return {"ic_map": ic_map, "ten_steps": ten, "market": market, "ipr": ipr}

def _summarise_findings(customer: str, size: str, sector: str, cues: Dict[str, Any]) -> str:
    h = cues["ic_map"]["Human"]
    s = cues["ic_map"]["Structural"]
    c = cues["ic_map"]["Customer"]
    a = cues["ic_map"]["Strategic Alliance"]
    highlights = []
    if h: highlights.append("Human Capital is evidenced (skills/training).")
    if s: highlights.append("Structural Capital exists (processes/systems/registers).")
    if c: highlights.append("Customer Capital appears in contracts/pipeline/CRM.")
    if a: highlights.append("Strategic Alliances present (partners/JVs/MOUs).")
    if not highlights:
        highlights.append("Limited explicit evidence; focus on tacit→explicit capture.")

    return (
        f"{customer} is a {size} in {sector or 'an unspecified sector'}. "
        "The evidence indicates:\n- " + "\n- ".join(highlights) + "\n\n"
        "10-Steps show partial readiness; priority is codifying artefacts, governance, and FRAND-ready terms. "
        "Market/Innovation cues indicate fit for lightweight licensing bundles (micro-SME friendly)."
    )

# =============== TEMPLATES (DOCX content) ===============
def _doc_par(doc, text: str, bold=False):
    p = doc.add_paragraph()
    run = p.add_run(text)
    if bold: run.bold = True
    return p

def build_ic_report_docx(customer: str, size: str, sector: str, cues: Dict[str, Any], notes: str) -> bytes:
    if not Document:
        return "python-docx not installed.".encode("utf-8")
    doc = Document()
    _doc_par(doc, "Intangible Capital Report", bold=True)
    _doc_par(doc, f"Customer: {customer}")
    _doc_par(doc, f"Company Size: {size}")
    _doc_par(doc, f"Sector: {sector or 'N/A'}")
    doc.add_paragraph()

    _doc_par(doc, "Executive Summary", bold=True)
    _doc_par(doc, _summarise_findings(customer, size, sector, cues))
    doc.add_paragraph()

    _doc_par(doc, "4-Leaf Map", bold=True)
    for leaf, present in cues["ic_map"].items():
        _doc_par(doc, f"- {leaf}: {'✔ Evidence' if present else '• (not explicit)'}")
    doc.add_paragraph()

    _doc_par(doc, "10-Steps Readiness", bold=True)
    for step, score in cues["ten_steps"].items():
        _doc_par(doc, f"- {step}: {score}/10")
    doc.add_paragraph()

    _doc_par(doc, "Market & Innovation", bold=True)
    for k, v in cues["market"].items():
        _doc_par(doc, f"- {k}: {'Yes' if v else 'No'}")
    doc.add_paragraph()

    _doc_par(doc, "IPR & ESG", bold=True)
    for k, v in cues["ipr"].items():
        _doc_par(doc, f"- {k}: {'Yes' if v else 'No'}")
    doc.add_paragraph()

    _doc_par(doc, "Analyst Notes", bold=True)
    _doc_par(doc, notes or "—")
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

def build_licensing_report_docx(customer: str, size: str, sector: str, cues: Dict[str, Any]) -> bytes:
    if not Document:
        return "python-docx not installed.".encode("utf-8")
    doc = Document()
    _doc_par(doc, "Licensing Strategy Report", bold=True)
    _doc_par(doc, f"Customer: {customer}  |  Size: {size}  |  Sector: {sector or 'N/A'}")
    doc.add_paragraph()

    _doc_par(doc, "Recommended FRAND-Aligned Options", bold=True)
    _doc_par(doc, "1) Fixed-Fee Starter Licence: 6–12m term; uniform terms; audit on request.")
    _doc_par(doc, "2) Royalty Licence: 2–3% of net sales; annual cap; MFN across equivalent licensees.")
    _doc_par(doc, "3) Evaluation→Commercial Path: 60-day evaluation; pre-agreed conversion corridor.")
    doc.add_paragraph()

    _doc_par(doc, "Co-Creation Pathway", bold=True)
    _doc_par(doc, "Joint artefact register, contribution logs, proportional revenue split, field-of-use carve-outs.")
    doc.add_paragraph()

    _doc_par(doc, "Non-Traditional Artefacts", bold=True)
    _doc_par(doc, "Codified know-how, checklists, datasets, prompts; social-benefit and commercial variants.")
    doc.add_paragraph()

    _doc_par(doc, "Governance & Traceability", bold=True)
    _doc_par(doc, "Owner approval per asset; one-page governance note; renewal diary; monthly evidence snapshot.")
    doc.add_paragraph()

    _doc_par(doc, "Signals from Evidence", bold=True)
    _doc_par(doc, _summarise_findings(customer, size, sector, cues))
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

def build_expert_checklist_docx(customer: str, sector: str) -> bytes:
    if not Document:
        return "python-docx not installed.".encode("utf-8")
    doc = Document()
    _doc_par(doc, "Expert Evidence Checklist (Licensing-first)", bold=True)
    _doc_par(doc, f"Customer: {customer} | Sector: {sector or 'N/A'}")
    doc.add_paragraph()

    _doc_par(doc, "1) 4-Leaf (tick and note evidence)", bold=True)
    for leaf in ["Human", "Structural", "Customer", "Strategic Alliance"]:
        _doc_par(doc, f"[ ] {leaf}: _________________________")

    doc.add_paragraph()
    _doc_par(doc, "2) 10-Steps (readiness & next action)", bold=True)
    for step in ["Identify","Separate","Protect","Safeguard","Manage","Control","Use","Monitor","Value","Report"]:
        _doc_par(doc, f"{step}: ______/10 | Next action: ___________________")

    doc.add_paragraph()
    _doc_par(doc, "3) Market & Innovation Highlights", bold=True)
    _doc_par(doc, "Notes: ________________________________________")

    doc.add_paragraph()
    _doc_par(doc, "4) IPR (copyright/trademark/patent/trade secret) & ESG cues", bold=True)
    _doc_par(doc, "Notes: ________________________________________")

    doc.add_paragraph()
    _doc_par(doc, "5) Licensing Intent (micro-bundle, co-creation, non-traditional)", bold=True)
    _doc_par(doc, "Notes: ________________________________________")

    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

def build_register_xlsx(items: List[Dict[str, Any]]) -> bytes:
    # Minimal IA register; pandas → Excel
    df = pd.DataFrame(items or [], columns=[
        "Asset Name","Type (4-Leaf)","Owner","Origin","Evidence","Protection","Readiness (10-Steps)","Notes"
    ])
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="IA_Register")
    return bio.getvalue()

# =============== SIDEBAR NAV ===============
with st.sidebar:
    st.markdown(f'<div class="eutitle">IC-LicAI Expert Console <span class="eubadge">EU</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="navwrap">', unsafe_allow_html=True)
    page = st.radio("Navigate", ["Customer", "Analyse Evidence", "Expert View", "Reports", "Licensing Templates"], index=0)
    st.markdown('</div>', unsafe_allow_html=True)

# =============== PAGES ===============
if page == "Customer":
    st.subheader("Customer Details")
    c1, c2, c3 = st.columns([2,2,2])
    with c1:
        ss.customer_name = st.text_input("Customer", value=ss.customer_name)
    with c2:
        ss.company_size = st.selectbox("Company Size", SIZES, index=SIZES.index(ss.company_size))
    with c3:
        ss.sector = st.selectbox("Sector", SECTORS, index=(SECTORS.index(ss.sector) if ss.sector in SECTORS else len(SECTORS)-1))
    ss.notes = st.text_area("Analyst Notes (optional)", value=ss.notes, height=120)

    st.divider()
    st.caption("Uploads are stored in session until analysis. Nothing is written to server until you export.")

    uploads = st.file_uploader(
        "Upload evidence (PDF, DOCX, TXT, CSV, XLSX, images, PPTX)",
        type=["pdf","docx","txt","csv","xlsx","png","jpg","jpeg","webp","pptx"],
        accept_multiple_files=True,
        key="uploader_customer"
    )
    if uploads:
        # Keep in memory for this session
        ss.uploads = [(f.name, f.getvalue()) for f in uploads]
        st.success(f"Loaded {len(uploads)} file(s) to session.")

elif page == "Analyse Evidence":
    st.subheader("Analyse Evidence")
    if not ss.uploads:
        st.warning("Please upload evidence on the **Customer** page first.")
    else:
        all_texts = []
        for name, data in ss.uploads:
            txt = _read_file_to_text(name, data)
            # light normalisation
            txt = re.sub(r"\s+", " ", txt).strip()
            if txt:
                all_texts.append(txt[:200000])  # cap per file just in case
        combined = "\n".join(all_texts)
        ss.parsed_texts = all_texts

        if not combined:
            st.error("No parsable text found in the uploaded files. Images/PPTX are recorded but not parsed.")
        else:
            cues = _extract_cues(combined)
            ss.ic_map = cues["ic_map"]
            ss.ten_steps = cues["ten_steps"]
            ss.market = cues["market"]
            ss.ipr = cues["ipr"]
            ss.assessment = cues
            ss.narrative = _summarise_findings(ss.customer_name, ss.company_size, ss.sector, cues)
            st.success("Evidence analysed. Switch to **Expert View** to inspect details or **Reports** to export.")

elif page == "Expert View":
    st.subheader("Expert View")
    if not ss.assessment:
        st.info("Run **Analyse Evidence** first.")
    else:
        st.markdown("#### Narrative Summary")
        st.text_area("Summary (editable)", ss.narrative, key="narrative_edit", height=180)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 4-Leaf Map")
            for k, v in ss.ic_map.items():
                st.write(f"- {k}: {'✔' if v else '•'}")
            st.markdown("#### Market & Innovation")
            for k, v in ss.market.items():
                st.write(f"- {k}: {'Yes' if v else 'No'}")
        with c2:
            st.markdown("#### 10-Steps Readiness")
            st.dataframe(pd.DataFrame({"Step": list(ss.ten_steps.keys()), "Score (1-10)": list(ss.ten_steps.values())}))
            st.markdown("#### IPR & ESG")
            for k, v in ss.ipr.items():
                st.write(f"- {k}: {'Yes' if v else 'No'}")

elif page == "Reports":
    st.subheader("Reports & Exports")
    if not ss.assessment:
        st.info("Run **Analyse Evidence** first.")
    else:
        # Build outputs
        cues = {
            "ic_map": ss.ic_map,
            "ten_steps": ss.ten_steps,
            "market": ss.market,
            "ipr": ss.ipr,
        }
        customer = ss.customer_name
        case_folder = _server_folder_for_case(customer)

        # IC Report (DOCX)
        ic_doc = build_ic_report_docx(customer, ss.company_size, ss.sector, cues, ss.get("narrative_edit", ss.narrative))
        ic_name = f"{customer}_IC_Report_{_now_stamp()}.docx"
        ic_path = _save_bytes_to_server(case_folder, ic_name, ic_doc)
        st.download_button("⬇ Download IC Report (DOCX)", data=ic_doc, file_name=ic_name, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="dl_ic")

        # Licensing Report (DOCX)
        lic_doc = build_licensing_report_docx(customer, ss.company_size, ss.sector, cues)
        lic_name = f"{customer}_Licensing_Report_{_now_stamp()}.docx"
        lic_path = _save_bytes_to_server(case_folder, lic_name, lic_doc)
        st.download_button("⬇ Download Licensing Report (DOCX)", data=lic_doc, file_name=lic_name, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="dl_lic")

        # Expert Checklist (DOCX)
        chk_doc = build_expert_checklist_docx(customer, ss.sector)
        chk_name = f"{customer}_Expert_Checklist_{_now_stamp()}.docx"
        chk_path = _save_bytes_to_server(case_folder, chk_name, chk_doc)
        st.download_button("⬇ Download Expert Checklist (DOCX)", data=chk_doc, file_name=chk_name, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="dl_chk")

        # IA Register (XLSX) — simple placeholder from the four-leaf presence
        items = []
        for leaf, present in ss.ic_map.items():
            items.append({
                "Asset Name": f"{leaf} Asset",
                "Type (4-Leaf)": leaf,
                "Owner": ss.customer_name,
                "Origin": "Evidence upload",
                "Evidence": "Detected in text" if present else "Not explicit",
                "Protection": "TBD",
                "Readiness (10-Steps)": f"{sum(ss.ten_steps.values())//10}/10",
                "Notes": "",
            })
        xls = build_register_xlsx(items)
        xls_name = f"{customer}_IA_Register_{_now_stamp()}.xlsx"
        xls_path = _save_bytes_to_server(case_folder, xls_name, xls)
        st.download_button("⬇ Download IA Register (XLSX)", data=xls, file_name=xls_name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_reg")

        st.info(f"Saved to server: `{case_folder}`")

elif page == "Licensing Templates":
    st.subheader("Licensing Templates (DOCX)")

    if not Document:
        st.error("python-docx is required for template generation. Add `python-docx` to requirements.")
    else:
        def _docx_simple(title: str, lines: List[str]) -> bytes:
            doc = Document()
            _doc_par(doc, title, bold=True)
            for ln in lines:
                _doc_par(doc, ln)
            bio = io.BytesIO()
            doc.save(bio)
            return bio.getvalue()

        customer = ss.customer_name
        case_folder = _server_folder_for_case(customer)

        std = _docx_simple(
            "Standard FRAND Licence",
            [
                "Scope: Field-of-use; territory; term.",
                "Fees: Fixed and/or royalty with caps; MFN across equivalent licensees.",
                "Audit: On request; reasonable notice; limited frequency.",
                "Termination: Material breach; audit failure; end-of-term.",
                "IPR: Ownership retained; no implied transfer; improvements clause optional.",
            ],
        )
        std_name = f"{customer}_FRAND_Standard_Licence_{_now_stamp()}.docx"
        _save_bytes_to_server(case_folder, std_name, std)
        st.download_button("⬇ FRAND Standard (DOCX)", data=std, file_name=std_name, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="tmpl_std")

        co = _docx_simple(
            "Co-Creation Licence Template",
            [
                "Contributions: Joint artefact register; contribution logs.",
                "Ownership: Joint/segmented per contribution; background IP preserved.",
                "Revenue: Proportional split; audit rights.",
                "Publication: Prior approval; confidentiality carve-outs.",
                "Exit: Buy-out or wind-down; survival of key clauses.",
            ],
        )
        co_name = f"{customer}_CoCreation_Licence_{_now_stamp()}.docx"
        _save_bytes_to_server(case_folder, co_name, co)
        st.download_button("⬇ Co-Creation (DOCX)", data=co, file_name=co_name, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="tmpl_co")

        nt = _docx_simple(
            "Non-Traditional Artefact Licence",
            [
                "Artefacts: Codified know-how, datasets, prompts, checklists.",
                "Use: Commercial or social-benefit variants; attribution rules.",
                "Fees: Fixed or outcome-based; carve-outs for public interest.",
                "Traceability: Evidence snapshots; renewal diary.",
                "Liability: As-is; reasonable skill and care.",
            ],
        )
        nt_name = f"{customer}_NonTraditional_Licence_{_now_stamp()}.docx"
        _save_bytes_to_server(case_folder, nt_name, nt)
        st.download_button("⬇ Non-Traditional (DOCX)", data=nt, file_name=nt_name, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="tmpl_nt")
