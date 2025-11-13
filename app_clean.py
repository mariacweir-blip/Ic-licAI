# app_clean.py — IC-LicAI Expert Console (Locked Build + Evidence Dashboard/Radar)
# Adds: DOCX/PPTX extraction, weighted IC signal engine, interpreted narrative,
# improved evidence meter, expert-context fusion, defensive handling for ten_steps,
# and a visual Evidence Dashboard (bar chart + radar) on Page 2.

from __future__ import annotations
import io, os, tempfile
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import streamlit as st
import plotly.graph_objects as go  # NEW: for bar + radar charts

# -------------------- MODE / AUTH --------------------
PUBLIC_MODE: bool = False       # False = internal (richer text + watermark + server save)
REQUIRE_PASS: bool = True       # Passphrase gate if APP_KEY is set

# ---------------- DOCX/PPTX optional ----------------
HAVE_DOCX = False
HAVE_PPTX = False
try:
    from docx import Document  # type: ignore
    HAVE_DOCX = True
except Exception:
    HAVE_DOCX = False

try:
    from pptx import Presentation  # type: ignore
    HAVE_PPTX = True
except Exception:
    HAVE_PPTX = False

# ------------------ THEME ----------------------------
st.set_page_config(page_title="IC-LicAI Expert Console", layout="wide")
st.markdown("""
<style>
  .stApp { background:#FFF3BF; }
  .block-container { max-width:1250px; padding-top:1.2rem; padding-bottom:2rem; }
  .ic-title-bar{ background:#0F2F56; color:#fff; font-weight:800; font-size:34px;
    padding:18px 22px; border-radius:10px; letter-spacing:.2px; margin:10px 0 24px 0;
    box-shadow:0 2px 6px rgba(0,0,0,.08); }
  .stButton>button { background:#0F2F56!important; color:#fff!important; border-radius:8px!important;
    border:0!important; padding:.55rem 1rem!important; font-weight:700!important; }
  section[data-testid="stSidebar"] { background:#0F2F56; }
  section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] p,
  section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] span { color:#E7F0FF!important; }
  .stRadio div[role="radiogroup"] label { color:#E7F0FF!important; }
</style>
""", unsafe_allow_html=True)
st.markdown('<div class="ic-title-bar">IC-LicAI Expert Console</div>', unsafe_allow_html=True)

# ------------------ AUTH GATE ------------------------
def _auth_gate() -> None:
    if not REQUIRE_PASS:
        return
    secret = st.secrets.get("APP_KEY", None) or os.environ.get("APP_KEY", None)
    if not secret:
        with st.expander("Access control"):
            st.info("Optional passphrase: set st.secrets['APP_KEY'] or env APP_KEY.")
        return
    key = st.text_input("Enter access passphrase", type="password")
    if not key:
        st.stop()
    if key != secret:
        st.error("Incorrect passphrase.")
        st.stop()

_auth_gate()

# --------------- WRITABLE ROOT -----------------------
def _detect_writable_root() -> Path:
    for p in [Path("./out"), Path(os.path.expanduser("~")) / "out", Path(tempfile.gettempdir()) / "ic-licai-out"]:
        try:
            p.mkdir(parents=True, exist_ok=True)
            t = p / ".touch"
            t.write_text("ok", encoding="utf-8")
            t.unlink()
            return p
        except Exception:
            continue
    return Path(tempfile.gettempdir())

OUT_ROOT = _detect_writable_root()


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _safe(name: str) -> str:
    return "".join(c for c in (name or "").strip() if c.isalnum() or c in (" ", "_", "-", ".")).strip().replace(" ", "_")


def _export_bytes(title: str, body: str) -> Tuple[bytes, str, str]:
    base = _safe(title) or "ICLicAI_Report"
    if HAVE_DOCX:
        doc = Document()
        if not PUBLIC_MODE:
            doc.add_paragraph().add_run("CONFIDENTIAL — Internal Evaluation Draft (No Distribution)").bold = True
        doc.add_heading(title, 0)
        for para in body.split("\n\n"):
            doc.add_paragraph(para)
        bio = io.BytesIO()
        doc.save(bio)
        return bio.getvalue(), f"{base}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if not PUBLIC_MODE:
        body = "CONFIDENTIAL — Internal Evaluation Draft (No Distribution)\n\n" + body
    return body.encode("utf-8"), f"{base}.txt", "text/plain"


def _save_bytes(folder: Path, name: str, data: bytes) -> Tuple[Optional[Path], str]:
    if PUBLIC_MODE:
        return None, "Public mode: server save disabled (download only)."
    try:
        _ensure_dir(folder)
        p = folder / name
        p.write_bytes(data)
        return p, f"Saved to {p}"
    except Exception as e:
        return None, f"Server save skipped ({type(e).__name__}: {e}). Download still works."


