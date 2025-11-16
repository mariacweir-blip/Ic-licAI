# app_clean.py — IC-LicAI Expert Console (Structural + FRAND + LIP Assistant)
# Adds: DOCX/PPTX extraction, weighted IC signal engine, interpreted narrative,
# radar dashboard, CSV semantic extraction, robust company-context auto-split,
# IAS 38 Structural Capital emphasis, FRAND-aware licensing templates,
# Seven Stakeholder / ESG narrative, LIP Console, and LIP Assistant (AI-enabled).
#
# NEW in this build (8-point combined spec):
# - Structural Capital dominance preserved and made explicit in comments
# - Tacit vs Codified + pipeline heuristics (translation layer – Option A)
# - Tacit → codified transition and pending pipeline treated as tacit in narrative
# - AI chat box “Licensing & Intangibles Partner Assistant” using OpenAI when available
# - Local fallback if no API key / library
# - Global © Areopa 1987–2025 footer

from __future__ import annotations
import io, os, tempfile, re, csv
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import streamlit as st
import plotly.graph_objects as go  # for radar charts

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
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)
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
        return (
            bio.getvalue(),
            f"{base}.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
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
TEXT_EXT = {".txt"}
DOCX_EXT = {".docx"}
PPTX_EXT = {".pptx"}
CSV_EXT = {".csv"}
PDF_EXT = {".pdf"}  # filename cue only (kept for future)


def _extract_text_docx(data: bytes) -> str:
    if not HAVE_DOCX:
        return ""
    try:
        bio = io.BytesIO(data)
        doc = Document(bio)
        parts: List[str] = []
        for p in doc.paragraphs:
            txt = (p.text or "").strip()
            if txt:
                parts.append(txt)
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
            if getattr(slide, "has_notes_slide", False) and slide.notes_slide:
                nt = (slide.notes_slide.notes_text_frame.text or "").strip()
                if nt:
                    parts.append(nt)
        return "\n".join(parts)
    except Exception:
        return ""


def _extract_text_csv(raw: bytes, name: str) -> str:
    """
    CSV semantic extraction: surface headers + a few rows so SME/ESG words
    like 'safety', 'policy', 'contract', 'governance', 'emissions', etc.
    are visible to the heuristics.
    """
    try:
        decoded = raw.decode("utf-8", errors="ignore")
        rows = list(csv.reader(decoded.splitlines()))
        if not rows:
            return ""
        headers = [h.strip() for h in rows[0] if h.strip()]
        cells: List[str] = []
        for row in rows[1:11]:
            cells.extend([c.strip() for c in row if c.strip()])
        header_txt = ", ".join(headers)
        cells_txt = "; ".join(cells)
        return f"CSV:{name}\nHeaders: {header_txt}\nRows: {cells_txt}"
    except Exception:
        try:
            return raw.decode("utf-8", errors="ignore")
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

    NAME_WEIGHTS: List[Tuple[str, float]] = [
        ("contract", 1.0),
        ("msa", 1.0),
        ("sow", 0.9),
        ("sla", 0.9),
        ("agreement", 0.9),
        ("joint venture", 1.0),
        ("joint_venture", 1.0),
        ("jv", 1.0),
        ("mou", 1.0),
        ("grant", 0.9),
        ("licence", 0.9),
        ("license", 0.9),
        ("register", 0.9),
        ("knowledge_management", 0.8),
        ("kmp", 0.8),
        ("sop", 0.8),
        ("process", 0.8),
        ("safety", 0.8),
        ("protocol", 0.8),
        ("spec", 0.6),
        ("canvas", 0.6),
        ("bmc", 0.6),
        ("slides", 0.6),
        ("deck", 0.6),
        ("board_pack", 0.8),
        ("board", 0.8),
        ("pricing", 0.7),
        ("tariff", 0.7),
        ("dataset", 0.7),
        ("culture", 0.4),
        ("award", 0.4),
    ]
    EXT_DEFAULTS: Dict[str, float] = {
        ".docx": 0.7,
        ".pptx": 0.6,
        ".txt": 0.5,
        ".csv": 0.6,
        ".pdf": 0.4,
    }

    for f in files or []:
        name = getattr(f, "name", "file")
        lower_name = str(name).lower()
        ext = Path(lower_name).suffix or "none"
        counts[ext] = counts.get(ext, 0) + 1

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
            elif ext in CSV_EXT:
                text = _extract_text_csv(raw, name)
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
        "team",
        "staff",
        "employee",
        "hire",
        "recruit",
        "training",
        "trained",
        "trainer",
        "onboarding",
        "mentor",
        "apprentice",
        "qualification",
        "certified",
        "cpd",
        "skills matrix",
        "safety training",
        "toolbox talk",
        "rota",
    ],
    "Structural": [
        # IAS 38 explicit / documented assets
        "contract",
        "agreement",
        "joint venture",
        "joint_venture",
        "jv",
        "mou",
        "grant",
        "licence",
        "license",
        "nda",
        "non-disclosure",
        "confidentiality",
        "ip register",
        "asset register",
        "register",
        "policy",
        "sop",
        "procedure",
        "process",
        "workflow",
        "protocol",
        "safety protocol",
        "process map",
        "manual",
        "guide",
        "handbook",
        "template",
        "checklist",
        "board pack",
        "board report",
        "pricing sheet",
        "tariff",
        "datasheet",
        "dataset",
        "qms",
        "iso 9001",
        "iso 27001",
        "knowledge base",
        "architecture",
        "crm",  # explicit system
    ],
    "Customer": [
        "client",
        "customer",
        "account",
        "lead",
        "opportunity",
        "pipeline",
        "quote",
        "proposal",
        "purchase order",
        "po",
        "invoice",
        "renewal",
        "retention",
        "distributor",
        "reseller",
        "channel",
        "customer success",
        "subscription",
    ],
    "Strategic Alliance": [
        "partner",
        "partnership",
        "alliance",
        "strategic",
        "mou",
        "joint venture",
        "framework agreement",
        "collaboration",
        "consortium",
        "university",
        "college",
        "council",
        "ngo",
        "integrator",
        "oem",
        "supplier agreement",
        "grant agreement",
        "licensor",
        "licensee",
        "jv",
    ],
}

TEN_STEPS = [
    "Identify",
    "Separate",
    "Protect",
    "Safeguard",
    "Manage",
    "Control",
    "Use",
    "Monitor",
    "Value",
    "Report",
]

SECTOR_CUES = {
    "GreenTech": [
        "recycling",
        "recycled",
        "waste",
        "biomass",
        "circular",
        "emissions",
        "co2e",
        "solar",
        "pv",
        "turbine",
        "kwh",
        "energy efficiency",
        "retrofit",
        "heat pump",
        "iso 14001",
        "esg",
        "sdg",
        "ofgem",
        "lca",
    ],
    "MedTech": [
        "iso 13485",
        "mhra",
        "ce mark",
        "clinical",
        "gcp",
        "patient",
        "medical device",
        "pms",
        "post-market surveillance",
    ],
    "AgriTech": [
        "soil",
        "irrigation",
        "seed",
        "fertiliser",
        "biomass",
        "yield",
        "farm",
    ],
}

