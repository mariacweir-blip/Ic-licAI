# app_clean.py — IC-LicAI Expert Console (clean rewrite, no external exporters)
# Safe, single-file app: DOCX generation is optional; falls back to TXT.

from __future__ import annotations
import io
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

import streamlit as st

# Optional DOCX support
try:
    from docx import Document  # type: ignore
    HAVE_DOCX = True
except Exception:
    HAVE_DOCX = False

# ===== Evidence Extraction (Step 1) =====
import re
from typing import Dict, List

# Optional imports for file text extraction. These will fail gracefully if a lib is missing.
try:
    from docx import Document as _DocxDocument  # python-docx
except Exception:
    _DocxDocument = None

try:
    from PyPDF2 import PdfReader as _PdfReader
except Exception:
    _PdfReader = None

try:
    from pptx import Presentation as _PptxPresentation  # python-pptx (optional)
except Exception:
    _PptxPresentation = None


FOUR_LEAF_KEYS = {
    "Human": [
        r"\bhuman capital\b", r"\btraining\b", r"\bcompetenc(e|y)\b",
        r"\bskills?\b", r"\bteams?\b", r"\bstaff\b"
    ],
    "Structural": [
        r"\bstructural capital\b", r"\bprocess(es)?\b", r"\bmethods?\b",
        r"\bprocedures?\b", r"\bsystems?\b", r"\bdocumentation\b", r"\bIPR?\b"
    ],
    "Customer": [
        r"\bcustomer capital\b", r"\bclients?\b", r"\busers?\b",
        r"\bcustomer contracts?\b", r"\bNPS\b", r"\bretention\b"
    ],
    "StrategicAlliance": [
        r"\bstrategic alliance(s)?\b", r"\bpartnership(s)?\b",
        r"\bJV\b", r"\bjoint venture\b", r"\bconsortium\b", r"\bMoU\b"
    ],
}

TEN_STEPS_KEYS = {
    "1 Identify":     [r"\bidentify\b", r"\bdiscovery\b", r"\bmapping\b"],
    "2 Separate":     [r"\bseparat(e|ion)\b", r"\bcarve-?out\b", r"\bclassif(y|ication)\b"],
    "3 Protect":      [r"\bprotect(ion)?\b", r"\bconfidential\b", r"\btrade secret\b", r"\bIP\b"],
    "4 Safeguard":    [r"\bsafeguard\b", r"\baccess control\b", r"\bauthorization\b"],
    "5 Manage":       [r"\bmanage(ment)?\b", r"\bgovernance\b", r"\bowner\b", r"\baccountability\b"],
    "6 Control":      [r"\bcontrol\b", r"\bversioning\b", r"\baudit trail\b"],
    "7 Develop":      [r"\bdevelop(ment)?\b", r"\broadmap\b", r"\bbacklog\b", r"\bR&D\b"],
    "8 Exploit":      [r"\bexploit(ation)?\b", r"\bmonetis(e|z)e\b", r"\blicens(?:e|ing)\b"],
    "9 Value":        [r"\bvalu(e|ation)\b", r"\bIAS ?38\b", r"\bfair value\b"],
    "10 Report":      [r"\breport(ing)?\b", r"\bdisclosure\b", r"\bregister\b"],
}

# Basic normalizer: lower-case and collapse whitespace
def _norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()