# --------------- EVIDENCE EXTRACTION -----------------
TEXT_EXT = {".txt", ".csv"}
DOCX_EXT = {".docx"}
PPTX_EXT = {".pptx"}
PDF_EXT = {".pdf"}  # filename cue only (kept for future)


def _extract_text_docx(data: bytes) -> str:
    if not HAVE_DOCX:
        return ""
    try:
        bio = io.BytesIO(data)
        doc = Document(bio)
        parts: List[str] = []
        # headings & paragraphs
        for p in doc.paragraphs:
            txt = (p.text or "").strip()
            if txt:
                parts.append(txt)
        # simple tables
        for tbl in getattr(doc, "tables", []):
            for row in tbl.rows:
                line = " | ".join((cell.text or "").strip() for cell in row.cells)
                if line.strip():
                    parts.append(line)
        return "\n".join(parts)
    except Exception:
        return ""


def _extract_text_pptx(data: bytes) -> str:
    if not HAVE_PPTX:
        return ""
    try:
        bio = io.BytesIO(data)
        prs = Presentation(bio)
        parts: List[str] = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    txt = (shape.text or "").strip()
                    if txt:
                        parts.append(txt)
            # notes
            if getattr(slide, "has_notes_slide", False) and slide.notes_slide:
                nt = (slide.notes_slide.notes_text_frame.text or "").strip()
                if nt:
                    parts.append(nt)
        return "\n".join(parts)
    except Exception:
        return ""


def _read_text(files: List[Any]) -> Tuple[str, Dict[str, int], Dict[str, float]]:
    """
    Returns (combined_text, counts_by_ext, weights_used)
    Weights depend on artefact type (contract/JV > SOP/KMP > specs/slides > culture).
    """
    chunks: List[str] = []
    counts: Dict[str, int] = {}
    weights_used: Dict[str, float] = {}

    # Artefact weights (desc)
    NAME_WEIGHTS: List[Tuple[str, float]] = [
        ("contract", 1.0), ("msa", 1.0), ("sow", 0.9), ("sla", 0.9),
        ("joint venture", 1.0), ("joint_venture", 1.0), ("jv", 1.0), ("mou", 1.0),
        ("grant", 0.9), ("licence", 0.9), ("license", 0.9),
        ("knowledge_management", 0.8), ("kmp", 0.8), ("sop", 0.8), ("process", 0.8), ("safety", 0.8),
        ("protocol", 0.8),
        ("spec", 0.6), ("canvas", 0.6), ("bmc", 0.6), ("slides", 0.6), ("deck", 0.6),
        ("culture", 0.4), ("award", 0.4)
    ]
    EXT_DEFAULTS: Dict[str, float] = {".docx": 0.7, ".pptx": 0.6, ".txt": 0.5, ".csv": 0.5, ".pdf": 0.4}

    for f in files or []:
        name = getattr(f, "name", "file")
        lower_name = str(name).lower()
        ext = Path(lower_name).suffix or "none"
        counts[ext] = counts.get(ext, 0) + 1

        # choose weight by filename cue first
        weight = EXT_DEFAULTS.get(ext, 0.4)
        for cue, w in NAME_WEIGHTS:
            if cue in lower_name:
                weight = max(weight, w)

        weights_used[lower_name] = weight

        try:
            raw = f.read()
            text = ""
            if ext in TEXT_EXT:
                text = raw.decode("utf-8", errors="ignore")
            elif ext in DOCX_EXT:
                text = _extract_text_docx(raw)
            elif ext in PPTX_EXT:
                text = _extract_text_pptx(raw)
            elif ext in PDF_EXT:
                text = f"[[PDF:{name}]]"
            else:
                text = f"[[FILE:{name}]]"

            if text.strip():
                chunks.append(f"\n# {name}\n{text.strip()}\n")
            else:
                chunks.append(f"\n# {name}\n[[NO-TEXT-EXTRACTED]]\n")
        except Exception:
            chunks.append(f"\n# {name}\n[[READ-ERROR]]\n")

    return "\n".join(chunks).strip(), counts, weights_used