# Explicit structural cues (IAS 38-compliant artefact hints)
EXPLICIT_STRUCTURAL_CUES: List[str] = [
    "contract",
    "agreement",
    "msa",
    "sow",
    "sla",
    "mou",
    "joint venture",
    "joint_venture",
    "jv",
    "grant",
    "licence",
    "license",
    "ip register",
    "asset register",
    "register",
    "policy",
    "sop",
    "procedure",
    "process",
    "workflow",
    "protocol",
    "safety protocol",
    "process map",
    "manual",
    "guide",
    "handbook",
    "template",
    "checklist",
    "board pack",
    "board report",
    "pricing sheet",
    "tariff",
    "datasheet",
    "dataset",
    "qms",
    "iso 9001",
    "iso 27001",
    "crm",
]

# ESG & Seven Stakeholder cues (Sugai / Weir)
ESG_CUES: List[str] = [
    "esg",
    "sdg",
    "carbon",
    "emissions",
    "net zero",
    "scope 1",
    "scope 2",
    "scope 3",
    "sustainability",
    "governance",
    "diversity",
    "inclusion",
    "impact",
    "stakeholder",
]

SEVEN_STAKEHOLDER_CUES: List[str] = [
    "employee",
    "staff",
    "worker",
    "investor",
    "shareholder",
    "lender",
    "customer",
    "client",
    "supplier",
    "vendor",
    "partner",
    "alliance",
    "community",
    "local authority",
    "municipality",
    "ngo",
    "nature",
    "environment",
    "biodiversity",
]

# -------- Translation Layer (Option A) – Tacit vs Codified & Pipeline -----
# These heuristics are used primarily to give the AI LIP Assistant
# a simple “tacit / codified / pending pipeline” snapshot that aligns
# with Structural Capital dominance and IAS 38.

TACIT_HINTS: List[str] = [
    "informal",
    "in heads",
    "word of mouth",
    "relationship",
    "relationships",
    "reputation",
    "network",
    "networks",
    "experience only",
    "people-based",
]

PIPELINE_HINTS: List[str] = [
    "pipeline",
    "prospect",
    "prospects",
    "in negotiation",
    "under negotiation",
    "mou",
    "letter of intent",
    "loi",
    "in discussion",
    "under discussion",
]

CODED_HINTS: List[str] = EXPLICIT_STRUCTURAL_CUES + [
    "documented",
    "written",
    "stored",
    "registered",
    "codified",
    "standardised",
    "standardized",
]


def _estimate_tacit_codified_pipeline(text: str) -> Dict[str, Any]:
    """
    Very lightweight translation snapshot:
    - counts signals for codified (explicit structural) vs tacit (people / reputation)
    - counts basic pipeline cues (treated as tacit until contracted)
    Used only to give a high-level summary to the AI assistant and LIP.
    """
    t = (text or "").lower()
    if not t:
        return {"codified_hits": 0, "tacit_hits": 0, "pipeline_hits": 0, "summary": "No evidence text available."}

    codified_hits = sum(t.count(c) for c in CODED_HINTS)
    tacit_hits = sum(t.count(c) for c in TACIT_HINTS)
    pipeline_hits = sum(t.count(c) for c in PIPELINE_HINTS)

    parts: List[str] = []
    if codified_hits:
        parts.append(
            f"Detected ~{codified_hits} codified/explicit cues (contracts, SOPs, registers, policies, datasets, CRM)."
        )
    if tacit_hits:
        parts.append(
            f"Detected ~{tacit_hits} tacit cues (informal relationships, reputation, people-based practices)."
        )
    if pipeline_hits:
        parts.append(
            f"Detected ~{pipeline_hits} pipeline cues (MoUs, prospects, in negotiation), treated as tacit until codified."
        )

    if not parts:
        parts.append(
            "No strong tacit/codified or pipeline cues detected in the current text; additional artefacts may be needed."
        )

    return {
        "codified_hits": codified_hits,
        "tacit_hits": tacit_hits,
        "pipeline_hits": pipeline_hits,
        "summary": " ".join(parts),
    }

