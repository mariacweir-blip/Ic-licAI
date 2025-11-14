# app_clean.py — IC-LicAI Expert Console (Locked Build, Option 1 + Ask IC Assistant)
# Adds: DOCX/PPTX extraction, weighted IC signal engine, interpreted narrative,
# radar dashboard, CSV semantic extraction, robust expert-context auto-split,
# and an "Ask IC Assistant" local chat page.

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
        ("contract", 1.0), ("msa", 1.0), ("sow", 0.9), ("sla", 0.9),
        ("joint venture", 1.0), ("joint_venture", 1.0), ("jv", 1.0), ("mou", 1.0),
        ("grant", 0.9), ("licence", 0.9), ("license", 0.9),
        ("knowledge_management", 0.8), ("kmp", 0.8), ("sop", 0.8), ("process", 0.8),
        ("safety", 0.8), ("protocol", 0.8),
        ("spec", 0.6), ("canvas", 0.6), ("bmc", 0.6), ("slides", 0.6), ("deck", 0.6),
        ("culture", 0.4), ("award", 0.4),
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
        "team", "staff", "employee", "hire", "recruit", "training", "trained", "trainer",
        "onboarding", "mentor", "apprentice", "qualification", "certified", "cpd",
        "skills matrix", "safety training", "toolbox talk", "rota",
    ],
    "Structural": [
        "process", "procedure", "sop", "workflow", "policy", "template", "checklist",
        "system", "crm", "erp", "sharepoint", "database", "knowledge base", "qms",
        "iso 9001", "iso 27001", "ip register", "asset register", "method", "spec",
        "playbook", "datasheet", "architecture", "safety protocol",
        "risk assessment", "process map",
    ],
    "Customer": [
        "client", "customer", "account", "lead", "opportunity", "pipeline", "quote",
        "proposal", "contract", "msa", "sow", "sla", "purchase order", "po", "invoice",
        "renewal", "retention", "distributor", "reseller", "channel", "customer success",
    ],
    "Strategic Alliance": [
        "partner", "partnership", "alliance", "strategic", "mou", "joint venture",
        "framework agreement", "collaboration", "consortium", "university", "college",
        "council", "ngo", "integrator", "oem", "supplier agreement", "grant agreement",
        "licensor", "licensee", "jv",
    ],
}

TEN_STEPS = ["Identify", "Separate", "Protect", "Safeguard", "Manage",
             "Control", "Use", "Monitor", "Value", "Report"]

SECTOR_CUES = {
    "GreenTech": [
        "recycling", "recycled", "waste", "biomass", "circular", "emissions", "co2e",
        "solar", "pv", "turbine", "kwh", "energy efficiency", "retrofit", "heat pump",
        "iso 14001", "esg", "sdg", "ofgem", "lca",
    ],
    "MedTech": [
        "iso 13485", "mhra", "ce mark", "clinical", "gcp", "patient",
        "medical device", "pms", "post-market surveillance",
    ],
    "AgriTech": [
        "soil", "irrigation", "seed", "fertiliser", "biomass", "yield", "farm",
    ],
}