# --------------- SME cues / analysis -----------------
FOUR_LEAF_KEYS: Dict[str, List[str]] = {
    "Human": [
        "team", "staff", "employee", "hire", "recruit", "training", "trained", "trainer", "onboarding", "mentor",
        "apprentice", "qualification", "certified", "cpd", "skills matrix", "safety training", "toolbox talk", "rota"
    ],
    "Structural": [
        "process", "procedure", "sop", "workflow", "policy", "template", "checklist", "system", "crm", "erp",
        "sharepoint",
        "database", "knowledge base", "qms", "iso 9001", "iso 27001", "ip register", "asset register", "method", "spec",
        "playbook", "datasheet", "architecture", "safety protocol", "risk assessment", "process map"
    ],
    "Customer": [
        "client", "customer", "account", "lead", "opportunity", "pipeline", "quote", "proposal", "contract", "msa",
        "sow", "sla",
        "purchase order", "po", "invoice", "renewal", "retention", "distributor", "reseller", "channel",
        "customer success"
    ],
    "Strategic Alliance": [
        "partner", "partnership", "alliance", "strategic", "mou", "joint venture", "framework agreement",
        "collaboration",
        "consortium", "university", "college", "council", "ngo", "integrator", "oem", "supplier agreement",
        "grant agreement",
        "licensor", "licensee", "jv"
    ],
}
TEN_STEPS = ["Identify", "Separate", "Protect", "Safeguard", "Manage", "Control", "Use", "Monitor", "Value", "Report"]
SECTOR_CUES = {
    "GreenTech": ["recycling", "recycled", "waste", "biomass", "circular", "emissions", "co2e", "solar", "pv",
                  "turbine", "kwh",
                  "energy efficiency", "retrofit", "heat pump", "iso 14001", "esg", "sdg", "ofgem", "lca"],
    "MedTech": ["iso 13485", "mhra", "ce mark", "clinical", "gcp", "patient", "medical device", "pms",
                "post-market surveillance"],
    "AgriTech": ["soil", "irrigation", "seed", "fertiliser", "biomass", "yield", "farm"],
}


def _analyse_weighted(text: str, weights_by_file: Dict[str, float]) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, float], int]:
    """
    Weighted Four-Leaf & Ten-Steps.
    Returns:
      ic_map (with tick/narrative/score),
      ten (scores+narratives),
      leaf_scores (raw weighted scores for 4-leaf),
      quality% (heuristic)
    """
    sector = st.session_state.get("sector", "Other")
    t_all = text.lower()

    # per-leaf weighted scores
    leaf_scores: Dict[str, float] = {"Human": 0.0, "Structural": 0.0, "Customer": 0.0, "Strategic Alliance": 0.0}
    # step scores accumulation (float, later bounded 1..10)
    step_scores: Dict[str, float] = {s: 0.0 for s in TEN_STEPS}

    # Weight context: if sector cues are present, add mild boosts
    sector_present = False
    if sector in SECTOR_CUES:
        if any(c in t_all for c in SECTOR_CUES[sector]):
            sector_present = True

    # Evaluate leafs by weighted keyword presence
    for leaf, cues in FOUR_LEAF_KEYS.items():
        eff = list(cues)
        if sector_present and leaf in ("Structural", "Customer", "Strategic Alliance"):
            eff += SECTOR_CUES[sector]
        base = 0.0
        for cue in eff:
            if cue in t_all:
                base += max(weights_by_file.values() or [0.4])
        leaf_scores[leaf] += base

    # Map artefact categories to step boosts:
    def bump(step: str, amt: float) -> None:
        step_scores[step] = step_scores.get(step, 0.0) + amt

    for fname, w in (weights_by_file or {}).items():
        n = fname.lower()
        # contracts / JV / MoU / grants
        if any(k in n for k in ["contract", "msa", "sow", "sla", "po", "joint_venture", "joint venture", "jv", "mou", "grant", "licence", "license"]):
            bump("Control", 2.0 * w)
            bump("Use", 2.5 * w)
        # knowledge/process/safety
        if any(k in n for k in ["knowledge", "kmp", "sop", "process", "safety", "protocol", "risk", "qms", "iso"]):
            bump("Identify", 1.8 * w)
            bump("Separate", 1.4 * w)
            bump("Manage", 1.6 * w)
        # specs/slides/canvas
        if any(k in n for k in ["spec", "canvas", "deck", "slides", "pptx"]):
            bump("Identify", 0.8 * w)
            bump("Use", 0.6 * w)
        # pricing/licensing hints
        if any(k in n for k in ["price", "pricing", "royalty", "subscription", "oem", "white label"]):
            bump("Use", 1.0 * w)
            bump("Value", 1.4 * w)
        # governance/reporting hints
        if any(k in n for k in ["board", "report", "dashboard", "audit"]):
            bump("Report", 1.2 * w)
            bump("Monitor", 1.0 * w)

    # Convert leaf_scores -> ticks & narratives
    ic_map: Dict[str, Any] = {}
    avg_leaf = (sum(leaf_scores.values()) / max(1, len(leaf_scores)))
    threshold = max(1.0, avg_leaf * 0.6)

    for leaf, score in leaf_scores.items():
        tick = score >= threshold
        if leaf == "Human":
            nar = "Human Capital evidenced (values/awards/training/safety) but requires competency mapping." if tick else \
                  "Human Capital cues are present but limited; competency & training records should be formalised."
        elif leaf == "Structural":
            nar = "Structural Capital formalised (KMP/SOPs/process maps/ISO/QMS) enabling repeatable delivery." if tick else \
                  "Structural Capital under-documented; SOPs/KMP/ISO mapping recommended."
        elif leaf == "Customer":
            nar = "Customer Capital present (contracts/POs/channels), supporting recurring value capture." if tick else \
                  "Customer Capital weak in evidence; contracts/renewals/pipeline should be documented."
        else:
            nar = "Strategic Alliance Capital evidenced (JV/MoU/partners/universities/councils)." if tick else \
                  "Strategic alliances not clearly evidenced; JV/MoU documentation needed."
        ic_map[leaf] = {"tick": tick, "narrative": nar, "score": round(score, 2)}

    # Build Ten-Steps final scores 1..10
    base = 3.0
    ten_scores: List[int] = []
    ten_narrs: List[str] = []
    if sector_present:
        step_scores["Use"] = step_scores.get("Use", 0.0) + 0.8
        step_scores["Report"] = step_scores.get("Report", 0.0) + 0.5

    for step in TEN_STEPS:
        s_float = base + step_scores.get(step, 0.0)
        s = int(max(1, min(10, round(s_float))))
        ten_scores.append(s)
        ten_narrs.append(f"{step}: readiness ≈ {s}/10.")

    ten = {"scores": ten_scores, "narratives": ten_narrs}

    # Evidence quality
    files_factor = min(1.0, len(weights_by_file) / 6.0)
    leaf_div = sum(1 for v in ic_map.values() if v["tick"]) / 4.0
    weight_mean = (sum(weights_by_file.values()) / max(1, len(weights_by_file))) if weights_by_file else 0.4
    quality = int(round(100 * (0.45 * files_factor + 0.35 * leaf_div + 0.20 * min(1.0, weight_mean))))

    return ic_map, ten, leaf_scores, quality