# --------------- ANALYSIS ENGINE ---------------------
def _analyse_weighted(
    text: str,
    weights_by_file: Dict[str, float],
) -> Tuple[Dict[str, Any], Dict[str, float], Dict[str, Any], int]:
    """
    Weighted Four-Leaf & Ten-Steps.
    Returns:
      ic_map (with tick/narrative/score),
      leaf_scores (raw weighted scores for 4-leaf),
      ten (scores+narratives),
      quality% (heuristic)
    NOTE: Structural Capital dominance:
    - Explicit Structural cues + codified artefacts are intentionally weighted
      so that, where there is conflict between 'who' and 'what', Structural wins
      for IAS 38 readiness.
    """
    sector = st.session_state.get("sector", "Other")
    t_all = (text or "").lower()

    leaf_scores: Dict[str, float] = {
        "Human": 0.0,
        "Structural": 0.0,
        "Customer": 0.0,
        "Strategic Alliance": 0.0,
    }
    step_scores: Dict[str, float] = {s: 0.0 for s in TEN_STEPS}

    sector_present = False
    if sector in SECTOR_CUES:
        if any(c in t_all for c in SECTOR_CUES[sector]):
            sector_present = True

    # ----- Structural vs Tacit weighting -----
    max_weight = max(weights_by_file.values() or [0.4])

    # Base structural emphasis from explicit cues anywhere in the text (IAS 38 explicit assets)
    for cue in EXPLICIT_STRUCTURAL_CUES:
        if cue in t_all:
            leaf_scores["Structural"] += max_weight * 1.5  # audit-ready bump

    # Four-Leaf cues (with sector reinforcement)
    for leaf, cues in FOUR_LEAF_KEYS.items():
        eff = list(cues)
        if sector_present and leaf in ("Structural", "Customer", "Strategic Alliance"):
            eff += SECTOR_CUES[sector]
        base = 0.0
        for cue in eff:
            if cue in t_all:
                base += max_weight
        leaf_scores[leaf] += base

    # Ten-Steps scoring (file-name based + ESG / FRAND cues)
    def bump(step: str, amt: float) -> None:
        step_scores[step] = step_scores.get(step, 0.0) + amt

    for fname, w in (weights_by_file or {}).items():
        n = fname.lower()

        # Contracts / grants / agreements → Structural dominates, Customer/SA secondary
        if any(k in n for k in ["contract", "msa", "sow", "sla", "po", "agreement"]):
            leaf_scores["Structural"] += 2.5 * w
            leaf_scores["Customer"] += 1.0 * w
            bump("Control", 2.0 * w)
            bump("Use", 2.5 * w)

        if any(k in n for k in ["joint_venture", "joint venture", "jv", "mou", "grant"]):
            leaf_scores["Structural"] += 2.5 * w
            leaf_scores["Strategic Alliance"] += 1.5 * w
            bump("Control", 2.0 * w)
            bump("Use", 2.0 * w)

        # Knowledge / SOP / KMP / safety / ISO → Structural + Human
        if any(k in n for k in ["knowledge", "kmp", "sop", "process", "safety", "protocol", "risk", "qms", "iso"]):
            leaf_scores["Structural"] += 1.8 * w
            leaf_scores["Human"] += 0.8 * w
            bump("Identify", 1.8 * w)
            bump("Separate", 1.4 * w)
            bump("Manage", 1.6 * w)
            bump("Safeguard", 1.0 * w)

        # Specs/slides/canvas → Structural + Use
        if any(k in n for k in ["spec", "canvas", "deck", "slides", "pptx"]):
            leaf_scores["Structural"] += 0.8 * w
            bump("Identify", 0.8 * w)
            bump("Use", 0.6 * w)

        # Pricing/licensing hints → Use/Value (multi value streams)
        if any(k in n for k in ["price", "pricing", "royalty", "subscription", "oem", "white label"]):
            bump("Use", 1.2 * w)
            bump("Value", 1.6 * w)

        # Governance/reporting → Monitor/Report
        if any(k in n for k in ["board", "report", "dashboard", "audit"]):
            bump("Report", 1.4 * w)
            bump("Monitor", 1.2 * w)

    # ESG & Seven Stakeholder presence → boost Report/Value (double materiality)
    esg_hits = any(c in t_all for c in ESG_CUES)
    stakeholder_hits = any(c in t_all for c in SEVEN_STAKEHOLDER_CUES)
    if esg_hits or stakeholder_hits:
        bump("Report", 1.2)
        bump("Value", 1.0)

    if sector_present:
        bump("Use", 0.8)
        bump("Report", 0.5)

    # Make sure Structural "wins" when explicit + tacit both present:
    # if Structural>0 and (Customer or SA also high), add a small dominance bump.
    if leaf_scores["Structural"] > 0 and (leaf_scores["Customer"] > 0 or leaf_scores["Strategic Alliance"] > 0):
        leaf_scores["Structural"] *= 1.15  # dominance tweak

    # Convert leaf_scores -> ticks & narratives
    ic_map: Dict[str, Any] = {}
    avg_leaf = (sum(leaf_scores.values()) / max(1, len(leaf_scores)))
    threshold = max(1.0, avg_leaf * 0.6)

    for leaf, score in leaf_scores.items():
        tick = score >= threshold
        if leaf == "Human":
            nar = (
                "Human Capital evidenced (values, awards, training and safety practice), but competency and role-mapping "
                "should be consolidated into a formal skills register."
                if tick
                else "Human Capital is not yet clearly evidenced; competency mapping, training logs and safety records are needed."
            )
        elif leaf == "Structural":
            nar = (
                "Structural Capital appears IAS 38-ready in places (contracts, SOPs, protocols, registers, CRM and board packs "
                "are present), supporting audit-ready recognition on the balance sheet."
                if tick
                else "Structural Capital is under-documented; explicit artefacts (contracts, registers, SOPs, board packs, "
                "pricing, datasets, CRM) should be consolidated into an auditable IA Register."
            )
        elif leaf == "Customer":
            nar = (
                "Customer Capital is evidenced through relationships, renewal logic and channels, supporting recurring value capture "
                "and future licensing opportunities."
                if tick
                else "Customer Capital appears weak in the evidence; relationship histories, renewals, CRM and pipeline data should be structured."
            )
        else:
            nar = (
                "Strategic Alliance Capital is evidenced (JVs, MoUs, partners, universities, councils), enabling co-creation "
                "and ecosystem-based licensing opportunities."
                if tick
                else "Strategic alliances are not clearly evidenced; JV/MoU documentation and partner frameworks are needed."
            )
        ic_map[leaf] = {"tick": tick, "narrative": nar, "score": round(score, 2)}

    # Ten-Steps scores
    base = 3.0
    ten_scores: List[int] = []
    ten_narrs: List[str] = []

    for step in TEN_STEPS:
        s_float = base + step_scores.get(step, 0.0)
        s = int(max(1, min(10, round(s_float))))
        ten_scores.append(s)
        ten_narrs.append(f"{step}: readiness ≈ {s}/10.")

    ten = {"scores": ten_scores, "narratives": ten_narrs}

    # Evidence quality metric
    files_factor = min(1.0, len(weights_by_file) / 6.0)
    leaf_div = sum(1 for v in ic_map.values() if v["tick"]) / 4.0
    weight_mean = (sum(weights_by_file.values()) / max(1, len(weights_by_file))) if weights_by_file else 0.4
    quality = int(round(100 * (0.45 * files_factor + 0.35 * leaf_div + 0.20 * min(1.0, weight_mean))))

    return ic_map, leaf_scores, ten, quality