def _extract_matches(text: str, patterns: List[str], window: int = 300) -> List[str]:
    """
    Return short snippets around each match so experts can review in context.
    window = number of characters captured around the match.
    """
    snippets = []
    if not text:
        return snippets
    for pat in patterns:
        try:
            for m in re.finditer(pat, text, flags=re.IGNORECASE):
                start = max(0, m.start() - window // 2)
                end = min(len(text), m.end() + window // 2)
                snippet = text[start:end].strip()
                if snippet and snippet not in snippets:
                    snippets.append(snippet)
        except re.error:
            # If a regex is malformed, skip it
            continue
    return snippets

def extract_evidence_from_text(raw_text: str) -> Dict:
    """
    Classify free text into Four-Leaf and 10 Steps evidence buckets.
    Returns a dict:
    {
      "FourLeaf": {"Human": [...], "Structural": [...], "Customer": [...], "StrategicAlliance": [...]},
      "TenSteps": {"1 Identify":[...], ..., "10 Report":[...]},
    }
    """
    text = raw_text or ""
    four_leaf = {k: _extract_matches(text, pats) for k, pats in FOUR_LEAF_KEYS.items()}
    ten_steps = {k: _extract_matches(text, pats) for k, pats in TEN_STEPS_KEYS.items()}
    return {"FourLeaf": four_leaf, "TenSteps": ten_steps}

def read_text_from_uploaded_file(up_file) -> str:
    """
    Safely read text from an uploaded file-like object (Streamlit's UploadedFile).
    Supports: .txt, .docx, .pdf, .pptx (if python-pptx installed).
    Falls back to empty string on failure.
    """
    name = (up_file.name or "").lower()
    try:
        if name.endswith(".txt"):
            return up_file.read().decode("utf-8", errors="ignore")

        if name.endswith(".docx") and _DocxDocument is not None:
            up_file.seek(0)
            doc = _DocxDocument(up_file)
            return "\n".join(p.text for p in doc.paragraphs)

        if name.endswith(".pdf") and _PdfReader is not None:
            out = []
            up_file.seek(0)
            r = _PdfReader(up_file)
            for page in r.pages:
                try:
                    out.append(page.extract_text() or "")
                except Exception:
                    continue
            return "\n".join(out)

        if name.endswith(".pptx") and _PptxPresentation is not None:
            up_file.seek(0)
            prs = _PptxPresentation(up_file)
            slides = []
            for s in prs.slides:
                txt = []
                for shape in s.shapes:
                    if hasattr(shape, "text"):
                        txt.append(shape.text)
                slides.append("\n".join(txt))
            return "\n\n".join(slides)

    except Exception:
        pass

    # Unknown or failed parsing: best-effort binary decode
    try:
        up_file.seek(0)
        return up_file.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""
# ===== End Evidence Extraction (Step 1) =====

# ---------------- UI theme (Navy + Pale Yellow) ----------------
st.set_page_config(page_title="IC-LicAI Expert Console", layout="wide")

def inject_theme():
    st.markdown("""
    <style>
      .stApp { background: #FFF3BF; }
      .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1250px; }

      /* Title bar */
      .ic-title-bar{
        background:#0F2F56; color:#FFFFFF; padding:18px 22px;
        border-radius:10px; font-weight:800; font-size:34px; line-height:1.1;
        box-shadow:0 2px 6px rgba(0,0,0,0.08); letter-spacing:.2px;
        margin: 0 0 18px 0;
      }

      /* Section header */
      .ic-section-title{
        color:#0F2F56; font-weight:800; font-size:28px; margin:.25rem 0 1rem 0;
      }

      /* Card */
      .ic-card{
        background:#FFF7D6; border:1px solid #F0E2A6; border-radius:10px;
        padding:16px 18px; box-shadow:0 2px 6px rgba(0,0,0,0.05);
      }

      /* Sidebar */
      [data-testid="stSidebar"] { width: 280px; min-width: 280px; background:#0B2747; }
      [data-testid="stSidebar"] * { color:#DDE8F5 !important; }

      /* Sidebar buttons */
      [data-testid="stSidebar"] .stButton > button{
        width:100%; background:#163B69; color:#FFFFFF;
        border:1px solid #1D4D86; border-radius:12px;
        font-weight:800; padding:12px 14px; margin:6px 0 10px 0;
        box-shadow: inset 0 -2px 0 rgba(255,255,255,0.06), 0 1px 2px rgba(0,0,0,0.15);
      }
      [data-testid="stSidebar"] .stButton > button:hover{ background:#1D4D86; }

      /* Sidebar radio */
      [data-testid="stSidebar"] .stRadio > div[role='radiogroup'] label{
        background:transparent; border:1px solid transparent; padding:6px 2px;
        font-weight:700; color:#E8F1FF !important;
      }

      /* Inputs */
      .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        border-radius:8px;
      }
    </style>
    """, unsafe_allow_html=True)

inject_theme()

# ---------------- Constants & Session ----------------
SECTORS = [
    "Food & Beverage", "MedTech", "GreenTech", "AgriTech", "Biotech",
    "Software/SaaS", "FinTech", "EdTech", "Manufacturing", "Creative/Digital",
    "Professional Services", "Mobility/Transport", "Energy", "Other",
]
SIZES = ["Micro (1–10)", "Small (11–50)", "Medium (51–250)", "Large (250+)"]

ss = st.session_state
ss.setdefault("case_name", "Untitled Customer")
ss.setdefault("company_size", "Micro (1–10)")
ss.setdefault("sector", "Food & Beverage")
ss.setdefault("notes", "")
ss.setdefault("combined_text", "")
ss.setdefault("analysis", {})  # holds 4_leaf, ten_steps, market, innovation, ipr, business_model

# ---------------- Helpers ----------------
def read_textlike_uploads(files: Optional[List[Any]]) -> str:
    """Read only text-like files (txt) here to avoid cloud parsing surprises."""
    if not files:
        return ""
    chunks: List[str] = []
    for f in files:
        try:
            name = getattr(f, "name", "").lower()
            if name.endswith(".txt"):
                chunks.append(f.read().decode("utf-8", errors="ignore"))
            else:
                # safer demo: keep non-txt as filenames only
                chunks.append(f"[uploaded: {getattr(f,'name','file')}]")
        except Exception:
            pass
    return "\n".join([c for c in chunks if c])

def _blob_docx(title: str, body: str) -> Tuple[bytes, str, str]:
    """Return (bytes, filename, mime) as DOCX if available, else TXT."""
    safe_title = (title or "Report").replace("/", "_").replace("\\", "_")
    if HAVE_DOCX:
        doc = Document()
        doc.add_heading(title or "Report", level=1)
        for para in body.split("\n"):
            doc.add_paragraph(para)
        bio = io.BytesIO()
        doc.save(bio)
        return bio.getvalue(), f"{safe_title}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    # fallback TXT
    return body.encode("utf-8"), f"{safe_title}.txt", "text/plain"

def _title_bar(text: str):
    st.markdown(f'<div class="ic-title-bar">{text}</div>', unsafe_allow_html=True)

def _section_title(text: str):
    st.markdown(f'<div class="ic-section-title">{text}</div>', unsafe_allow_html=True)

# Compose report texts (clean, simple)
def compose_ic_report_text(bundle: Dict[str, Any]) -> Tuple[str, str]:
    title = f"IC Report — {bundle.get('case','Customer')}"
    lines = []
    lines.append("Cover")
    lines.append(f"Customer: {bundle.get('case','')}")
    lines.append(f"Sector: {bundle.get('sector','')}")
    lines.append(f"Size: {bundle.get('size','')}")
    lines.append("")
    lines.append("Disclaimer")
    lines.append("This is an advisory draft for expert review; no accounting advice is implied.")
    lines.append("")
    lines.append("Index")
    lines.append("1. Executive Summary")
    lines.append("2. Intellectual Asset Inventory")
    lines.append("3. Innovation Analysis")
    lines.append("4. Market Scenario")
    lines.append("5. Business Model")
    lines.append("6. Assumptions")
    lines.append("7. Valuation (placeholder)")
    lines.append("8. Conclusions")
    lines.append("9. Action Plan")
    lines.append("")
    lines.append("Executive Summary")
    lines.append(bundle.get("summary","This report summarises IC findings and next actions."))
    lines.append("")
    lines.append("Intellectual Asset Inventory (4-Leaf)")
    leaf = bundle.get("four_leaf", {})
    for k in ["Human","Structural","Customer","Strategic Alliance"]:
        v = leaf.get(k,"")
        if v:
            lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("10-Steps (Areopa) — readiness notes")
    steps = bundle.get("ten_steps", {})
    for i in range(1,11):
        key = f"Step {i}"
        v = steps.get(key,"")
        if v:
            lines.append(f"{key}: {v}")
    lines.append("")
    lines.append("Innovation Analysis")
    lines.append(bundle.get("innovation",""))
    lines.append("")
    lines.append("Market Scenario")
    lines.append(bundle.get("market",""))
    lines.append("")
    lines.append("Business Model")
    lines.append(bundle.get("business_model",""))
    lines.append("")
    lines.append("Assumptions")
    lines.append(bundle.get("assumptions",""))
    lines.append("")
    lines.append("Valuation (placeholder)")
    lines.append("Valuation to be produced under IAS 38 by authorised valuators.")
    lines.append("")
    lines.append("Conclusions")
    lines.append(bundle.get("conclusions",""))
    lines.append("")
    lines.append("Action Plan")
    lines.append(bundle.get("action_plan",""))
    return title, "\n".join(lines)

def compose_licensing_report_text(bundle: Dict[str, Any]) -> Tuple[str, str]:
    title = f"Licensing Report — {bundle.get('case','Customer')}"
    lines = []
    lines.append("Licensing-first Advisory")
    lines.append(f"Customer: {bundle.get('case','')}")
    lines.append(f"Sector: {bundle.get('sector','')}")
    lines.append("")
    lines.append("FRAND Readiness (high-level):")
    lines.append("- Fair & reasonable fees aligned with value and ability to pay.")
    lines.append("- Non-discrimination across licensees.")
    lines.append("- Governance: audit clause; essentiality check; termination terms.")
    lines.append("")
    lines.append("Candidate models:")
    lines.append("1) Revenue Licence — royalty or usage-based")
    lines.append("2) Defensive Licence — protective pooling / non-assertion in cluster")
    lines.append("3) Co-Creation Licence — foreground IP sharing; joint roadmap")
    lines.append("")
    lines.append("IC context (from 4-Leaf):")
    leaf = bundle.get("four_leaf", {})
    for k in ["Human","Structural","Customer","Strategic Alliance"]:
        v = leaf.get(k,"")
        if v:
            lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("Advisory narrative:")
    lines.append(bundle.get("narrative","Licensing options are aligned to the identified IC and market intents."))
    return title, "\n".join(lines)

def compose_template(template_name: str, case: str, sector: str) -> Tuple[str, str]:
    """Return (title, body) for a template."""
    t = template_name
    title = f"{t} — {case}"
    hdr = f"{t} (Sector: {sector})"
    if template_name == "FRAND Standard":
        body = (
            hdr + "\n\n"
            "1. Grant: Licensor grants a non-exclusive licence to defined IP and know-how.\n"
            "2. Field / Territory: as specified in Schedule A.\n"
            "3. Fees: FRAND-aligned royalty model; audit right; annual true-up.\n"
            "4. Essentiality & Non-discrimination: commitments recorded.\n"
            "5. Compliance: quality, safety, and reporting obligations.\n"
            "6. Term & Termination: material breach, insolvency, non-payment.\n"
            "7. Governance: dispute resolution; notice; change control.\n"
        )
    elif template_name == "Co-creation (Joint Development)":
        body = (
            hdr + "\n\n"
            "1. Purpose: joint development of Foreground IP with shared roadmap.\n"
            "2. Background IP: remains with the contributing party; licensed as needed.\n"
            "3. Foreground IP: joint ownership; exploitation shares per Schedule B.\n"
            "4. Confidentiality & Trade Secrets: strict protection and handling.\n"
            "5. Contributions & Milestones: effort and deliverables per workplan.\n"
            "6. Revenue Sharing: allocation model; reporting & audit.\n"
            "7. Exit & Continuity: step-in rights; buy-out formulas.\n"
        )
    else:  # Knowledge (Non-traditional)
        body = (
            hdr + "\n\n"
            "1. Subject Matter: codified knowledge (copyright, databases, GTI), training content.\n"
            "2. Scope: commercial or social-benefit use; attribution; moral rights noted.\n"
            "3. Licence: non-exclusive, limited term; sublicensing by consent.\n"
            "4. Fees: subscription / per-seat / outcome-based models.\n"
            "5. Safeguarding: integrity of knowledge artefacts; quality gates.\n"
            "6. Termination: misuse; breach; reputational risk clause.\n"
        )
    return title, body

def build_bundle_from_session() -> Dict[str, Any]:
    a: Dict[str, Any] = ss.get("analysis", {})
    return {
        "case": ss.get("case_name",""),
        "size": ss.get("company_size",""),
        "sector": ss.get("sector",""),
        "summary": a.get("summary",""),
        "four_leaf": a.get("four_leaf", {}),
        "ten_steps": a.get("ten_steps", {}),
        "market": a.get("market",""),
        "innovation": a.get("innovation",""),
        "business_model": a.get("business_model",""),
        "assumptions": a.get("assumptions",""),
        "conclusions": a.get("conclusions",""),
        "action_plan": a.get("action_plan",""),
        "narrative": a.get("narrative",""),
    }

# ---------------- Sidebar navigation ----------------
with st.sidebar:
    page = st.radio("Navigate", ["Customer","Analyse Evidence","Expert View","Reports"], index=0)
    st.button("IC Value Analysis")
    st.button("Licensing Reports & Templates")
    st.button("IC Report")
    st.button("Generate All Reports")
    st.caption("EU theme • Areopa/ARICC demo")

# ---------------- Title ----------------
_title_bar("IC-LicAI Expert Console")

# ---------------- Pages ----------------
if page == "Customer":
    _section_title("Customer details")
    st.markdown('<div class="ic-card">', unsafe_allow_html=True)

    with st.form("customer_form"):
        c1, c2 = st.columns(2)
        with c1:
            case_name = st.text_input("Customer / Company name", ss.get("case_name","Untitled Customer"))
            size = st.selectbox("Company size", SIZES, index=SIZES.index(ss.get("company_size","Micro (1–10)")))
        with c2:
            sector = st.selectbox("Sector / Industry", SECTORS, index=SECTORS.index(ss.get("sector","Food & Beverage")))
            notes = st.text_area("Quick notes (optional)", ss.get("notes",""), height=120)

        uploads = st.file_uploader(
            "Upload evidence (optional)",
            type=["pdf","docx","txt","csv","xlsx","pptx","png","jpg","jpeg"],
            accept_multiple_files=True,
            key="uploader_main",
        )
        submitted = st.form_submit_button("Save details")
        if submitted:
            ss["case_name"] = case_name or "Untitled Customer"
            ss["company_size"] = size
            ss["sector"] = sector
            ss["notes"] = notes or ""
            combined = read_textlike_uploads(uploads)
            if combined:
                ss["combined_text"] = combined
            st.success("Saved details.")

    st.markdown('</div>', unsafe_allow_html=True)
    st.info("Next: go to **Analyse Evidence** to auto-draft 4-Leaf and 10-Steps.")

elif page == "Analyse Evidence":
    _section_title("Analyse & build narrative (preview)")
    st.markdown('<div class="ic-card">', unsafe_allow_html=True)

    st.text_area("Preview extracted / combined evidence", ss.get("combined_text",""), height=220, key="txt_preview")

    if st.button("Run quick auto-analysis", key="btn_auto"):
        text = (ss.get("combined_text") or "").lower()

        def has_any(words: List[str]) -> bool:
            return any(w in text for w in words)

        human_words = ["team","training","skill","mentor","employee"]
        structural_words = ["process","system","software","method","ipr","trade secret","copyright","trademark"]
        customer_words = ["client","customer","partner","contract","channel"]
        strategic_words = ["alliance","mou","joint","collaboration"]

        four_leaf = {
            "Human": "Signals of people/skills present." if has_any(human_words) else "No strong human-capital signals detected yet.",
            "Structural": "Internal systems, IP or methods referenced." if has_any(structural_words) else "No clear structural artefacts found.",
            "Customer": "Evidence of client/partner relations." if has_any(customer_words) else "No customer/partner evidence detected.",
            "Strategic Alliance": "External collaborations or MOUs present." if has_any(strategic_words) else "No alliance evidence detected.",
        }

        ten_steps = {f"Step {i}": "" for i in range(1,11)}
        ten_steps["Step 1"] = "Identify: list core intangibles; tag Human/Structural/Customer/Strategic."
        ten_steps["Step 2"] = "Protect: confirm NDAs, filings, trade-secret coverage."
        ten_steps["Step 3"] = "Name: standard naming; version control; owners."
        ten_steps["Step 4"] = "Value: initial readiness narrative; evidence links."
        # (Keep steps 5-10 as placeholders to edit in Expert View)

        analysis = {
            "summary": "Auto-draft generated. Please refine in Expert View.",
            "four_leaf": four_leaf,
            "ten_steps": ten_steps,
            "market": "Market notes (placeholder).",
            "innovation": "Innovation notes (placeholder).",
            "business_model": "Business model notes (placeholder).",
            "assumptions": "Assumptions (placeholder).",
            "conclusions": "Conclusions (placeholder).",
            "action_plan": "Action plan (placeholder).",
            "narrative": "Licensing options will align to asset readiness and FRAND principles.",
        }
        ss["analysis"] = analysis
        st.success("Auto-analysis complete. Open **Expert View** to refine.")

    st.markdown('</div>', unsafe_allow_html=True)

elif page == "Expert View":
    _section_title("Expert View (edit & confirm)")
    st.markdown('<div class="ic-card">', unsafe_allow_html=True)
    a = ss.get("analysis", {})
    leaf = a.get("four_leaf", {})
    steps = a.get("ten_steps", {})

    c1, c2 = st.columns(2)
    with c1:
        ss["leaf_human"] = st.text_area("Human Capital", leaf.get("Human",""), height=120)
        ss["leaf_structural"] = st.text_area("Structural Capital", leaf.get("Structural",""), height=120)
    with c2:
        ss["leaf_customer"] = st.text_area("Customer Capital", leaf.get("Customer",""), height=120)
        ss["leaf_strategic"] = st.text_area("Strategic Alliance Capital", leaf.get("Strategic Alliance",""), height=120)

    st.markdown("---")
    st.write("**10-Steps (Areopa):**")
    for i in range(1,11):
        key = f"Step {i}"
        ss[f"ts_{i}"] = st.text_area(key, steps.get(key,""), height=80)

    st.markdown("---")
    ss["market"] = st.text_area("Market Analysis", a.get("market",""), height=120)
    ss["innovation"] = st.text_area("Innovation Analysis", a.get("innovation",""), height=120)
    ss["business_model"] = st.text_area("Business Model", a.get("business_model",""), height=120)
    ss["assumptions"] = st.text_area("Assumptions for Action Plan", a.get("assumptions",""), height=120)
    ss["conclusions"] = st.text_area("Conclusions", a.get("conclusions",""), height=100)
    ss["action_plan"] = st.text_area("Action Plan", a.get("action_plan",""), height=120)
    ss["narrative"] = st.text_area("Licensing Narrative", a.get("narrative",""), height=100)

    if st.button("Save expert edits", key="btn_save_expert"):
        ss["analysis"] = {
            "summary": "Expert-refined narrative saved.",
            "four_leaf": {
                "Human": ss.get("leaf_human",""),
                "Structural": ss.get("leaf_structural",""),
                "Customer": ss.get("leaf_customer",""),
                "Strategic Alliance": ss.get("leaf_strategic",""),
            },
            "ten_steps": {f"Step {i}": ss.get(f"ts_{i}","") for i in range(1,11)},
            "market": ss.get("market",""),
            "innovation": ss.get("innovation",""),
            "business_model": ss.get("business_model",""),
            "assumptions": ss.get("assumptions",""),
            "conclusions": ss.get("conclusions",""),
            "action_plan": ss.get("action_plan",""),
            "narrative": ss.get("narrative",""),
        }
        st.success("Expert edits saved.")

    st.markdown('</div>', unsafe_allow_html=True)

elif page == "Reports":
    _section_title("Reports & Templates (editable DOCX or TXT)")
    st.markdown('<div class="ic-card">', unsafe_allow_html=True)
    bundle = build_bundle_from_session()
    bundle.setdefault("sector", ss.get("sector",""))
    bundle.setdefault("size", ss.get("company_size",""))
    bundle.setdefault("case", ss.get("case_name",""))

    c1, c2 = st.columns(2)
    with c1:
        # IC Report
        t, body = compose_ic_report_text(bundle)
        data, fname, mime = _blob_docx(t, body)
        st.download_button("Download IC Report", data=data, file_name=fname, mime=mime, key="dl_ic")

    with c2:
        # Licensing Report
        t2, body2 = compose_licensing_report_text(bundle)
        data2, fname2, mime2 = _blob_docx(t2, body2)
        st.download_button("Download Licensing Report", data=data2, file_name=fname2, mime=mime2, key="dl_lic")

    st.markdown("---")
    st.write("**Licensing Templates**")
    tmpl = st.selectbox("Choose a template", ["FRAND Standard","Co-creation (Joint Development)","Knowledge (Non-traditional)"], index=0, key="tmpl_sel")
    if st.button("Generate Template", key="btn_make_tmpl"):
        tt, bb = compose_template(tmpl, ss.get("case_name","Customer"), ss.get("sector",""))
        d3, fn3, mm3 = _blob_docx(tt, bb)
        st.download_button("Download Template", data=d3, file_name=fn3, mime=mm3, key="dl_tmpl")

    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.info("Select a page in the sidebar.")