# --------------- INTERPRETIVE NARRATIVE --------------
def _build_interpreted_summary(case: str,
                               leaf_scores: Dict[str, float],
                               ic_map: Dict[str, Any],
                               ten: Dict[str, Any],
                               evidence_quality: int,
                               context: Dict[str, str]) -> str:
    sector = st.session_state.get("sector", "Other")
    size = st.session_state.get("company_size", "Micro (1–10)")

    strengths = [k for k, v in ic_map.items() if v.get("tick")]
    gaps = [k for k, v in ic_map.items() if not v.get("tick")]

    ts = ten.get("scores") or [5] * len(TEN_STEPS)
    strong_steps = [s for s, sc in zip(TEN_STEPS, ts) if sc >= 7]
    weak_steps = [s for s, sc in zip(TEN_STEPS, ts) if sc <= 5]

    p1 = (f"{case} is a {size} in {sector}. Based on uploaded artefacts and expert context, the company shows "
          f"an emerging ability to codify and scale its operating model, with measurable signals across "
          f"{', '.join(strengths) if strengths else 'selected IC dimensions'}.")

    if strengths:
        p2a = f"Strengths concentrate in {', '.join(strengths)}" + (f"; gaps are {', '.join(gaps)}." if gaps else ".")
    else:
        p2a = "Strengths are not yet well-evidenced; additional artefacts are required."
    p2b = ("Evidence points to maturing structures (e.g., KMP/SOPs/process maps) and formal relationships "
           "(contracts/JVs) where present. Human capability and customer lifecycle signals improve markedly once "
           "competency maps and CRM/renewal data are attached.")
    p2 = p2a + " " + p2b

    if strong_steps or weak_steps:
        p3 = (f"Ten-Steps patterns indicate strong {', '.join(strong_steps) if strong_steps else 'foundations'}; "
              f"progress is constrained by {', '.join(weak_steps) if weak_steps else 'later-stage governance and valuation readiness'}.")
    else:
        p3 = "Ten-Steps scores suggest a developing baseline; expert review will refine scoring as artefacts are consolidated."

    actions = [
        "Create a single IA Register linking contracts/JVs, SOPs/KMP, and product/service artefacts (source-of-truth).",
        "Introduce quarterly governance reporting (board pack + KPI dashboard) to strengthen Monitor/Report.",
        "Define valuation approach (IAS 38 fair value) and connect to licensing templates for near-term monetisation.",
        "Formalise competency matrices and training logs to evidence Human Capital maturity.",
    ]
    p4 = "Assumptions & Action Plan:\n" + "\n".join([f"• {a}" for a in actions])

    missing = "Request additional artefacts: CRM/renewal data, NDA/licence/royalty terms, board/management reports."
    p5 = f"Evidence quality ≈ {evidence_quality}% (heuristic). {missing}"

    return "\n\n".join([p1, p2, p3, p4, p5])