# --------------- INTERPRETIVE NARRATIVE --------------
def _build_interpreted_summary(
    case: str,
    leaf_scores: Dict[str, float],
    ic_map: Dict[str, Any],
    ten: Dict[str, Any],
    evidence_quality: int,
    context: Dict[str, str],
) -> str:
    sector = st.session_state.get("sector", "Other")
    size = st.session_state.get("company_size", "Micro (1–10)")

    strengths = [k for k, v in ic_map.items() if v.get("tick")]
    gaps = [k for k, v in ic_map.items() if not v.get("tick")]

    ts = ten.get("scores") or [5] * len(TEN_STEPS)
    strong_steps = [s for s, sc in zip(TEN_STEPS, ts) if sc >= 7]
    weak_steps = [s for s, sc in zip(TEN_STEPS, ts) if sc <= 5]

    narrative_text = context.get("why", "") + " " + context.get("markets", "")
    seven_hit = any(c in narrative_text.lower() for c in SEVEN_STAKEHOLDER_CUES)
    esg_hit = any(c in narrative_text.lower() for c in ESG_CUES)

    # Tacit vs codified snapshot (translation layer)
    combined_for_tacit = (
        (context.get("why", "") or "")
        + " "
        + (context.get("stage", "") or "")
        + " "
        + (context.get("plan_s", "") or "")
        + " "
        + (context.get("plan_m", "") or "")
        + " "
        + (context.get("plan_l", "") or "")
        + " "
        + (context.get("markets", "") or "")
    )
    tacit_snapshot = _estimate_tacit_codified_pipeline(combined_for_tacit)

    # 1) Context & positioning
    p1 = (
        f"{case} is a {size} in {sector}. Based on uploaded artefacts and company context, the company shows an "
        f"emerging ability to codify and scale its operating model, with measurable signals across "
        f"{', '.join(strengths) if strengths else 'selected IC dimensions'}."
    )

    # 2) Four-Leaf interpretation (explicit vs tacit, IAS 38)
    if strengths:
        p2a = f"Strengths concentrate in {', '.join(strengths)}" + (f"; gaps are {', '.join(gaps)}." if gaps else ".")
    else:
        p2a = "Strengths are not yet well-evidenced; additional artefacts are required."

    p2b = (
        "Evidence points to maturing Structural Capital where explicit artefacts — contracts, SOPs, protocols, registers, "
        "board materials, CRM and datasets — are present. These are the primary candidates for IAS 38-compliant recognition on "
        "the balance sheet. Human, Customer and Strategic Alliance Capital are reflected mainly through tacit know-how, "
        "relationships and informal practice, which require codification before they become audit-ready."
    )
    p2c = (
        f" From a tacit/codified perspective, {tacit_snapshot['summary']} "
        "Pending pipeline items (prospects, MoUs, in-negotiation deals) are treated as tacit value until translated "
        "into explicit contracts or structured datasets."
    )
    p2 = p2a + " " + p2b + p2c

    # 3) Ten-Steps insight and readiness for licensing
    if strong_steps or weak_steps:
        p3 = (
            f"Ten-Steps patterns indicate strong {', '.join(strong_steps) if strong_steps else 'foundations'}; "
            f"progress is constrained by {', '.join(weak_steps) if weak_steps else 'later-stage governance, valuation and reporting readiness'}."
        )
    else:
        p3 = (
            "Ten-Steps scores suggest a developing baseline; company-side review will refine scoring as artefacts are "
            "consolidated and IA governance is embedded."
        )

    # 4) Seven Stakeholder / ESG framing and value streams
    if seven_hit or esg_hit:
        p4_intro = (
            "Using the Seven Stakeholder Model (SSM) as defined by Professor Philip Sugai and Dr Maria Weir, "
            "the company can frame value creation across employees, investors, customers, partners and suppliers, "
            "communities and the natural environment. This provides a structured way to connect ESG performance "
            "and double materiality to concrete intangible assets."
        )
    else:
        p4_intro = (
            "Applying the Seven Stakeholder Model (SSM) as defined by Professor Philip Sugai and Dr Maria Weir "
            "would allow the company to frame value creation across employees, investors, customers, partners and "
            "suppliers, communities and the natural environment, even if these links are not yet fully articulated "
            "in the evidence set."
        )

    p4_mid = (
        "From a commercialisation perspective, explicit Structural Capital (contracts, data, software, methods, indices, "
        "protocols) can support multiple simultaneous value streams — including revenue licences, access or community "
        "licences, co-creation arrangements and data/algorithm sharing — provided that ownership, rights and governance "
        "are clarified."
    )

    actions = [
        "Create a single IA Register linking all explicit artefacts (contracts, JVs, SOPs, protocols, datasets, board packs, CRM) to the 4-Leaf Model.",
        "Map each explicit asset to at least one licensing-ready value stream (revenue, access/community, co-creation, defensive or data/algorithm sharing).",
        "Introduce quarterly governance reporting (board pack + KPI dashboard) to strengthen Monitor and Report and to evidence ESG and stakeholder impacts.",
        "Define valuation approach (IAS 38 fair value) and link to licensing templates so that audit-ready Structural Capital supports near-term monetisation.",
        "Formalise competency matrices and training logs so that tacit Human Capital can be progressively codified into Structural Capital.",
    ]
    p4_actions = "Assumptions & Action Plan:\n" + "\n".join([f"• {a}" for a in actions])

    p4 = p4_intro + "\n\n" + p4_mid + "\n\n" + p4_actions

    # 5) Evidence quality and next evidence requests
    missing = (
        "Request additional artefacts: CRM/renewal data, NDA/licence/royalty and access terms, IA or IP registers, "
        "board/management reports, and any ESG or stakeholder dashboards used in internal decision-making."
    )
    p5 = f"Evidence quality ≈ {evidence_quality}% (heuristic). {missing}"

    return "\n\n".join([p1, p2, p3, p4, p5])

# --------- COMPANY CONTEXT AUTO-SPLIT HELPER ----------
def _auto_split_expert_block(text: str) -> Dict[str, str]:
    """
    Take a single pasted block and try to split it across:
    why_service, stage, plan_s, plan_m, plan_l, markets_why, sale_price_why
    using blank lines or sentence boundaries.
    """
    t = (text or "").strip()
    keys = [
        "why_service",
        "stage",
        "plan_s",
        "plan_m",
        "plan_l",
        "markets_why",
        "sale_price_why",
    ]
    if not t:
        return {k: "" for k in keys}

    blocks = [b.strip() for b in t.replace("\r\n", "\n").split("\n\n") if b.strip()]

    if len(blocks) < 5:
        blocks = [s.strip() for s in re.split(r"(?<=[.!?])\s+", t) if s.strip()]

    out: Dict[str, str] = {k: "" for k in keys}
    for k, chunk in zip(keys, blocks):
        out[k] = chunk
    return out

# ------------------ LIP AI ASSISTANT HELPERS -----------------
def _build_lip_context_summary() -> str:
    """
    Build a compact context string for the AI-based LIP Assistant.
    Uses:
      - case name, sector, size
      - IC map ticks
      - Ten-Steps high level
      - tacit/codified/pipeline snapshot
      - stored narrative
    """
    ss = st.session_state
    case = ss.get("case_name", "Untitled Company")
    sector = ss.get("sector", "Other")
    size = ss.get("company_size", "Micro (1–10)")
    ic_map: Dict[str, Any] = ss.get("ic_map", {})
    ten = ss.get("ten_steps", {})
    scores = ten.get("scores") or [5] * len(TEN_STEPS)

    leaf_flags = ", ".join(
        f"{leaf}={'Y' if ic_map.get(leaf, {}).get('tick') else 'N'}"
        for leaf in ["Human", "Structural", "Customer", "Strategic Alliance"]
    )

    tacit_src = (
        (ss.get("why_service", "") or "")
        + " "
        + (ss.get("stage", "") or "")
        + " "
        + (ss.get("plan_s", "") or "")
        + " "
        + (ss.get("plan_m", "") or "")
        + " "
        + (ss.get("plan_l", "") or "")
        + " "
        + (ss.get("markets_why", "") or "")
    )
    tacit_snapshot = _estimate_tacit_codified_pipeline(tacit_src)

    narrative = ss.get("combined_text", "") or ss.get("narrative", "")
    narrative_short = narrative[:900]

    return (
        f"Company: {case} | size={size} | sector={sector}\n"
        f"Four-Leaf ticks: {leaf_flags}\n"
        f"Ten-Steps scores (1–10): {scores}\n"
        f"Tacit vs Codified & pipeline snapshot: {tacit_snapshot['summary']}\n"
        f"IC narrative (truncated): {narrative_short}"
    )


