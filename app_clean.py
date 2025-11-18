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

# 3) LIP CONSOLE
elif page == "LIP Console":
    st.header("LIP Console — Narrative, IC Map & Verification")

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

        st.subheader("Asset & Evidence Verification (summary)")
        ev = ss.get("evidence_check", {})
        if ev:
            st.markdown(f"- **Evidence focus:** {ev.get('focus', '—')}")
            st.markdown(f"- **Evidence quality:** {ev.get('quality', '—')}/5")
            st.markdown(f"- **Assurance:** {ev.get('assurance', '—')}")
            if ev.get("comments"):
                st.markdown(f"- **Comments:** {ev.get('comments')}")
        else:
            st.caption("No evidence-level verification notes saved yet.")

        assets = ss.get("asset_verification", []) or []
        if assets:
            st.markdown("**Key assets logged:**")
            for a in assets:
                st.markdown(
                    f"- **{a.get('name','')}** "
                    f"({a.get('type','')}, 4-Leaf: {a.get('leaf','')}, status: {a.get('status','')})"
                )
                if a.get("risks"):
                    st.caption("  • Risks: " + ", ".join(a["risks"]))
        else:
            st.caption("No assets have been recorded in the verification panel.")

        st.subheader("Translation layer (manual capture)")
        lang = st.selectbox(
            "Translated summary language",
            ["None", "French", "German", "Spanish", "Italian", "Arabic", "Other"],
            index=["None", "French", "German", "Spanish", "Italian", "Arabic", "Other"].index(
                ss.get("translation_lang", "None")
            ),
        )
        trans_text = st.text_area(
            "Translated version of the summary (paste human / external translation here)",
            ss.get("translation_text", ""),
            height=120,
        )
        if st.button("Save translation"):
            ss["translation_lang"] = lang
            ss["translation_text"] = trans_text.strip()
            st.success("Saved translated summary in session.")

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

        # Optional translated summary
        if ss.get("translation_lang", "None") != "None" and ss.get("translation_text"):
            b.append(
                f"Translated Summary ({ss.get('translation_lang')}):\n\n"
                f"{ss.get('translation_text')}\n"
            )

        b.append("Four-Leaf Analysis")
        for leaf in ["Human", "Structural", "Customer", "Strategic Alliance"]:
            row = ic_map.get(leaf, {"tick": False, "narrative": "", "score": 0.0})
            tail = "" if PUBLIC_MODE else f" (score: {row.get('score', 0.0)})"
            b.append(f"- {leaf}: {'✓' if row.get('tick') else '•'} — {row.get('narrative', '')}{tail}")

        b.append("\nTen-Steps Readiness")
        for s, n in zip(TEN_STEPS, ten["narratives"]):
            b.append(f"- {n}")

        # Asset & Evidence Verification section
        ev = ss.get("evidence_check", {})
        assets = ss.get("asset_verification", []) or []
        b.append("\nAsset & Evidence Verification")
        if ev:
            b.append(
                f"Main evidence focus: {ev.get('focus','n/a')}. "
                f"Overall evidence quality was rated {ev.get('quality','-')}/5 with assurance level "
                f"'{ev.get('assurance','n/a')}'."
            )
            if ev.get("comments"):
                b.append(f"LIP comments on evidence: {ev.get('comments')}")
        else:
            b.append("No structured evidence-level verification notes were recorded in this run.")

        if assets:
            b.append("Key assets logged for verification:")
            for a in assets:
                line = (
                    f"- {a.get('name','')} "
                    f"(type: {a.get('type','')}, 4-Leaf home: {a.get('leaf','')}, "
                    f"status: {a.get('status','')})"
                )
                b.append(line)
                if a.get("risks"):
                    b.append("  • Risks: " + ", ".join(a["risks"]))
        else:
            b.append("No specific assets were recorded in the verification panel.")

        b.append("\nNotes")
        b.append(
            "This document is provided for high-level evaluation only."
            if PUBLIC_MODE
            else "CONFIDENTIAL. Advisory-first; company and LIP review required for final scoring, licensing design and accounting treatment."
        )
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