def _analyse_weighted(
    text: str,
    weights_by_file: Dict[str, float],
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, float], int]:
    """
    Weighted Four-Leaf & Ten-Steps.
    Returns:
      ic_map (with tick/narrative/score),
      ten (scores+narratives),
      leaf_scores (raw weighted scores for 4-leaf),
      quality% (heuristic)
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

    for leaf, cues in FOUR_LEAF_KEYS.items():
        eff = list(cues)
        if sector_present and leaf in ("Structural", "Customer", "Strategic Alliance"):
            eff += SECTOR_CUES[sector]
        base = 0.0
        for cue in eff:
            if cue in t_all:
                base += max(weights_by_file.values() or [0.4])
        leaf_scores[leaf] += base

    def bump(step: str, amt: float) -> None:
        step_scores[step] = step_scores.get(step, 0.0) + amt

    for fname, w in (weights_by_file or {}).items():
        n = fname.lower()
        if any(k in n for k in ["contract", "msa", "sow", "sla", "po",
                                "joint_venture", "joint venture", "jv",
                                "mou", "grant", "licence", "license"]):
            bump("Control", 2.0 * w)
            bump("Use", 2.5 * w)
        if any(k in n for k in ["knowledge", "kmp", "sop", "process",
                                "safety", "protocol", "risk", "qms", "iso"]):
            bump("Identify", 1.8 * w)
            bump("Separate", 1.4 * w)
            bump("Manage", 1.6 * w)
        if any(k in n for k in ["spec", "canvas", "deck", "slides", "pptx"]):
            bump("Identify", 0.8 * w)
            bump("Use", 0.6 * w)
        if any(k in n for k in ["price", "pricing", "royalty",
                                "subscription", "oem", "white label"]):
            bump("Use", 1.0 * w)
            bump("Value", 1.4 * w)
        if any(k in n for k in ["board", "report", "dashboard", "audit"]):
            bump("Report", 1.2 * w)
            bump("Monitor", 1.0 * w)

    ic_map: Dict[str, Any] = {}
    avg_leaf = (sum(leaf_scores.values()) / max(1, len(leaf_scores)))
    threshold = max(1.0, avg_leaf * 0.6)

    for leaf, score in leaf_scores.items():
        tick = score >= threshold
        if leaf == "Human":
            nar = (
                "Human Capital cues are present but limited; competency & training records should be formalised."
                if tick else
                "Human Capital not yet clearly evidenced; competency mapping and training logs are needed."
            )
        elif leaf == "Structural":
            nar = (
                "Structural Capital formalised (KMP/SOPs/process maps/ISO/QMS) enabling repeatable delivery."
                if tick else
                "Structural Capital under-documented; SOPs/KMP/ISO mapping recommended."
            )
        elif leaf == "Customer":
            nar = (
                "Customer Capital present (contracts/POs/channels), supporting recurring value capture."
                if tick else
                "Customer Capital weak in evidence; contracts/renewals/pipeline should be documented."
            )
        else:
            nar = (
                "Strategic Alliance Capital evidenced (JV/MoU/partners/universities/councils)."
                if tick else
                "Strategic alliances not clearly evidenced; JV/MoU documentation needed."
            )
        ic_map[leaf] = {"tick": tick, "narrative": nar, "score": round(score, 2)}

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

    files_factor = min(1.0, len(weights_by_file) / 6.0)
    leaf_div = sum(1 for v in ic_map.values() if v["tick"]) / 4.0
    weight_mean = (sum(weights_by_file.values()) / max(1, len(weights_by_file))) if weights_by_file else 0.4
    quality = int(round(100 * (0.45 * files_factor + 0.35 * leaf_div + 0.20 * min(1.0, weight_mean))))

    return ic_map, ten, leaf_scores, quality

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

    p1 = (
        f"{case} is a {size} in {sector}. Based on uploaded artefacts and expert context, "
        f"the company shows an emerging ability to codify and scale its operating model, "
        f"with measurable signals across {', '.join(strengths) if strengths else 'selected IC dimensions'}."
    )

    if strengths:
        p2a = f"Strengths concentrate in {', '.join(strengths)}" + (f"; gaps are {', '.join(gaps)}." if gaps else ".")
    else:
        p2a = "Strengths are not yet well-evidenced; additional artefacts are required."

    p2b = (
        "Evidence points to maturing structures (e.g., KMP/SOPs/process maps) and formal relationships "
        "(contracts/JVs) where present. Human capability and customer lifecycle signals improve markedly "
        "once competency maps, CRM data and renewal information are attached."
    )
    p2 = p2a + " " + p2b

    if strong_steps or weak_steps:
        p3 = (
            f"Ten-Steps patterns indicate strong {', '.join(strong_steps) if strong_steps else 'foundations'}; "
            f"progress is constrained by {', '.join(weak_steps) if weak_steps else 'later-stage governance and valuation readiness'}."
        )
    else:
        p3 = (
            "Ten-Steps scores suggest a developing baseline; expert review will refine scoring "
            "as artefacts are consolidated."
        )

    actions = [
        "Create a single IA Register linking contracts/JVs, SOPs/KMP, and product/service artefacts (source-of-truth).",
        "Introduce quarterly governance reporting (board pack + KPI dashboard) to strengthen Monitor/Report.",
        "Define valuation approach (IAS 38 fair value) and connect to licensing templates for near-term monetisation and multiple value streams.",
        "Formalise competency matrices and training logs to evidence Human Capital maturity.",
    ]
    p4 = "Assumptions & Action Plan:\n" + "\n".join([f"• {a}" for a in actions])

    missing = (
        "Request additional artefacts: CRM/renewal data, NDA/licence/royalty terms, "
        "board/management reports."
    )
    p5 = f"Evidence quality ≈ {evidence_quality}% (heuristic). {missing}"

    return "\n\n".join([p1, p2, p3, p4, p5])

# --------- IC ASSISTANT (LOCAL CHAT OVER CURRENT CASE) ----------
def _ic_chat_reply(question: str) -> str:
    """
    Lightweight, local 'chat' over the current case.
    It never calls an external API – it only uses:
      - combined_text / narrative
      - ic_map (4-leaf)
      - Ten-Steps scores
      - evidence_quality
      - basic FRAND / licensing logic
    """
    q = (question or "").lower()
    summary = st.session_state.get("combined_text", "") or st.session_state.get("narrative", "")
    ic_map = st.session_state.get("ic_map", {}) or {}
    ten = st.session_state.get("ten_steps", {}) or {}
    scores = ten.get("scores") or [5] * len(TEN_STEPS)
    narrs = ten.get("narratives") or [f"{s}: tbd" for s in TEN_STEPS]
    evidence_quality = int(st.session_state.get("evidence_quality", 0))
    sector = st.session_state.get("sector", "Other")
    size = st.session_state.get("company_size", "Micro (1–10)")
    case = st.session_state.get("case_name", "Untitled Company")

    parts: List[str] = []

    # Basic context header
    parts.append(
        f"You are looking at {case}, a {size} in {sector}. "
        f"Evidence coverage is currently about {evidence_quality}% (heuristic)."
    )

    # Structural / IAS 38 / audit readiness
    if any(k in q for k in ["structural", "structure", "systems", "sop", "iso", "audit", "ias 38", "ias38"]):
        row = ic_map.get("Structural", {})
        sc_score = row.get("score", 0.0)
        tick = row.get("tick", False)
        parts.append(
            "Structural Capital: the tool treats explicit, documented artefacts "
            "(contracts, specs, protocols, registers, KMP/SOPs, formal agreements) "
            "as Structural Capital in line with IAS 38 principles."
        )
        parts.append(
            f"For this case, Structural Capital is scored at about {sc_score:.1f} "
            f"and is {'evidenced strongly' if tick else 'still under-documented in the evidence bundle'}."
        )
        parts.append(
            "To strengthen audit-readiness you should: "
            "1) consolidate contracts and agreements into an IA Register, "
            "2) link each artefact to a product/service and revenue stream, "
            "3) ensure version-controlled SOPs, safety protocols, and governance docs are in place."
        )

    # Human Capital
    if "human" in q or "people" in q or "skills" in q:
        row = ic_map.get("Human", {})
        parts.append(
            "Human Capital: this covers tacit expertise, training, competencies and culture. "
            "The app looks for signals like training records, safety briefings, competency matrices and awards."
        )
        parts.append(f"Current Human Capital narrative: {row.get('narrative', '(no narrative yet)')}")

    # Customer Capital
    if "customer" in q or "clients" in q or "sales" in q or "revenue" in q:
        row = ic_map.get("Customer", {})
        parts.append(
            "Customer Capital: this covers contracts, renewals, pipeline, channel partners and retention. "
            "It is mostly tacit–plus–explicit, but still sits outside the balance sheet until fully structured."
        )
        parts.append(f"Current Customer Capital narrative: {row.get('narrative', '(no narrative yet)')}")

    # Strategic Alliance Capital
    if "alliance" in q or "partner" in q or "university" in q or "consortium" in q:
        row = ic_map.get("Strategic Alliance", {})
        parts.append(
            "Strategic Alliance Capital: this includes JVs, MoUs, grant agreements, university links and ecosystem partners. "
            "These relationships are critical for co-creation and non-traditional licensing."
        )
        parts.append(f"Current Strategic Alliance narrative: {row.get('narrative', '(no narrative yet)')}")

    # Ten-Steps / readiness
    if "ten steps" in q or "10 steps" in q or "readiness" in q or "maturity" in q:
        strong = [s for s, sc in zip(TEN_STEPS, scores) if sc >= 7]
        weak = [s for s, sc in zip(TEN_STEPS, scores) if sc <= 5]
        parts.append(
            "Ten-Steps readiness gives a quick sense of how well the company is identifying, "
            "separating, protecting, safeguarding, managing, controlling, using, monitoring, valuing and reporting on its IA."
        )
        parts.append(
            f"Stronger steps here: {', '.join(strong) if strong else 'no obvious strengths yet'}; "
            f"weaker steps: {', '.join(weak) if weak else 'no critical weaknesses flagged'}."
        )

    # FRAND, royalty-free, licensing, multiple value streams
    if any(k in q for k in ["frand", "licence", "license", "royalty", "royalties",
                            "non-traditional", "non traditional", "co-creation", "co creation"]):
        parts.append(
            "FRAND in this context is used as a fairness lens: Fair, Reasonable and Non-Discriminatory. "
            "It helps make sure access terms, pricing corridors and audit rights are proportionate and comparable "
            "across similar users."
        )
        parts.append(
            "The tool distinguishes different licence models: revenue licences (royalty-bearing), "
            "defensive licences (cross-licence / non-assert), co-creation licences (shared Foreground IP), "
            "and knowledge / community licences that may be royalty-free but still FRAND-aligned on access conditions."
        )
        parts.append(
            "When reports talk about 'multiple simultaneous value streams', they mean combining core product revenue "
            "with additional flows from data, methods, software, training, and partnerships – each with its own licence path."
        )

    # Seven Stakeholders / ESG / double materiality
    if any(k in q for k in ["stakeholder", "seven stakeholders", "7 stakeholders", "esg", "double materiality", "impact"]):
        parts.append(
            "The analysis is framed by the Seven Stakeholder Model (Sugai & Weir): "
            "employees, customers, investors, nature, suppliers, partners and the wider community."
        )
        parts.append(
            "Double materiality means we look both at financial materiality (how IA and ESG affect value) and "
            "impact materiality (how the company affects those stakeholders and nature). "
            "Licensing and commercialisation strategies should be checked against both dimensions."
        )

    # Valuation / balance sheet
    if "valuation" in q or "value" in q or "balance sheet" in q:
        parts.append(
            "This demo tool stops at 'audit-readiness' and licensing readiness. "
            "Full monetary valuation under IAS 38 uses Areopa's proprietary multi-formula model "
            "and would sit in a separate valuation workbook or IC Compass Enterprise."
        )

    # If nothing matched, fall back to summary
    if len(parts) <= 1:
        if summary:
            parts.append("Here is a concise reading of the current case, based on the latest narrative:")
            parts.append(summary[:900])
        else:
            parts.append(
                "I don't yet have much narrative to work with. "
                "Try running the analysis first and/or adding more evidence and expert context."
            )

    return "\n\n".join(parts)

# --------- EXPERT CONTEXT AUTO-SPLIT HELPER ----------
def _auto_split_expert_block(text: str) -> Dict[str, str]:
    """
    Take a single pasted block and try to split it across:
    why_service, stage, plan_s, plan_m, plan_l, markets_why, sale_price_why
    using blank lines or sentence boundaries. This is intentionally simple
    and just meant to reduce typing for the expert.
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

    # First try paragraphs split by blank lines
    blocks = [b.strip() for b in t.replace("\r\n", "\n").split("\n\n") if b.strip()]

    # If still short, fall back to sentence-based split
    if len(blocks) < 5:
        blocks = [s.strip() for s in re.split(r"(?<=[.!?])\s+", t) if s.strip()]

    out: Dict[str, str] = {k: "" for k in keys}
    for k, chunk in zip(keys, blocks):
        out[k] = chunk
    return out

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
ss.setdefault("chat_history", [])

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
    (
        "Company",
        "Analyse Evidence",
        "Expert View",
        "Ask IC Assistant",
        "Reports",
        "Licensing Templates",
    ),
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

        st.markdown("#### Expert Context (required)")
        full_block = st.text_area(
            "Optional: paste full expert context here (one block, then auto-fill below)",
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
                st.success("Saved company details & expert context.")

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
        ten = ss.get("ten_steps", {"scores": [5] * len(TEN_STEPS), "narratives": [f"{s}: tbd" for s in TEN_STEPS]})

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
        "Summary view (read-only; editable in Expert View)",
        combined[:5000],
        height=260,
        key="combined_preview",
    )

    if st.button("Run analysis now"):
        uploads: List[Any] = ss.get("uploads") or []
        extracted, counts, weights = _read_text(uploads)

        ss["file_counts"] = counts or {}

        # Build expert-context dict (fed into interpreter, but not blindly copied)
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

        ic_map, ten, leaf_scores, quality = _analyse_weighted(combined_text_for_detection, weights)

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

        st.success("Analysis complete. Open **Expert View** to refine and export.")