# ------------------ SESSION DEFAULTS -----------------
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
ss.setdefault("leaf_scores", {})
ss.setdefault("evidence_quality", 0)
ss.setdefault("evidence_counts", {})     # NEW: store file-type mix
ss.setdefault("evidence_weights", {})    # NEW: store per-file weights
# Expert prompts
ss.setdefault("why_service", "")
ss.setdefault("stage", "")
ss.setdefault("plan_s", "")
ss.setdefault("plan_m", "")
ss.setdefault("plan_l", "")
ss.setdefault("markets_why", "")
ss.setdefault("sale_price_why", "")

SIZES = ["Micro (1–10)", "Small (11–50)", "Medium (51–250)", "Large (250+)"]
SECTORS = [
    "Food & Beverage", "MedTech", "GreenTech", "AgriTech", "Biotech", "Software/SaaS", "FinTech", "EdTech",
    "Manufacturing", "Creative/Digital", "Professional Services", "Mobility/Transport", "Energy", "Other"
]

# -------------------- NAV ---------------------------
st.sidebar.markdown("### Navigate")
page = st.sidebar.radio("", ("Customer", "Analyse Evidence", "Expert View", "Reports", "Licensing Templates"),
                        index=0, key="nav")

# -------------------- PAGES -------------------------

# 1) CUSTOMER (with required prompts)
if page == "Customer":
    st.header("Customer details")
    with st.form("customer_form"):
        c1, c2, c3 = st.columns([1.1, 1, 1])
        with c1:
            case_name = st.text_input("Customer / Company name *", ss.get("case_name", ""))
        with c2:
            size = st.selectbox("Company size", SIZES, index=SIZES.index(ss.get("company_size", SIZES[0])))
        with c3:
            current_sector = ss.get("sector", "Other")
            sector_index = SECTORS.index(current_sector) if current_sector in SECTORS else SECTORS.index("Other")
            sector = st.selectbox("Sector / Industry", SECTORS, index=sector_index)

        st.markdown("#### Expert Context (required)")
        why_service = st.text_area("1) Why is the customer seeking this service? *", ss.get("why_service", ""), height=90)
        stage = st.text_area("2) What stage are the products/services at? *", ss.get("stage", ""), height=90)
        c4, c5, c6 = st.columns(3)
        with c4:
            plan_s = st.text_area("3a) Short-term plan (0–6m) *", ss.get("plan_s", ""), height=90)
        with c5:
            plan_m = st.text_area("3b) Medium-term plan (6–24m) *", ss.get("plan_m", ""), height=90)
        with c6:
            plan_l = st.text_area("3c) Long-term plan (24m+) *", ss.get("plan_l", ""), height=90)
        markets_why = st.text_area("4) Which markets fit and why? *", ss.get("markets_why", ""), height=90)
        sale_price_why = st.text_area("5) If selling tomorrow, target price & why? *",
                                      ss.get("sale_price_why", ""), height=90)

        st.caption("Uploads are held in session until analysis. Nothing is written to server until export.")
        uploads = st.file_uploader("Upload evidence (PDF, DOCX, TXT, CSV, XLSX, PPTX, images)",
                                   type=["pdf", "docx", "txt", "csv", "xlsx", "pptx", "png", "jpg", "jpeg", "webp"],
                                   accept_multiple_files=True, key="uploader_main")

        submitted = st.form_submit_button("Save details")
        if submitted:
            missing = [("Customer / Company name", case_name),
                       ("Why service", why_service), ("Stage", stage),
                       ("Short plan", plan_s), ("Medium plan", plan_m), ("Long plan", plan_l),
                       ("Markets & why", markets_why), ("Sale price & why", sale_price_why)]
            missing_fields = [label for (label, val) in missing if not (val or "").strip()]
            if missing_fields:
                st.error("Please complete required fields: " + ", ".join(missing_fields))
            else:
                ss["case_name"] = case_name
                ss["company_size"] = size
                ss["sector"] = sector
                ss["why_service"] = why_service.strip()
                ss["stage"] = stage.strip()
                ss["plan_s"] = plan_s.strip()
                ss["plan_m"] = plan_m.strip()
                ss["plan_l"] = plan_l.strip()
                ss["markets_why"] = markets_why.strip()
                ss["sale_price_why"] = sale_price_why.strip()
                if uploads:
                    ss["uploads"] = uploads
                st.success("Saved customer details & expert context.")
    if ss.get("uploads"):
        st.info(f"{len(ss['uploads'])} file(s) stored in session. Go to **Analyse Evidence** next.")

