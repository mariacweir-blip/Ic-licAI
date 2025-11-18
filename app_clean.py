# app_clean.py — IC-LicAI Expert Console (v1.1)
# Includes:
# - Structural Capital dominance (IAS 38 lens)
# - Tacit → codified → Structural transition
# - 4-Leaf + Ten-Steps analysis
# - Evidence extraction (TXT/DOCX/PPTX/CSV)
# - Asset & Evidence Verification (LIP review)
# - Translation layer (manual capture)
# - LIP Assistant
# - IMPAC3T + EU sidebar branding
# - © Areopa 1987–2025 footer

from __future__ import annotations
import io, os, tempfile, re, csv
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import streamlit as st
import plotly.graph_objects as go  # for radar charts
from PIL import Image

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
  section[data-testid="stSidebar"] { background:#0047AB; }  /* cobalt for IMPAC3T */
  section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] p,
  section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] span { color:#E7F0FF!important; }
  .stRadio div[role="radiogroup"] label { color:#E7F0FF!important; }
  footer {visibility: hidden;}
  footer:after {
    content: "© Areopa 1987–2025. All rights reserved.";
    visibility: visible;
    display: block;
    position: relative;
    padding: 8px 0 4px 0;
    text-align: center;
    font-size: 11px;
    color: #555;
  }
</style>
""",
    unsafe_allow_html=True,
)
st.markdown('<div class="ic-title-bar">IC-LicAI Expert Console</div>', unsafe_allow_html=True)

# ---------------- LOGOS ----------------------------
IMPAC3T_LOGO_PATH = "demo_assets/impac3t_logo.png"
EU_FLAG_PATH = "demo_assets/eu_flag.png"

try:
    IMPAC3T_LOGO = Image.open(IMPAC3T_LOGO_PATH)
except Exception:
    IMPAC3T_LOGO = None

try:
    EU_FLAG_LOGO = Image.open(EU_FLAG_PATH)
except Exception:
    EU_FLAG_LOGO = None

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
    CSV semantic extraction: headers + first rows to expose SME / ESG terms
    (safety, contract, emissions, etc.) to the heuristics.
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
    Weights depend on artefact type (contracts/JVs > SOPs > slides > culture).
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
        "crm",
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

def _analyse_weighted(
    text: str,
    weights_by_file: Dict[str, float],
) -> Tuple[Dict[str, Any], Dict[str, float], Dict[str, Any], int]:
    """
    Weighted 4-Leaf + Ten-Steps engine with Structural Capital dominance
    and sector / ESG reinforcement.
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

    max_weight = max(weights_by_file.values() or [0.4])

    # Structural base bump from explicit cues in content
    for cue in EXPLICIT_STRUCTURAL_CUES:
        if cue in t_all:
            leaf_scores["Structural"] += max_weight * 1.5

    # 4-Leaf scoring (with sector hints)
    for leaf, cues in FOUR_LEAF_KEYS.items():
        eff = list(cues)
        if sector_present and leaf in ("Structural", "Customer", "Strategic Alliance"):
            eff += SECTOR_CUES[sector]
        base = 0.0
        for cue in eff:
            if cue in t_all:
                base += max_weight
        leaf_scores[leaf] += base

    # Ten-Steps bump helper
    def bump(step: str, amt: float) -> None:
        step_scores[step] = step_scores.get(step, 0.0) + amt

    # File-name driven patterns
    for fname, w in (weights_by_file or {}).items():
        n = fname.lower()

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

        if any(k in n for k in ["knowledge", "kmp", "sop", "process", "safety", "protocol", "risk", "qms", "iso"]):
            leaf_scores["Structural"] += 1.8 * w
            leaf_scores["Human"] += 0.8 * w
            bump("Identify", 1.8 * w)
            bump("Separate", 1.4 * w)
            bump("Manage", 1.6 * w)
            bump("Safeguard", 1.0 * w)

        if any(k in n for k in ["spec", "canvas", "deck", "slides", "pptx"]):
            leaf_scores["Structural"] += 0.8 * w
            bump("Identify", 0.8 * w)
            bump("Use", 0.6 * w)

        if any(k in n for k in ["price", "pricing", "royalty", "subscription", "oem", "white label"]):
            bump("Use", 1.2 * w)
            bump("Value", 1.6 * w)

        if any(k in n for k in ["board", "report", "dashboard", "audit"]):
            bump("Report", 1.4 * w)
            bump("Monitor", 1.2 * w)

    # ESG + Stakeholders → double materiality signal
    esg_hits = any(c in t_all for c in ESG_CUES)
    stakeholder_hits = any(c in t_all for c in SEVEN_STAKEHOLDER_CUES)
    if esg_hits or stakeholder_hits:
        bump("Report", 1.2)
        bump("Value", 1.0)

    if sector_present:
        bump("Use", 0.8)
        bump("Report", 0.5)

    # Structural dominance if both tacit and explicit present
    if leaf_scores["Structural"] > 0 and (leaf_scores["Customer"] > 0 or leaf_scores["Strategic Alliance"] > 0):
        leaf_scores["Structural"] *= 1.15

    # Convert to IC map with narratives
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
  