def _call_lip_ai(question: str, context_summary: str) -> str:
    """
    AI-enabled LIP Assistant.
    - If OPENAI_API_KEY (or st.secrets['OPENAI_API_KEY']) is set and openai>=1.x is available,
      uses the API to generate an answer.
    - Otherwise, falls back to a local, rule-based explanation using existing narrative.
    """
    api_key = st.secrets.get("OPENAI_API_KEY", None) or os.environ.get("OPENAI_API_KEY", None)
    if not api_key:
        # Local fallback using existing narrative and FRAND text
        ss = st.session_state
        narrative = ss.get("combined_text", "") or ss.get("narrative", "")
        lic_snippet = (
            "The current tool supports revenue licences, access/community licences, co-creation/joint development, "
            "defensive/cross-licence arrangements and data/algorithm licences, framed through a FRAND-informed lens "
            "across the Seven Stakeholder Model."
        )
        answer_parts = [
            "LIP Assistant (offline mode – no API key set).",
            "",
            f"Question: {question}",
        ]
        if "structural" in question.lower() or "ias 38" in question.lower():
            answer_parts.append(
                "- Structural Capital is treated as the home for explicit, documented assets (contracts, SOPs, registers, "
                "CRM, datasets, board packs). Where both tacit and explicit signals exist, Structural is deliberately "
                "weighted to dominate, reflecting IAS 38 audit-readiness."
            )
        answer_parts.append("- FRAND / licensing view: " + lic_snippet)
        if narrative:
            answer_parts.append(
                "- IC narrative extract:\n" + narrative[:800] + ("..." if len(narrative) > 800 else "")
            )
        else:
            answer_parts.append("- No stored IC narrative yet; run Analyse Evidence for richer insights.")
        return "\n\n".join(answer_parts)

    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI(api_key=api_key)

        system_msg = (
            "You are the 'Licensing & Intangibles Partner Assistant' (LIP Assistant) for Areopa's IC-LicAI tool. "
            "You specialise in Intellectual Capital (4-Leaf Model), IAS 38-ready Structural Capital, tacit vs codified "
            "knowledge, FRAND-style licensing models and the Seven Stakeholder Model (Sugai–Weir). "
            "Give concise, practical answers that a Licensing & Intangibles Partner can use directly with SMEs."
        )
        user_msg = (
            "Context from the IC-LicAI console:\n"
            f"{context_summary}\n\n"
            "User question:\n"
            f"{question}"
        )

        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"LIP Assistant (AI) error: {e}"

# ------------------ SESSION DEFAULTS -----------------
ss = st.session_state
ss.setdefault("case_name", "Untitled Company")
ss.setdefault("company_size", "Micro (1–10)")
ss.setdefault("sector", "Other")
ss.setdefault("uploads", [])
ss.setdefault("combined_text", "")
ss.setdefault("ic_map", {})
ss.setdefault("ten_steps", {})
ss.setdefault("narrative", "")
ss.setdefault("leaf_scores", {})
ss.setdefault("evidence_quality", 0)
ss.setdefault("file_counts", {})

# Expert prompts
ss.setdefault("why_service", "")
ss.setdefault("stage", "")
ss.setdefault("plan_s", "")
ss.setdefault("plan_m", "")
ss.setdefault("plan_l", "")
ss.setdefault("markets_why", "")
ss.setdefault("sale_price_why", "")
ss.setdefault("full_context_block", "")
ss.setdefault("auto_split_on_save", True)

# Legacy simple LIP log (kept but no longer used in UI)
ss.setdefault("lip_history", [])

# New chat-style LIP AI history
ss.setdefault("lip_chat_history", [])

SIZES = [
    "Micro (1–10)",
    "Small (11–50)",
    "Medium (51–250)",
    "Large (250+)",
]
SECTORS = [
    "Food & Beverage",
    "MedTech",
    "GreenTech",
    "AgriTech",
    "Biotech",
    "Software/SaaS",
    "FinTech",
    "EdTech",
    "Manufacturing",
    "Creative/Digital",
    "Professional Services",
    "Mobility/Transport",
    "Energy",
    "Other",
]

# -------------------- NAV ---------------------------
st.sidebar.markdown("### Navigate")
page = st.sidebar.radio(
    "",
    ("Company", "Analyse Evidence", "LIP Console", "Reports", "Licensing Templates", "LIP Assistant"),
    index=0,
    key="nav",
)

# -------------------- PAGES -------------------------