# 2) ANALYSE EVIDENCE  → Evidence Dashboard + Run Analysis
elif page == "Analyse Evidence":
    st.header("Evidence Dashboard & Analysis")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Evidence Quality")
        eq = ss.get("evidence_quality", 0) or 0
        st.progress(min(100, max(0, eq)) / 100.0)
        st.caption(f"{eq}% evidence coverage (heuristic – based on file mix, diversity, and weight).")

    with col2:
        st.subheader("File-type mix")
        counts = ss.get("evidence_counts", {}) or {}
        if counts:
            labels = list(counts.keys())
            values = [counts[k] for k in labels]
            fig_bar = go.Figure(data=[go.Bar(x=labels, y=values)])
            fig_bar.update_layout(
                margin=dict(l=0, r=0, t=30, b=0),
                height=260,
                xaxis_title="Extension",
                yaxis_title="File count"
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.caption("No files analysed yet. Upload evidence on the Customer page and click **Run analysis now** below.")

    st.subheader("Intellectual Capital Radar (4-Leaf)")
    leaf_scores = ss.get("leaf_scores", {}) or {}
    if leaf_scores:
        leaves = ["Human", "Structural", "Customer", "Strategic Alliance"]
        raw_vals = [float(leaf_scores.get(l, 0.0)) for l in leaves]
        max_val = max(raw_vals) if any(v > 0 for v in raw_vals) else 1.0
        # normalise to 0–10 for display
        norm_vals = [(v / max_val) * 10.0 if max_val > 0 else 0.0 for v in raw_vals]

        # close the loop for radar
        theta = leaves + [leaves[0]]
        r = norm_vals + [norm_vals[0]]

        fig_rad = go.Figure(
            data=go.Scatterpolar(r=r, theta=theta, fill='toself', name='IC Radar')
        )
        fig_rad.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
            showlegend=False,
            margin=dict(l=0, r=0, t=20, b=10),
            height=320
        )
        st.plotly_chart(fig_rad, use_container_width=True)
        st.caption("Radar shows relative strength of evidence for each IC leaf (scaled 0–10 from weighted signals).")
    else:
        st.caption("Run analysis to populate the IC Radar from the uploaded evidence.")

    st.subheader("What we've found / What may be missing")
    ic_map = ss.get("ic_map", {}) or {}
    colF, colM = st.columns(2)
    with colF:
        st.markdown("**Found (✓)**")
        any_found = False
        for leaf in ["Human", "Structural", "Customer", "Strategic Alliance"]:
            row = ic_map.get(leaf)
            if row and row.get("tick"):
                any_found = True
                st.markdown(f"- ✓ **{leaf}** — {row.get('narrative', '')}")
        if not any_found:
            st.caption("No strong IC signals evidenced yet – analysis will update this once run.")
    with colM:
        st.markdown("**Potential gaps (⚠)**")
        any_gap = False
        for leaf in ["Human", "Structural", "Customer", "Strategic Alliance"]:
            row = ic_map.get(leaf)
            if not row or not row.get("tick"):
                any_gap = True
                msg = row.get("narrative", f"{leaf} not yet clearly evidenced.") if row else f"{leaf} not yet clearly evidenced."
                st.markdown(f"- ⚠ **{leaf}** — {msg}")
        if not any_gap:
            st.caption("No obvious gaps detected at this evidence level.")

    st.markdown("---")
    st.markdown("### Run or refresh analysis")
    if st.button("Run analysis now"):
        uploads: List[Any] = ss.get("uploads") or []
        extracted, counts, weights = _read_text(uploads)

        # Build expert-context header (used by interpreter but NOT blindly copied)
        context = {
            "why": ss.get("why_service", ""),
            "stage": ss.get("stage", ""),
            "plan_s": ss.get("plan_s", ""),
            "plan_m": ss.get("plan_m", ""),
            "plan_l": ss.get("plan_l", ""),
            "markets": ss.get("markets_why", ""),
            "sale": ss.get("sale_price_why", ""),
        }

        context_stub = (
            f"[CTX] why={context['why'][:140]} | stage={context['stage'][:140]} | "
            f"plans=({context['plan_s'][:60]}/{context['plan_m'][:60]}/{context['plan_l'][:60]}) | "
            f"markets={context['markets'][:140]} | sale={context['sale'][:60]}"
        )
        combined_text_for_detection = (extracted + "\n\n" + context_stub).strip().lower()

        ic_map_new, ten, leaf_scores_new, quality = _analyse_weighted(combined_text_for_detection, weights)

        case = ss.get("case_name", "Untitled Customer")
        interpreted = _build_interpreted_summary(case, leaf_scores_new, ic_map_new, ten, quality, context)

        ss["combined_text"] = interpreted
        ss["ic_map"] = ic_map_new
        ss["ten_steps"] = ten
        ss["leaf_scores"] = leaf_scores_new
        ss["evidence_quality"] = quality
        ss["evidence_counts"] = counts
        ss["evidence_weights"] = weights

        if len(extracted.strip()) < 100:
            st.warning("Little machine-readable text was extracted. If PDFs dominate, consider adding a brief TXT note "
                       "or exporting key pages to DOCX or PPTX.")

        st.success("Analysis complete. Dashboard, Expert View and reports have been updated.")

