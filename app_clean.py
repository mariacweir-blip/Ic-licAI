# app_clean.py — IC-LicAI Expert Console (EU theme, SME-friendly)
# Single-file Streamlit app. Paste this entire file into your repo.
# Requirements (in requirements.txt):
#   streamlit>=1.36
#   python-docx>=1.1  (optional; will fall back to .txt if missing)

from __future__ import annotations
import io
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Tuple

import streamlit as st

# -------- Optional DOCX support (falls back to .txt if missing) --------
try:
    from docx import Document  # type: ignore
    HAVE_DOCX = True
except Exception:
    HAVE_DOCX = False

# ================= UI THEME (Navy + Pale Yellow) =================
st.set_page_config(page_title="IC-LicAI Expert Console", layout="wide")

def _inject_theme() -> None:
    st.markdown(
        """
        <style>
          /* page bg */
          .stApp { background:#FFF3BF; }
          .block-container { max-width:1250px; padding-top:1.2rem; padding-bottom:2rem; }

          /* title */
          .ic-title-bar{
            background:#0F2F56; color:#FFFFFF; font-weight:800; font-size:34px;
            padding:18px 22px; border-radius:10px; letter-spacing:.2px; margin:10px 0 24px 0;
            box-shadow:0 2px 6px rgba(0,0,0,.08);
          }

          /* section card */
          .ic-card{
            background:#FFF7CF; border:1px solid #E6DFA8; border-radius:8px;
            padding:18px; margin:8px 0 14px 0;
          }

          /* navy buttons */
          .stButton>button {
            background:#0F2F56 !important; color:#fff !important; border-radius:8px !important;
            border:0 !important; padding:.55rem 1rem !important; font-weight:700 !important;
          }

          /* sidebar */
          section[data-testid="stSidebar"] { background:#0F2F56; }
          section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] p,
          section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] span {
            color:#E7F0FF !important;
          }
          .stRadio div[role="radiogroup"] label { color:#E7F0FF !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

_inject_theme()
st.markdown('<div class="ic-title-bar">IC-LicAI Expert Console</div>', unsafe_allow_html=True)

# ================= Writable root (robust against /srv/shared) =================
def _detect_writable_root() -> Path:
    """
    Choose a writable folder in Streamlit Cloud / local without touching /srv/shared.
    Order: ./out  →  $HOME/out  →  tmpdir/ic-licai
    """
    candidates = [
        Path("./out"),
        Path(os.path.expanduser("~")) / "out",
        Path(tempfile.gettempdir()) / "ic-licai-out",
    ]
    for p in candidates:
        try:
            p.mkdir(parents=True, exist_ok=True)
            test = p / ".touch"
            test.write_text("ok", encoding="utf-8")
            test.unlink(missing_ok=True)
            return p
        except Exception:
            continue
    # As a last resort, return a temp dir (no guarantee but better than crashing)
    return Path(tempfile.gettempdir())

OUT_ROOT = _detect_writable_root()

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _safe_filename(name: str) -> str:
    return "".join(c for c in (name or "").strip() if c.isalnum() or c in (" ", "_", "-", ".")).strip().replace(" ", "_")

def _export_bytes_as_docx_or_txt(title: str, body: str) -> Tuple[bytes, str, str]:
    """
    Returns (data, filename, mimetype) — uses DOCX if available, else TXT.
    """
    base = _safe_filename(title) or "ICLicAI_Report"
    if HAVE_DOCX:
        doc = Document()
        doc.add_heading(title, 0)
        for para in body.split("\n\n"):
            doc.add_paragraph(para)
        bio = io.BytesIO()
        doc.save(bio)
        return bio.getvalue(), f"{base}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        data = body.encode("utf-8")
        return data, f"{base}.txt", "text/plain"

def _save_bytes_to_server(folder: Path, std_name: str, data: bytes) -> Tuple[Path | None, str]:
    """
    Save under a writable root. Never crash on PermissionError — return (path_or_None, message).
    """
    try:
        _ensure_dir(folder)
        p = folder / std_name
        p.write_bytes(data)
        return p, f"Saved to {p}"
    except Exception as e:
        return None, f"Server save skipped ({type(e).__name__}: {e}). Download still works."

# ================= Evidence extraction (demo-safe) =================
TEXT_EXT = {".txt", ".csv"}

def _read_text_from_uploads(files: List[st.runtime.uploaded_file_manager.UploadedFile]) -> str:
    chunks: List[str] = []
    for f in files or []:
        name = f.name
        ext = Path(name.lower()).suffix
        try:
            if ext in TEXT_EXT:
                chunks.append(f.read().decode("utf-8", errors="ignore"))
            else:
                # For PDFs/DOCX/PPTX/images etc. the demo uses filename cues only
                chunks.append(f"[[FILE:{name}]]")
        except Exception:
            chunks.append(f"[[FILE:{name}]]")
    return "\n".join(chunks)

# ================= SME-friendly heuristics =================
FOUR_LEAF_KEYS = {
    "Human": [
        # people & skills (SME wording)
        "team","staff","employee","hire","recruit","training","trained","trainer","onboarding",
        "mentor","apprentice","nvq","cscs","cim","cips","qualification","certified","cpd",
        "safety training","toolbox talk","shift rota","skills matrix"
    ],
    "Structural": [
        # processes, systems, IP registers (no IC jargon needed)
        "process","processes","procedure","sop","workflow","policy","template","checklist",
        "system","crm","erp","sharepoint","database","knowledge base","qms","iso 9001","iso 27001",
        "ip register","asset register","method","spec","playbook","datasheet","architecture"
    ],
    "Customer": [
        # contracts, pipeline, channel
        "client","customer","account","lead","opportunity","pipeline","crm","quote","proposal",
        "contract","msa","sow","sla","purchase order","po","invoice","renewal","retention",
        "distributor","reseller","channel","customer success","nps","churn"
    ],
    "Strategic Alliance": [
        # partners, universities, councils, grants, JV/MoU
        "partner","partnership","alliance","strategic","mou","memorandum of understanding","joint venture",
        "framework agreement","collaboration","consortium","university","college","council","ngo",
        "integrator","oem","supplier agreement","grant agreement","licensor","licensee"
    ],
}

TEN_STEPS = ["Identify","Separate","Protect","Safeguard","Manage","Control","Use","Monitor","Value","Report"]

# Sector-specific cues (extendable)
SECTOR_CUES = {
    "GreenTech": [
        "recycling","recycled","waste","anaerobic","biomass","compost","circular","emissions","co2e",
        "solar","pv","turbine","kwh","energy efficiency","retrofit","heat pump","iso 14001","esg","sdg",
        "defra","ofgem","innovate uk","feasibility study","lca"
    ],
    # Add more sectors easily: "MedTech": [...], "AgriTech": [...]
}

def _analyse_to_maps(text: str) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    """
    Returns (ic_map, ten_steps_map, summary_text)
    ic_map:  { leaf: {tick: bool, narrative: str} }
    ten_steps_map: { 'scores': List[int], 'narratives': List[str] }
    """
    t = (text or "").lower()
    sector = st.session_state.get("sector","Other")

    # ---- Four-Leaf with SME cues + sector cues mixed in where relevant
    ic_map: Dict[str, Any] = {}
    for leaf, cues in FOUR_LEAF_KEYS.items():
        effective_cues = list(cues)
        if sector in SECTOR_CUES and leaf in ("Structural","Customer","Strategic Alliance"):
            effective_cues += SECTOR_CUES[sector]
        hit = any(c in t for c in effective_cues)

        if leaf == "Human":
            nar = ("Human Capital evidenced (people, roles, training, qualifications)."
                   if hit else "No strong people/skills cues detected in evidence.")
        elif leaf == "Structural":
            nar = ("Structural Capital present (SOPs/processes/systems/registers/ISO/QMS)."
                   if hit else "No explicit systems/processes/registers referenced.")
        elif leaf == "Customer":
            nar = ("Customer Capital indicated (contracts/POs/CRM/pipeline/channels)."
                   if hit else "Little/no explicit evidence of customer relationships.")
        else:
            nar = ("Strategic alliances present (partners/MoUs/JVs/universities/councils/grants)."
                   if hit else "No clear references to strategic partners/alliances.")
        ic_map[leaf] = {"tick": hit, "narrative": nar}

    # ---- Ten-Steps scoring with SME-friendly boosters
    base = 3
    boosts = {
        "Identify": 2 if any(w in t for w in ["asset","intangible","know-how","knowhow","dataset","algorithm"]) else 0,
        "Separate": 2 if any(w in t for w in ["register","inventory","taxonomy","asset list"]) else 0,
        "Protect": 3 if any(w in t for w in [
            "nda","non-disclosure","confidentiality","trade secret","copyright","trademark","®","™","patent"]) else 0,
        "Safeguard": 2 if any(w in t for w in ["backup","version control","encryption","access control","retention"]) else 0,
        "Manage": 2 if any(w in t for w in ["sop","policy","owner","raci","governance","qms"]) else 0,
        "Control": 2 if any(w in t for w in ["rights","ownership","assign","exclusive","non-exclusive"]) else 0,
        "Use": 3 if any(w in t for w in [
            "licence","license","oem","white label","royalty","subscription","per seat","saas","pricing"]) else 0,
        "Monitor": 2 if any(w in t for w in ["kpi","dashboard","audit","monthly report","iso audit"]) else 0,
        "Value": 3 if any(w in t for w in ["valuation","pricing model","ias 38","frs 102","amortisation","fair value"]) else 0,
        "Report": 2 if any(w in t for w in ["board pack","management report","investor update","governance report"]) else 0,
    }
    # small sector influence (e.g., GreenTech evidence suggests more use/report structure)
    if sector in SECTOR_CUES and any(c in t for c in SECTOR_CUES[sector]):
        boosts["Use"] = max(boosts["Use"], 1)
        boosts["Report"] = max(boosts["Report"], 1)

    scores, narratives = [], []
    for step in TEN_STEPS:
        s = max(1, min(10, base + boosts.get(step, 0)))
        scores.append(s)
        narratives.append(f"{step}: readiness ≈ {s}/10 based on SME-language cues in evidence.")
    ten = {"scores": scores, "narratives": narratives}

    # ---- Summary written in plain business language
    ticks = [k for k, v in ic_map.items() if v["tick"]]
    gaps  = [k for k, v in ic_map.items() if not v["tick"]]
    summary = (
        f"{st.session_state.get('case_name','Untitled Customer')} is a "
        f"{st.session_state.get('company_size','Micro (1–10)')} in {sector}.\n"
        f"Evidence suggests: {', '.join(ticks) if ticks else 'no obvious IC signals'}"
        f"{'; gaps: ' + ', '.join(gaps) if gaps else ''}.\n"
        "Ten-Steps scores are heuristic – experts should review and adjust."
    )
    return ic_map, ten, summary

# ================= Session defaults =================
ss = st.session_state
ss.setdefault("case_name", "Untitled Customer")
ss.setdefault("company_size", "Micro (1–10)")
ss.setdefault("sector", "Other")
ss.setdefault("notes", "")
ss.setdefault("uploads", [])
ss.setdefault("combined_text", "")
ss.setdefault("ic_map", {})
ss.setdefault("ten_steps", {})
ss.setdefault("narrative", "")

SIZES = ["Micro (1–10)", "Small (11–50)", "Medium (51–250)", "Large (250+)"]
SECTORS = [
    "Food & Beverage","MedTech","GreenTech","AgriTech","Biotech",
    "Software/SaaS","FinTech","EdTech","Manufacturing","Creative/Digital",
    "Professional Services","Mobility/Transport","Energy","Other",
]

# ================= Sidebar =================
st.sidebar.markdown("### Navigate")
page = st.sidebar.radio(
    "",
    ("Customer", "Analyse Evidence", "Expert View", "Reports", "Licensing Templates"),
    index=0,
    key="nav",
)

# ================= PAGES =================

# -- 1) Customer
if page == "Customer":
    with st.container():
        st.header("Customer details")
        with st.form("customer_form"):
            c1, c2, c3 = st.columns([1.1, 1, 1])
            with c1:
                case_name = st.text_input("Customer / Company name", ss.get("case_name", ""))
            with c2:
                size = st.selectbox("Company size", SIZES, index=SIZES.index(ss.get("company_size", SIZES[0])))
            with c3:
                sector = st.selectbox("Sector / Industry", SECTORS, index=SECTORS.index(ss.get("sector", "Other")))

            notes = st.text_area("Analyst notes (optional)", value=ss.get("notes", ""), height=120)

            st.markdown("---")
            st.caption("Uploads are held in session until you analyse. Nothing is written to server until you export.")
            uploads = st.file_uploader(
                "Upload evidence (PDF, DOCX, TXT, CSV, XLSX, PPTX, images)",
                type=["pdf","docx","txt","csv","xlsx","pptx","png","jpg","jpeg","webp"],
                accept_multiple_files=True,
                key="uploader_main",
            )
            submitted = st.form_submit_button("Save details")
            if submitted:
                ss["case_name"] = case_name or "Untitled Customer"
                ss["company_size"] = size
                ss["sector"] = sector
                ss["notes"] = notes
                if uploads:
                    ss["uploads"] = uploads
                st.success("Saved customer details.")

    if ss.get("uploads"):
        st.info(f"{len(ss['uploads'])} file(s) stored in session. Go to **Analyse Evidence** next.")

# -- 2) Analyse Evidence
elif page == "Analyse Evidence":
    st.header("Analyse & build narrative (preview)")
    combined = ss.get("combined_text", "")
    st.text_area("Preview extracted / combined evidence (first 5000 chars)", combined[:5000], height=200, key="combined_preview")

    if st.button("Run analysis now"):
        uploads: List = ss.get("uploads") or []
        combined_text = _read_text_from_uploads(uploads)
        if ss.get("notes"):
            combined_text = (combined_text + "\n\n" + ss["notes"]).strip()
        ss["combined_text"] = combined_text

        ic_map, ten_steps, summary = _analyse_to_maps(combined_text)
        ss["ic_map"]  = ic_map
        ss["ten_steps"] = ten_steps
        ss["narrative"] = summary
        st.success("Analysis complete. Open **Expert View** to refine and export.")

# -- 3) Expert View
elif page == "Expert View":
    st.header("Narrative Summary")
    nar = st.text_area("Summary (editable)", value=ss.get("narrative",""), height=160, key="nar_edit")
    ss["narrative"] = nar

    colA, colB = st.columns([1,1])
    with colA:
        st.subheader("4-Leaf Map")
        ic_map: Dict[str, Any] = ss.get("ic_map", {})
        for leaf in ["Human","Structural","Customer","Strategic Alliance"]:
            row = ic_map.get(leaf, {"tick": False, "narrative": f"No assessment yet for {leaf}."})
            tick = "✓" if row["tick"] else "•"
            st.markdown(f"- **{leaf}**: {tick}")
            st.caption(row["narrative"])

        st.subheader("Market & Innovation")
        t = (ss.get("combined_text","").lower())
        st.markdown(f"- Sector Mentioned: {'Yes' if ss.get('sector','Other').lower() in t else 'Likely'}")
        st.markdown(f"- Innovation Signals: {'Yes' if any(w in t for w in ['innov','novel','patent','prototype']) else 'Possible'}")
        st.markdown(f"- Business Model Cues: {'Yes' if any(w in t for w in ['saas','licen','royalt','subscription']) else 'Possible'}")

    with colB:
        st.subheader("10-Steps Readiness")
        ten = ss.get("ten_steps", {"scores":[5]*10, "narratives":[f"{s}: tbd" for s in TEN_STEPS]})
        st.dataframe(
            {"Step": TEN_STEPS, "Score (1-10)": ten["scores"]},
            hide_index=True, use_container_width=True
        )
        with st.expander("Narrative per step"):
            for s, n in zip(TEN_STEPS, ten["narratives"]):
                st.markdown(f"**{s}** — {n}")

        st.subheader("IPR & ESG")
        st.markdown("- IPR cues: NDA/License/Trademark/Copyright/Trade Secret/Patent (auto-detected if present).")
        st.markdown("- ESG → ValuCompass: CSV artefacts can be mapped to IC and valued under IAS 38 (later step).")

# -- 4) Reports & Exports
elif page == "Reports":
    st.header("Reports & Exports")
    case_name   = ss.get("case_name","Untitled_Customer")
    case_folder = OUT_ROOT / _safe_filename(case_name)

    def _compose_ic_text() -> Tuple[str,str]:
        title = f"IC Report — {case_name}"
        ic_map = ss.get("ic_map", {})
        ten    = ss.get("ten_steps", {"scores":[5]*10, "narratives":[f"{s}: tbd" for s in TEN_STEPS]})
        body = []
        body.append(f"Executive Summary\n\n{ss.get('narrative','(no summary)')}\n")
        body.append("Four-Leaf Analysis")
        for leaf in ["Human","Structural","Customer","Strategic Alliance"]:
            row = ic_map.get(leaf, {"tick": False, "narrative": ""})
            body.append(f"- {leaf}: {'✓' if row.get('tick') else '•'} — {row.get('narrative','')}")
        body.append("\nTen-Steps Readiness")
        for s, n in zip(TEN_STEPS, ten["narratives"]):
            body.append(f"- {n}")
        body.append("\nAssumptions & Action Plan (to be agreed with customer)")
        body.append("• Draft assumptions placeholder.\n• Initial actions placeholder.\n")
        return title, "\n".join(body)

    def _compose_lic_text() -> Tuple[str,str]:
        title = f"Licensing Report — {case_name}"
        body = []
        body.append(f"Licensing Options & FRAND Readiness for {case_name}\n")
        body.append("Models:")
        body.append("- Revenue licence (royalties, FRAND-aligned terms, annual audit clause)")
        body.append("- Defensive licence (IP pooling, non-assert across partners)")
        body.append("- Co-creation licence (shared ownership of Foreground IP, revenue-sharing)")
        body.append("\nGovernance & Audit")
        body.append("This report is advisory-first with human approval. Evidence should be recorded in an IA Register.")
        return title, "\n".join(body)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Generate IC Report (DOCX/TXT)", key="btn_ic"):
            title, body = _compose_ic_text()
            data, fname, mime = _export_bytes_as_docx_or_txt(title, body)
            # server save (best effort)
            path, msg = _save_bytes_to_server(case_folder, fname, data)
            st.download_button("⬇️ Download IC Report", data, file_name=fname, mime=mime, key="dl_ic")
            (st.success if path else st.warning)(msg)

    with c2:
        if st.button("Generate Licensing Report (DOCX/TXT)", key="btn_lic"):
            title, body = _compose_lic_text()
            data, fname, mime = _export_bytes_as_docx_or_txt(title, body)
            path, msg = _save_bytes_to_server(case_folder, fname, data)
            st.download_button("⬇️ Download Licensing Report", data, file_name=fname, mime=mime, key="dl_lic")
            (st.success if path else st.warning)(msg)

    st.caption(f"Server save root: {OUT_ROOT}. If saving is restricted, the download still works.")

# -- 5) Licensing Templates
elif page == "Licensing Templates":
    st.header("Licensing Templates (editable DOCX/TXT)")
    case   = ss.get("case_name","Untitled Customer")
    sector = ss.get("sector","Other")

    template = st.selectbox(
        "Choose a template:",
        ["FRAND Standard","Co-creation (Joint Development)","Knowledge (Non-traditional)"],
        index=0
    )

    if st.button("Generate template", key="btn_make_template"):
        if template == "FRAND Standard":
            title = f"FRAND Standard template — {case}"
            body  = (
                f"FRAND Standard — {case} ({sector})\n\n"
                "Scope, definitions, essentiality clause, non-discrimination clause, reasonable fee corridor, "
                "audit & verification, termination, governing law (EU), dispute resolution.\n"
            )
        elif template == "Co-creation (Joint Development)":
            title = f"Co-creation template — {case}"
            body  = (
                f"Co-creation / Joint Development — {case} ({sector})\n\n"
                "Background IP, Foreground IP, contributions, ownership split, publication rights, "
                "commercial model, revenue sharing, exit/assignment, FRAND alignment where applicable.\n"
            )
        else:
            title = f"Knowledge licence (non-traditional) — {case}"
            body  = (
                f"Knowledge Licence — {case} ({sector})\n\n"
                "Codified know-how (copyright/trade secret), permitted fields of use, attribution, "
                "commercial vs social-benefit pathways, verification, revocation, jurisdiction.\n"
            )

        data, fname, mime = _export_bytes_as_docx_or_txt(title, body)
        folder = OUT_ROOT / _safe_filename(case)
        path, msg = _save_bytes_to_server(folder, fname, data)
        st.download_button("⬇️ Download Template", data, file_name=fname, mime=mime, key="dl_tpl")
        (st.success if path else st.warning)(msg)