# 3) EXPERT VIEW
elif page == "Expert View":
    st.header("Narrative Summary")
    nar = st.text_area(
        "Summary (editable)",
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

        st.subheader("Expert Context (read-only)")
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

# 3b) ASK IC ASSISTANT (LOCAL CHAT)
elif page == "Ask IC Assistant":
    st.header("Ask IC Assistant (beta)")
    st.caption(
        "This chat uses the current IC and Licensing analysis to answer questions. "
        "It does not change scores or reports – it just helps you interpret them."
    )

    history: List[Tuple[str, str]] = ss.get("chat_history", [])

    question = st.text_area(
        "Type your question about this case (e.g. 'How strong is our Structural Capital?' "
        "or 'What does FRAND mean for a royalty-free community licence?')",
        key="ic_chat_q",
        height=80,
    )

    col_q1, col_q2 = st.columns([1, 1])
    with col_q1:
        if st.button("Ask", key="ask_ic_chat_btn"):
            if question.strip():
                reply = _ic_chat_reply(question.strip())
                history.append(("user", question.strip()))
                history.append(("assistant", reply))
                ss["chat_history"] = history
    with col_q2:
        if st.button("Clear history", key="clear_ic_chat"):
            ss["chat_history"] = []
            history = []

    st.markdown("---")
    if not history:
        st.caption("No questions yet. Ask something above to start the conversation.")
    else:
        for role, text in history:
            if role == "user":
                st.markdown(f"**You:** {text}")
            else:
                st.markdown(f"**IC Assistant:** {text}")

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
            else "CONFIDENTIAL. Advisory-first; expert review required for final scoring and accounting treatment."
        )
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
        b.append(
            "IA Register maintained; evidence bundles per licence; regular royalty/performance "
            "reporting aligned to board and investor expectations."
        )
        if PUBLIC_MODE:
            b.append("\n(Details suppressed in public mode.)")
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
        if template == "FRAND Standard":
            title = f"FRAND Standard template — {case}"
            body = (
                f"FRAND Standard — {case} ({sector})\n\n"
                "Scope, definitions, essentiality clause, non-discrimination clause, reasonable fee corridor, "
                "audit & verification, termination, governing law (EU), dispute resolution.\n"
            )
        elif template == "Co-creation (Joint Development)":
            title = f"Co-creation template — {case}"
            body = (
                f"Co-creation / Joint Development — {case} ({sector})\n\n"
                "Background IP, Foreground IP, contributions, ownership split, publication rights, "
                "commercial model, revenue sharing, exit/assignment, FRAND alignment where applicable.\n"
            )
        else:
            title = f"Knowledge licence (non-traditional) — {case}"
            body = (
                f"Knowledge Licence — {case} ({sector})\n\n"
                "Codified know-how (copyright/trade secret), permitted fields of use, attribution, "
                "commercial vs social-benefit pathways, verification, revocation, jurisdiction.\n"
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