# 3) EXPERT VIEW
elif page == "Expert View":
    st.header("Narrative Summary")
    nar = st.text_area("Summary (editable)", value=ss.get("combined_text", ""), height=220, key="nar_edit")
    ss["narrative"] = nar or ss.get("narrative", "")

    colA, colB = st.columns([1, 1])
    with colA:
        if not PUBLIC_MODE:
            st.subheader("Evidence Quality")
            st.progress(min(100, max(0, ss.get("evidence_quality", 0))) / 100.0)
            st.caption(f"{ss.get('evidence_quality', 0)}% evidence coverage (heuristic)")

        st.subheader("4-Leaf Map")
        ic_map: Dict[str, Any] = ss.get("ic_map", {})
        for leaf in ["Human", "Structural", "Customer", "Strategic Alliance"]:
            row = ic_map.get(leaf, {"tick": False, "narrative": f"No assessment yet for {leaf}.", "score": 0.0})
            tick = "✓" if row["tick"] else "•"
            suffix = "" if PUBLIC_MODE else f"  _(score: {row.get('score', 0.0)})_"
            st.markdown(f"- **{leaf}**: {tick}{suffix}")
            st.caption(row["narrative"])

        st.subheader("Expert Context (read-only)")
        st.markdown(f"- **Why service:** {ss.get('why_service', '') or '—'}")
        st.markdown(f"- **Stage:** {ss.get('stage', '') or '—'}")
        st.markdown(f"- **Plans:** S={ss.get('plan_s', '') or '—'} | M={ss.get('plan_m', '') or '—'} | L={ss.get('plan_l', '') or '—'}")
        st.markdown(f"- **Markets & why:** {ss.get('markets_why', '') or '—'}")
        st.markdown(f"- **Target sale & why:** {ss.get('sale_price_why', '') or '—'}")

    with colB:
        st.subheader("Ten-Steps Readiness")
        raw_ten = st.session_state.get("ten_steps") or {}
        scores = raw_ten.get("scores") or [5] * len(TEN_STEPS)
        narrs = raw_ten.get("narratives") or [f"{s}: tbd" for s in TEN_STEPS]
        ten = {"scores": scores, "narratives": narrs}

        st.dataframe({"Step": TEN_STEPS, "Score (1–10)": ten["scores"]},
                     hide_index=True, use_container_width=True)
        with st.expander("Narrative per step"):
            for s, n in zip(TEN_STEPS, ten["narratives"]):
                st.markdown(f"**{s}** — {n}")