# 1) COMPANY (with required prompts + auto-split)
if page == "Company":
    st.header("Company details")
    with st.form("company_form"):
        c1, c2, c3 = st.columns([1.1, 1, 1])
        with c1:
            case_name = st.text_input("Company name *", ss.get("case_name", ""))
        with c2:
            size = st.selectbox(
                "Company size",
                SIZES,
                index=SIZES.index(ss.get("company_size", SIZES[0])),
            )
        with c3:
            current_sector = ss.get("sector", "Other")
            sector_index = SECTORS.index(current_sector) if current_sector in SECTORS else SECTORS.index("Other")
            sector = st.selectbox("Sector / Industry", SECTORS, index=sector_index)

        st.markdown("#### Company context (required)")
        full_block = st.text_area(
            "Optional: paste full context here (one block, then auto-fill below)",
            ss.get("full_context_block", ""),
            help=(
                "You can paste your whole narrative here once, then tick auto-split and the tool will "
                "try to populate the individual questions for you."
            ),
            height=80,
        )
        auto_split = st.checkbox(
            "Auto-split pasted context into fields on Save",
            value=ss.get("auto_split_on_save", True),
            help="If ticked, the block above will be split across the questions below when you click Save.",
        )

        why_service = st.text_area(
            "Why is the company seeking this service? *",
            ss.get("why_service", ""),
            height=90,
        )
        stage = st.text_area(
            "What stage are the products/services at? *",
            ss.get("stage", ""),
            height=90,
        )
        c4, c5, c6 = st.columns(3)
        with c4:
            plan_s = st.text_area(
                "3a) Short-term plan (0–6m) *",
                ss.get("plan_s", ""),
                height=90,
            )
        with c5:
            plan_m = st.text_area(
                "3b) Medium-term plan (6–24m) *",
                ss.get("plan_m", ""),
                height=90,
            )
        with c6:
            plan_l = st.text_area(
                "3c) Long-term plan (24m+) *",
                ss.get("plan_l", ""),
                height=90,
            )
        markets_why = st.text_area(
            "4) Which markets fit and why? *",
            ss.get("markets_why", ""),
            height=90,
        )
        sale_price_why = st.text_area(
            "5) If selling tomorrow, target price & why? *",
            ss.get("sale_price_why", ""),
            height=90,
        )

        st.caption("Uploads are held in session until analysis. Nothing is written to server until export.")
        uploads = st.file_uploader(
            "Upload evidence (PDF, DOCX, TXT, CSV, XLSX, PPTX, images)",
            type=["pdf", "docx", "txt", "csv", "xlsx", "pptx", "png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            key="uploader_main",
        )

        submitted = st.form_submit_button("Save details")
        if submitted:
            # Optional auto-split of a single pasted narrative into all questions
            if auto_split and full_block.strip():
                derived = _auto_split_expert_block(full_block)
                if not why_service.strip() and derived["why_service"]:
                    why_service = derived["why_service"]
                if not stage.strip() and derived["stage"]:
                    stage = derived["stage"]
                if not plan_s.strip() and derived["plan_s"]:
                    plan_s = derived["plan_s"]
                if not plan_m.strip() and derived["plan_m"]:
                    plan_m = derived["plan_m"]
                if not plan_l.strip() and derived["plan_l"]:
                    plan_l = derived["plan_l"]
                if not markets_why.strip() and derived["markets_why"]:
                    markets_why = derived["markets_why"]
                if not sale_price_why.strip() and derived["sale_price_why"]:
                    sale_price_why = derived["sale_price_why"]

            missing = [
                ("Company name", case_name),
                ("Why service", why_service),
                ("Stage", stage),
                ("Short plan", plan_s),
                ("Medium plan", plan_m),
                ("Long plan", plan_l),
                ("Markets & why", markets_why),
                ("Sale price & why", sale_price_why),
            ]
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
                ss["full_context_block"] = full_block
                ss["auto_split_on_save"] = auto_split
                if uploads:
                    ss["uploads"] = uploads
                st.success("Saved company details & context.")

    if ss.get("uploads"):
        st.info(f"{len(ss['uploads'])} file(s) stored in session. Go to **Analyse Evidence** next.")

# 2) ANALYSE EVIDENCE (with radar / evidence quality)
elif page == "Analyse Evidence":
    st.header("Evidence Dashboard & Analysis")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Evidence Quality")
        eq = int(ss.get("evidence_quality", 0))
        st.progress(min(100, max(0, eq)) / 100.0)
        st.caption(f"{eq}% coverage (heuristic — based on artefact mix and IC diversity).")

        counts = ss.get("file_counts", {}) or {}
        if counts:
            st.markdown("**Files by type (session):**")
            for ext, n in counts.items():
                st.markdown(f"- `{ext}` → {n} file(s)")
        else:
            st.caption("No files analysed yet.")

    with col2:
        st.subheader("IC Radar (4-Leaf + Ten-Steps)")

        ic_map: Dict[str, Any] = ss.get("ic_map", {})
        ten = ss.get(
            "ten_steps",
            {"scores": [5] * len(TEN_STEPS), "narratives": [f"{s}: tbd" for s in TEN_STEPS]},
        )

        leaf_labels = ["Human", "Structural", "Customer", "Strategic Alliance"]
        leaf_vals = [float(ic_map.get(l, {}).get("score", 0.0)) for l in leaf_labels]
        if any(v > 0 for v in leaf_vals):
            fig_leaf = go.Figure()
            fig_leaf.add_trace(
                go.Scatterpolar(
                    r=leaf_vals + leaf_vals[:1],
                    theta=leaf_labels + leaf_labels[:1],
                    fill="toself",
                    name="IC Intensity",
                )
            )
            fig_leaf.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, max(leaf_vals) or 1])),
                showlegend=False,
                margin=dict(l=20, r=20, t=20, b=20),
            )
            st.plotly_chart(fig_leaf, use_container_width=True)
        else:
            st.caption("Radar will appear once analysis has been run and IC signals are detected.")

        step_scores = ten.get("scores") or [5] * len(TEN_STEPS)
        if step_scores:
            fig_steps = go.Figure(
                data=[
                    go.Bar(
                        x=TEN_STEPS,
                        y=step_scores,
                    )
                ]
            )
            fig_steps.update_layout(
                yaxis=dict(range=[0, 10]),
                margin=dict(l=20, r=20, t=20, b=40),
            )
            st.plotly_chart(fig_steps, use_container_width=True)

    st.markdown("---")
    st.subheader("Interpreted Analysis Summary (first 5000 chars)")
    combined = ss.get("combined_text", "")
    st.text_area(
        "Summary view (read-only; editable in LIP Console)",
        combined[:5000],
        height=260,
        key="combined_preview",
    )

    if st.button("Run analysis now"):
        uploads: List[Any] = ss.get("uploads") or []
        extracted, counts, weights = _read_text(uploads)

        ss["file_counts"] = counts or {}

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

        ic_map, leaf_scores, ten, quality = _analyse_weighted(combined_text_for_detection, weights)

        case = ss.get("case_name", "Untitled Company")
        interpreted = _build_interpreted_summary(case, leaf_scores, ic_map, ten, quality, context)

        ss["combined_text"] = interpreted
        ss["ic_map"] = ic_map
        ss["ten_steps"] = ten
        ss["leaf_scores"] = leaf_scores
        ss["evidence_quality"] = quality

        if len(extracted.strip()) < 100:
            st.warning(
                "Little machine-readable text was extracted (DOCX/PPTX/CSV extraction is enabled). "
                "If PDFs dominate, consider adding a brief TXT note or export key pages to DOCX."
            )

        st.success("Analysis complete. Open **LIP Console** to refine and export.")

# 3) LIP CONSOLE (was Expert View)
elif page == "LIP Console":
    st.header("LIP Console — Narrative & IC Map")
    nar = st.text_area(
        "Summary (editable by Licensing & Intangibles Partner)",
        value=ss.get("combined_text", ""),
        height=220,
        key="nar_edit",
    )
    ss["narrative"] = nar or ss.get("narrative", "")
    ss["combined_text"] = ss["narrative"]

    colA, colB = st.columns([1, 1])
    with colA:
        if not PUBLIC_MODE:
            st.subheader("Evidence Quality")
            st.progress(min(100, max(0, ss.get("evidence_quality", 0))) / 100.0)
            st.caption(f"{ss.get('evidence_quality', 0)}% evidence coverage (heuristic)")

        st.subheader("4-Leaf Map")
        ic_map: Dict[str, Any] = ss.get("ic_map", {})
        for leaf in ["Human", "Structural", "Customer", "Strategic Alliance"]:
            row = ic_map.get(
                leaf,
                {"tick": False, "narrative": f"No assessment yet for {leaf}.", "score": 0.0},
            )
            tick = "✓" if row["tick"] else "•"
            suffix = "" if PUBLIC_MODE else f"  _(score: {row.get('score', 0.0)})_"
            st.markdown(f"- **{leaf}**: {tick}{suffix}")
            st.caption(row["narrative"])

        st.subheader("Company context (read-only)")
        st.markdown(f"- **Why service:** {ss.get('why_service', '') or '—'}")
        st.markdown(f"- **Stage:** {ss.get('stage', '') or '—'}")
        st.markdown(
            f"- **Plans:** S={ss.get('plan_s', '') or '—'} | "
            f"M={ss.get('plan_m', '') or '—'} | L={ss.get('plan_l', '') or '—'}"
        )
        st.markdown(f"- **Markets & why:** {ss.get('markets_why', '') or '—'}")
        st.markdown(f"- **Target sale & why:** {ss.get('sale_price_why', '') or '—'}")

    with colB:
        st.subheader("Ten-Steps Readiness")
        raw_ten = ss.get("ten_steps") or {}
        scores = raw_ten.get("scores") or [5] * len(TEN_STEPS)
        narrs = raw_ten.get("narratives") or [f"{s}: tbd" for s in TEN_STEPS]
        ten = {"scores": scores, "narratives": narrs}

        st.dataframe(
            {"Step": TEN_STEPS, "Score (1–10)": ten["scores"]},
            hide_index=True,
            use_container_width=True,
        )
        with st.expander("Narrative per step"):
            for s, n in zip(TEN_STEPS, ten["narratives"]):
                st.markdown(f"**{s}** — {n}")