# 6) LIP ASSISTANT (local helper)
elif page == "LIP Assistant":
    st.header("LIP Assistant (beta)")
    st.caption(
        "A lightweight helper for the Licensing & Intangibles Partner. "
        "It re-uses the IC narrative and licensing logic locally — no external AI calls are made in this demo."
    )

    if ss.get("combined_text", ""):
        st.success("IC narrative available from Analyse Evidence / LIP Console.")
    else:
        st.warning("No IC narrative stored yet. Run **Analyse Evidence** first for best results.")

    context_choice = st.selectbox(
        "Which context should the LIP Assistant focus on?",
        ["IC findings", "Licensing options", "Both"],
        index=2,
    )

    question = st.text_area(
        "Your question",
        "",
        height=120,
        help="Example: 'Which assets look IAS 38-ready?' or 'How could we structure a royalty-free community licence?'",
    )

    if st.button("Ask LIP Assistant"):
        if not question.strip():
            st.error("Please enter a question.")
        else:
            ic_text = ss.get("combined_text", "")
            lic_snippet = (
                "The tool supports revenue licences, access/community licences, co-creation/joint development, "
                "defensive/cross-licence arrangements and data/algorithm licences, all treated through a FRAND-informed "
                "lens across the Seven Stakeholder Model."
            )

            answer_parts: List[str] = []
            answer_parts.append(f"**Question received:** {question.strip()}")

            q_lower = question.lower()

            if context_choice in ("IC findings", "Both"):
                answer_parts.append("**IC & Structural Capital view (IAS 38):**")
                if "structural" in q_lower or "ias 38" in q_lower:
                    answer_parts.append(
                        "- Structural Capital is treated as the home for explicit, documented assets "
                        "(contracts, SOPs, registers, CRM, datasets, board packs). Where both tacit and explicit "
                        "signals exist, Structural is deliberately weighted to dominate, reflecting IAS 38 audit-readiness."
                    )
                if ic_text:
                    answer_parts.append(
                        "- Key IC narrative extract:\n\n"
                        + ic_text[:600]
                        + ("..." if len(ic_text) > 600 else "")
                    )
                else:
                    answer_parts.append(
                        "- No stored IC narrative yet. Run the analysis and revisit this view to see a richer explanation."
                    )

            if context_choice in ("Licensing options", "Both"):
                answer_parts.append("**Licensing & FRAND view:**")
                if "frand" in q_lower:
                    answer_parts.append(
                        "- In this tool, FRAND is a *design principle* rather than a legal certification. "
                        "It guides how pricing, access tiers and governance are framed across different stakeholders, "
                        "including royalty-free and community licences."
                    )
                answer_parts.append("- " + lic_snippet)

            # Connect to verification layer
            ev = ss.get("evidence_check", {})
            assets = ss.get("asset_verification", []) or []
            if ev or assets:
                answer_parts.append("**Asset & Evidence Verification context:**")
                if ev:
                    answer_parts.append(
                        f"- Main evidence focus: {ev.get('focus','n/a')}, quality {ev.get('quality','-')}/5, "
                        f"assurance: {ev.get('assurance','n/a')}."
                    )
                if assets:
                    verified = [a for a in assets if a.get("status") == "Verified with company"]
                    if verified:
                        names = ", ".join(a.get("name", "") for a in verified)
                        answer_parts.append(f"- Verified assets: {names}.")
                    risky = [a for a in assets if a.get("risks")]
                    if risky:
                        answer_parts.append(
                            "- Some assets carry explicit risk flags; review the verification section in LIP Console "
                            "before finalising any licensing recommendation."
                        )

            answer_parts.append(
                "_Next step: a Licensing & Intangibles Partner can tailor these insights into concrete clauses using the "
                "reports and templates generated in the other pages._"
            )

            ss["lip_history"].append({"q": question.strip(), "a": "\n\n".join(answer_parts)})
            st.markdown("\n\n".join(answer_parts))

    if ss.get("lip_history"):
        with st.expander("Previous LIP Assistant exchanges"):
            for i, entry in enumerate(reversed(ss["lip_history"]), start=1):
                st.markdown(f"**Q{i}:** {entry['q']}")
                st.markdown(entry["a"])
                st.markdown("---")


  