# 4) REPORTS
elif page == "Reports":
    st.header("Reports & Exports")
    case_name = ss.get("case_name", "Untitled_Customer")
    case_folder = OUT_ROOT / _safe(case_name)

    def _compose_ic() -> Tuple[str, str]:
        title = f"IC Report — {case_name}"
        ic_map_loc = ss.get("ic_map", {})

        raw_ten_loc = st.session_state.get("ten_steps") or {}
        scores = raw_ten_loc.get("scores") or [5] * len(TEN_STEPS)
        narrs = raw_ten_loc.get("narratives") or [f"{s}: tbd" for s in TEN_STEPS]
        ten_loc = {"scores": scores, "narratives": narrs}

        b: List[str] = []
        interpreted = ss.get("combined_text", "").strip() or ss.get("narrative", "(no summary)")
        b.append(f"Executive Summary\n\n{interpreted}\n")
        if not PUBLIC_MODE:
            b.append(f"Evidence Quality: ~{ss.get('evidence_quality', 0)}% coverage (heuristic)\n")

        b.append("Four-Leaf Analysis")
        for leaf in ["Human", "Structural", "Customer", "Strategic Alliance"]:
            row = ic_map_loc.get(leaf, {"tick": False, "narrative": "", "score": 0.0})
            tail = "" if PUBLIC_MODE else f" (score: {row.get('score', 0.0)})"
            b.append(f"- {leaf}: {'✓' if row.get('tick') else '•'} — {row.get('narrative', '')}{tail}")

        b.append("\nTen-Steps Readiness")
        for s, n in zip(TEN_STEPS, ten_loc["narratives"]):
            b.append(f"- {n}")

        b.append("\nNotes")
        b.append("This document is provided for high-level evaluation only." if PUBLIC_MODE
                 else "CONFIDENTIAL. Advisory-first; expert review required for final scoring and accounting treatment.")
        return title, "\n".join(b)

    def _compose_lic() -> Tuple[str, str]:
        title = f"Licensing Report — {case_name}"
        b: List[str] = []
        b.append(f"Licensing Options & FRAND Readiness for {case_name}\n")
        b.append("Expert Context (selected)")
        b.append(f"- Why service: {ss.get('why_service', '')}")
        b.append(f"- Target sale & why: {ss.get('sale_price_why', '')}\n")
        b.append("Models:")
        b.append("- Revenue licence (royalties, FRAND-aligned terms, annual audit clause)")
        b.append("- Defensive licence (IP pooling, non-assert across partners)")
        b.append("- Co-creation licence (shared ownership of Foreground IP, revenue-sharing)")
        b.append("\nGovernance & Audit")
        b.append("IA Register maintained; evidence bundles per licence; regular royalty/performance reporting.")
        if PUBLIC_MODE:
            b.append("\n(Details suppressed in public mode.)")
        return title, "\n".join(b)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Generate IC Report (DOCX/TXT)", key="btn_ic"):
            title, body = _compose_ic()
            data, fname, mime = _export_bytes(title, body)
            path, msg = _save_bytes(case_folder, fname, data)
            st.download_button("⬇️ Download IC Report", data, file_name=fname, mime=mime, key="dl_ic")
            (st.success if path else st.warning)(msg)
    with c2:
        if st.button("Generate Licensing Report (DOCX/TXT)", key="btn_lic"):
            title, body = _compose_lic()
            data, fname, mime = _export_bytes(title, body)
            path, msg = _save_bytes(case_folder, fname, data)
            st.download_button("⬇️ Download Licensing Report", data, file_name=fname, mime=mime, key="dl_lic")
            (st.success if path else st.warning)(msg)
    st.caption("Server save root: disabled (public mode)" if PUBLIC_MODE else f"Server save root: {OUT_ROOT}")

# 5) LICENSING TEMPLATES
elif page == "Licensing Templates":
    st.header("Licensing Templates (editable DOCX/TXT)")
    case = ss.get("case_name", "Untitled Customer")
    sector = ss.get("sector", "Other")
    template = st.selectbox("Choose a template:",
                            ["FRAND Standard", "Co-creation (Joint Development)", "Knowledge (Non-traditional)"],
                            index=0)
    if st.button("Generate template", key="btn_make_template"):
        if template == "FRAND Standard":
            title = f"FRAND Standard template — {case}"
            body = (f"FRAND Standard — {case} ({sector})\n\n"
                    "Scope, definitions, essentiality clause, non-discrimination clause, reasonable fee corridor, "
                    "audit & verification, termination, governing law (EU), dispute resolution.\n")
        elif template == "Co-creation (Joint Development)":
            title = f"Co-creation template — {case}"
            body = (f"Co-creation / Joint Development — {case} ({sector})\n\n"
                    "Background IP, Foreground IP, contributions, ownership split, publication rights, "
                    "commercial model, revenue sharing, exit/assignment, FRAND alignment where applicable.\n")
        else:
            title = f"Knowledge licence (non-traditional) — {case}"
            body = (f"Knowledge Licence — {case} ({sector})\n\n"
                    "Codified know-how (copyright/trade secret), permitted fields of use, attribution, "
                    "commercial vs social-benefit pathways, verification, revocation, jurisdiction.\n")
        data, fname, mime = _export_bytes(title, body)
        folder = OUT_ROOT / _safe(case)
        path, msg = _save_bytes(folder, fname, data)
        st.download_button("⬇️ Download Template", data, file_name=fname, mime=mime, key="dl_tpl")
        (st.success if path else st.warning)(msg)