# 4) REPORTS
elif page == "Reports":
    st.header("Reports & Exports")
    case_name = ss.get("case_name", "Untitled Company")
    case_folder = OUT_ROOT / _safe(case_name)

    def _compose_ic() -> Tuple[str, str]:
        title = f"IC Report — {case_name}"
        ic_map = ss.get("ic_map", {})

        raw_ten = ss.get("ten_steps") or {}
        scores = raw_ten.get("scores") or [5] * len(TEN_STEPS)
        narrs = raw_ten.get("narratives") or [f"{s}: tbd" for s in TEN_STEPS]
        ten = {"scores": scores, "narratives": narrs}

        b: List[str] = []
        interpreted = ss.get("combined_text", "").strip() or ss.get("narrative", "(no summary)")
        b.append(f"Executive Summary\n\n{interpreted}\n")
        if not PUBLIC_MODE:
            b.append(f"Evidence Quality: ~{ss.get('evidence_quality', 0)}% coverage (heuristic)\n")

        b.append("Four-Leaf Analysis")
        for leaf in ["Human", "Structural", "Customer", "Strategic Alliance"]:
            row = ic_map.get(leaf, {"tick": False, "narrative": "", "score": 0.0})
            tail = "" if PUBLIC_MODE else f" (score: {row.get('score', 0.0)})"
            b.append(f"- {leaf}: {'✓' if row.get('tick') else '•'} — {row.get('narrative', '')}{tail}")

        b.append("\nTen-Steps Readiness")
        for s, n in zip(TEN_STEPS, ten["narratives"]):
            b.append(f"- {n}")

        b.append("\nNotes")
        b.append(
            "This document is provided for high-level evaluation only."
            if PUBLIC_MODE
            else "CONFIDENTIAL. Advisory-first; company and LIP review required for final scoring, licensing design and accounting treatment."
        )

        b.append("\n\n© Areopa 1987–2025. All rights reserved.")
        return title, "\n".join(b)

    def _compose_lic() -> Tuple[str, str]:
        title = f"Licensing Report — {case_name}"
        b: List[str] = []
        b.append(f"Licensing Options & FRAND-Informed Readiness for {case_name}\n")

        b.append("Status & Disclaimer")
        b.append(
            "This report is an advisory draft only. It does not constitute legal advice and must be "
            "reviewed and adapted by qualified legal counsel before signature or implementation.\n"
        )

        b.append("Company Context (selected)")
        b.append(f"- Why service: {ss.get('why_service', '')}")
        b.append(f"- Target sale & why: {ss.get('sale_price_why', '')}\n")

        b.append("Licensing Model Families")
        b.append(
            "- Revenue licences: royalty or fee-based licences (e.g. per unit, per user, revenue share, or per dataset) with "
            "FRAND-informed fee corridors, audit rights and performance conditions."
        )
        b.append(
            "- Access / community licences: royalty-free or low-fee licences that prioritise fair, reasonable "
            "and non-discriminatory access (FRAND-aligned) for social, educational or public-good outcomes."
        )
        b.append(
            "- Co-creation / joint development licences: shared ownership of Foreground IP, clear contribution "
            "records, revenue sharing, and publication rights aligned to partner mandates."
        )
        b.append(
            "- Defensive and cross-licence arrangements: IP pooling, non-assert agreements and mutual access "
            "to codified know-how to reduce litigation risk and accelerate adoption."
        )
        b.append(
            "- Data / algorithm licences: controlled use of datasets, indices, scoring models and algorithms "
            "with clear field-of-use, access tiers and governance.\n"
        )

        b.append("FRAND & Seven Stakeholder Perspective")
        b.append(
            "FRAND is treated here as a design principle rather than a legal certification. For each proposed "
            "licence family, the company should consider fairness, reasonableness and non-discrimination across "
            "the seven stakeholders defined in the Sugai–Weir model (employees, investors, customers, partners "
            "and suppliers, communities and the natural environment). Royalty-bearing and royalty-free licences "
            "can both be FRAND-aligned when access criteria, pricing rationales and governance are clearly stated.\n"
        )

        b.append("Governance & Audit Expectations")
        b.append(
            "- Maintain an IA Register that links each explicit asset (software, indices, datasets, methods, "
            "processes, brand, training content, CRM data) to its licensing model(s)."
        )
        b.append(
            "- Define board-level oversight for licensing, including regular reporting on licence performance, "
            "compliance, ESG and stakeholder impacts."
        )
        b.append(
            "- Ensure that key contracts, JVs, MoUs and access licences are auditable and compatible with "
            "applicable accounting standards (e.g. IAS 38 for intangible assets).\n"
        )

        if PUBLIC_MODE:
            b.append("(Details suppressed in public mode.)")

        b.append("\n© Areopa 1987–2025. All rights reserved.")
        return title, "\n".join(b)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Generate IC Report (DOCX/TXT)", key="btn_ic"):
            title, body = _compose_ic()
            data, fname, mime = _export_bytes(title, body)
            path, msg = _save_bytes(case_folder, fname, data)
            st.download_button(
                "⬇️ Download IC Report",
                data,
                file_name=fname,
                mime=mime,
                key="dl_ic",
            )
            (st.success if path else st.warning)(msg)
    with c2:
        if st.button("Generate Licensing Report (DOCX/TXT)", key="btn_lic"):
            title, body = _compose_lic()
            data, fname, mime = _export_bytes(title, body)
            path, msg = _save_bytes(case_folder, fname, data)
            st.download_button(
                "⬇️ Download Licensing Report",
                data,
                file_name=fname,
                mime=mime,
                key="dl_lic",
            )
            (st.success if path else st.warning)(msg)

    st.caption("Server save root: disabled (public mode)" if PUBLIC_MODE else f"Server save root: {OUT_ROOT}")

# 5) LICENSING TEMPLATES
elif page == "Licensing Templates":
    st.header("Licensing Templates (editable DOCX/TXT)")
    case = ss.get("case_name", "Untitled Company")
    sector = ss.get("sector", "Other")

    template = st.selectbox(
        "Choose a template:",
        ["FRAND Standard", "Co-creation (Joint Development)", "Knowledge (Non-traditional)"],
        index=0,
    )

    if st.button("Generate template", key="btn_make_template"):
        disclaimer = (
            "STATUS: Non-binding draft template. This document is provided for internal discussion only and must be "
            "reviewed and adapted by qualified legal counsel before signature or implementation.\n\n"
        )

        if template == "FRAND Standard":
            title = f"FRAND Standard template — {case}"
            body = (
                f"FRAND Standard Licence — {case} ({sector})\n\n"
                + disclaimer
                + "1. Purpose & Scope\n"
                "   - Define the licensed technology, dataset, index, software or method.\n"
                "   - Specify fields of use, territories and permitted users.\n\n"
                "2. Access & FRAND-Informed Principles\n"
                "   - Describe how fees (including possible royalty-free tiers) are set on a fair, reasonable and\n"
                "     non-discriminatory basis across comparable users.\n"
                "   - Include access considerations for social, community or public-good partners where relevant.\n\n"
                "3. Financial Terms\n"
                "   - Royalty or fee structure (e.g. per unit, per user, revenue share, or capped fees).\n"
                "   - Invoicing, payment schedule, late payment and currency terms.\n\n"
                "4. Governance, Reporting & Audit\n"
                "   - Licensee reporting obligations (KPIs, usage, sublicensing, ESG/stakeholder indicators if applicable).\n"
                "   - Audit rights and frequency; treatment of under-reporting or non-compliance.\n\n"
                "5. IP Ownership & Improvements\n"
                "   - Background IP ownership and reservation of rights.\n"
                "   - Treatment of improvements, derivative works and feedback.\n\n"
                "6. Compliance, Term & Termination\n"
                "   - Conditions for suspension or termination (breach, non-payment, misuse).\n"
                "   - Survival of key clauses (confidentiality, audit, data protection).\n\n"
                "7. Data, AI & Regulatory Considerations (if applicable)\n"
                "   - Data protection, confidentiality and AI/automated decision-making safeguards.\n"
                "   - Reference to applicable laws, standards or regulatory guidance.\n\n"
                "8. Governing Law & Dispute Resolution\n"
                "   - Governing law (e.g. EU Member State law).\n"
                "   - Mechanism for dispute resolution (negotiation, mediation, arbitration, courts).\n"
                "\n© Areopa 1987–2025. All rights reserved.\n"
            )
        elif template == "Co-creation (Joint Development)":
            title = f"Co-creation template — {case}"
            body = (
                f"Co-creation / Joint Development Licence — {case} ({sector})\n\n"
                + disclaimer
                + "1. Parties, Purpose & Project Definition\n"
                "   - Identify all parties and describe the joint development project and objectives.\n\n"
                "2. Background IP\n"
                "   - List key Background IP contributed by each party and conditions of use.\n\n"
                "3. Foreground IP & Ownership Structure\n"
                "   - Define Foreground IP and allocate ownership shares (e.g. 50/50 or by contribution).\n"
                "   - Set rules for registration, maintenance and enforcement of Foreground IP.\n\n"
                "4. Contributions, Resources & Cost Sharing\n"
                "   - Describe personnel, facilities, data and funding contributed by each party.\n"
                "   - Agree cost-sharing mechanisms for development and exploitation.\n\n"
                "5. Commercialisation & Revenue Sharing\n"
                "   - Outline commercialisation routes (direct sales, licensing, joint ventures).\n"
                "   - Define revenue sharing mechanisms, including treatment of royalty-free access for selected stakeholders.\n\n"
                "6. Publication, Academic Use & Confidentiality\n"
                "   - Academic and scientific publication rights (timing, review, attribution).\n"
                "   - Confidentiality obligations and carve-outs.\n\n"
                "7. Governance, Decision-Making & Dispute Resolution\n"
                "   - Governance structure (steering committee, decision rules).\n"
                "   - Escalation and dispute resolution framework.\n\n"
                "8. Term, Exit & Transition\n"
                "   - Term and conditions for early termination.\n"
                "   - Exit options (buy-out, assignment, break clauses) and treatment of Foreground IP on exit.\n"
                "\n© Areopa 1987–2025. All rights reserved.\n"
            )
        else:
            title = f"Knowledge licence (non-traditional) — {case}"
            body = (
                f"Knowledge Licence — {case} ({sector})\n\n"
                + disclaimer
                + "1. Knowledge Asset Definition\n"
                "   - Describe the codified know-how (e.g. methods, training materials, playbooks, indices, checklists).\n\n"
                "2. Scope of Licence & Field of Use\n"
                "   - Specify permitted uses (internal training, consulting, product development, policy design, etc.).\n"
                "   - Clarify any restricted uses and prohibited activities.\n\n"
                "3. Access & Stakeholder Considerations\n"
                "   - Define standard and, where appropriate, community or social-benefit access tiers.\n"
                "   - Reference a FRAND-informed approach to fairness, reasonableness and non-discrimination\n"
                "     across employees, investors, customers, partners, suppliers, communities and nature.\n\n"
                "4. Attribution & Moral Rights\n"
                "   - Conditions for attribution (branding, acknowledgements, citation requirements).\n\n"
                "5. Confidentiality, Data Protection & Safeguards\n"
                "   - Treatment of confidential information and personal data.\n"
                "   - Safeguards where AI or automated decision-making is involved.\n\n"
                "6. Term, Revocation & Review\n"
                "   - Duration, renewal and review points.\n"
                "   - Conditions for revocation or modification of the licence.\n\n"
                "7. Governing Law & Dispute Resolution\n"
                "   - Governing law.\n"
                "   - Mechanism for addressing disputes.\n"
                "\n© Areopa 1987–2025. All rights reserved.\n"
            )

        data, fname, mime = _export_bytes(title, body)
        folder = OUT_ROOT / _safe(case)
        path, msg = _save_bytes(folder, fname, data)
        st.download_button(
            "⬇️ Download Template",
            data,
            file_name=fname,
            mime=mime,
            key="dl_tpl",
        )
        (st.success if path else st.warning)(msg)

# 6) LIP ASSISTANT (AI chat)
elif page == "LIP Assistant":
    st.header("LIP Assistant — Licensing & Intangibles Partner Assistant")
    st.caption(
        "A helper for the Licensing & Intangibles Partner. "
        "It re-uses the IC narrative, Structural Capital logic and FRAND models. "
        "If an OpenAI API key is configured, it will use AI; otherwise it falls back to a local explanation."
    )

    if ss.get("combined_text", ""):
        st.success("IC narrative available from Analyse Evidence / LIP Console.")
    else:
        st.warning("No IC narrative stored yet. Run **Analyse Evidence** first for best results.")

    # Chat history display
    chat_container = st.container()
    with chat_container:
        if ss.get("lip_chat_history"):
            for msg in ss["lip_chat_history"]:
                if msg["role"] == "user":
                    st.markdown(f"**You:** {msg['content']}")
                else:
                    st.markdown(f"**LIP Assistant:** {msg['content']}")

    st.markdown("---")

    context_focus = st.selectbox(
        "Focus of this question:",
        ["IC findings", "Licensing options", "Both"],
        index=2,
    )

    question = st.text_area(
        "Your question to the LIP Assistant",
        "",
        height=120,
        help="Example: 'Which assets look IAS 38-ready?' or 'How could we structure a royalty-free community licence?'",
    )

    if st.button("Ask LIP Assistant"):
        if not question.strip():
            st.error("Please enter a question.")
        else:
            # Build context summary tuned to requested focus
            full_context = _build_lip_context_summary()
            if context_focus == "IC findings":
                # Nudge assistant more towards IC / Structural
                full_context = "FOCUS: IC & Structural Capital.\n" + full_context
            elif context_focus == "Licensing options":
                full_context = "FOCUS: Licensing & FRAND.\n" + full_context
            else:
                full_context = "FOCUS: Both IC and Licensing.\n" + full_context

            answer = _call_lip_ai(question.strip(), full_context)

            ss["lip_chat_history"].append({"role": "user", "content": question.strip()})
            ss["lip_chat_history"].append({"role": "assistant", "content": answer})

            st.markdown(f"**You:** {question.strip()}")
            st.markdown(f"**LIP Assistant:** {answer}")

    if ss.get("lip_chat_history"):
        if st.button("Clear LIP Assistant history"):
            ss["lip_chat_history"] = []
            st.success("LIP Assistant chat history cleared.")

# ---------------- GLOBAL FOOTER ----------------
st.markdown(
    """
<hr style="margin-top:2rem;margin-bottom:0.5rem;">
<div style="font-size:0.8rem;color:#444;">
  © Areopa 1987–2025. All rights reserved. IC-LicAI Expert Console — Structural Capital & FRAND-ready licensing support.
</div>
""",
    unsafe_allow_html=True,
)
