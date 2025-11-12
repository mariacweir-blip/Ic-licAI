# app.py — IC-LicAI Expert Console (Locked build + Expert Context prompts)
# Changes vs prior: adds 5 required expert questions; folds answers into analysis & reports;
# shows warnings for thin evidence; stays compatible with Streamlit 1.38.

from __future__ import annotations
import io, os, tempfile
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import streamlit as st

# -------------------- MODE / AUTH --------------------
PUBLIC_MODE: bool = False       # False = internal (richer text + watermark + server save)
REQUIRE_PASS: bool = True       # Passphrase gate if APP_KEY is set

# ---------------- DOCX optional ----------------------
try:
    from docx import Document  # type: ignore
    HAVE_DOCX = True
except Exception:
    HAVE_DOCX = False

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
        st.error("Incorrect passphrase."); st.stop()
_auth_gate()

# --------------- WRITABLE ROOT -----------------------
def _detect_writable_root() -> Path:
    for p in [Path("./out"), Path(os.path.expanduser("~"))/"out", Path(tempfile.gettempdir())/"ic-licai-out"]:
        try:
            p.mkdir(parents=True, exist_ok=True)
            t = p/".touch"; t.write_text("ok", encoding="utf-8"); t.unlink()
            return p
        except Exception:
            continue
    return Path(tempfile.gettempdir())
OUT_ROOT = _detect_writable_root()
def _ensure_dir(p: Path) -> None: p.mkdir(parents=True, exist_ok=True)
def _safe(name: str) -> str:
    return "".join(c for c in (name or "").strip() if c.isalnum() or c in (" ","_","-",".")).strip().replace(" ","_")

def _export_bytes(title: str, body: str) -> Tuple[bytes, str, str]:
    base = _safe(title) or "ICLicAI_Report"
    if HAVE_DOCX:
        doc = Document()
        if not PUBLIC_MODE:
            doc.add_paragraph().add_run("CONFIDENTIAL — Internal Evaluation Draft (No Distribution)").bold = True
        doc.add_heading(title, 0)
        for para in body.split("\n\n"):
            doc.add_paragraph(para)
        bio = io.BytesIO(); doc.save(bio)
        return bio.getvalue(), f"{base}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if not PUBLIC_MODE:
        body = "CONFIDENTIAL — Internal Evaluation Draft (No Distribution)\n\n" + body
    return body.encode("utf-8"), f"{base}.txt", "text/plain"

def _save_bytes(folder: Path, name: str, data: bytes) -> Tuple[Optional[Path], str]:
    if PUBLIC_MODE:
        return None, "Public mode: server save disabled (download only)."
    try:
        _ensure_dir(folder); p = folder/name; p.write_bytes(data); return p, f"Saved to {p}"
    except Exception as e:
        return None, f"Server save skipped ({type(e).__name__}: {e}). Download still works."

# --------------- EVIDENCE INGEST ---------------------
TEXT_EXT = {".txt", ".csv"}
def _read_text(files: List[Any]) -> Tuple[str, Dict[str,int]]:
    chunks: List[str] = []; counts: Dict[str,int] = {}
    for f in files or []:
        name = getattr(f, "name", "file"); ext = Path(str(name).lower()).suffix or "none"
        counts[ext] = counts.get(ext, 0) + 1
        try:
            if ext in TEXT_EXT:
                chunks.append(f.read().decode("utf-8", errors="ignore"))
            else:
                chunks.append(f"[[FILE:{name}]]")
        except Exception:
            chunks.append(f"[[FILE:{name}]]")
    return "\n".join(chunks), counts

# --------------- SME cues / analysis -----------------
FOUR_LEAF_KEYS: Dict[str, List[str]] = {
    "Human": ["team","staff","employee","hire","recruit","training","trained","trainer","onboarding","mentor","apprentice","qualification","certified","cpd","skills matrix"],
    "Structural": ["process","procedure","sop","workflow","policy","template","checklist","system","crm","erp","sharepoint","database","knowledge base","qms","iso 9001","iso 27001","ip register","asset register","method","spec","playbook","datasheet","architecture"],
    "Customer": ["client","customer","account","lead","opportunity","pipeline","quote","proposal","contract","msa","sow","sla","purchase order","po","invoice","renewal","retention","distributor","reseller","channel","customer success"],
    "Strategic Alliance": ["partner","partnership","alliance","strategic","mou","joint venture","framework agreement","collaboration","consortium","university","college","council","ngo","integrator","oem","supplier agreement","grant agreement","licensor","licensee"],
}
TEN_STEPS = ["Identify","Separate","Protect","Safeguard","Manage","Control","Use","Monitor","Value","Report"]
SECTOR_CUES = {
    "GreenTech": ["recycling","waste","biomass","circular","emissions","co2e","solar","pv","turbine","kwh","energy efficiency","retrofit","heat pump","iso 14001","esg","sdg","ofgem","lca"],
    "MedTech":  ["iso 13485","mhra","ce mark","clinical","gcp","patient","medical device","pms","post-market surveillance"],
    "AgriTech": ["soil","irrigation","seed","fertiliser","biomass","yield","farm"],
}

def _count_hits(text: str, words: List[str]) -> int:
    t = text; return sum(1 for w in words if w in t)

def _analyse(text: str) -> Tuple[Dict[str, Any], Dict[str, Any], str, Dict[str,int], int]:
    t = (text or "").lower()
    sector = st.session_state.get("sector","Other")
    ic_map: Dict[str, Any] = {}; hit_counts: Dict[str,int] = {}

    for leaf, cues in FOUR_LEAF_KEYS.items():
        effective = list(cues)
        if sector in SECTOR_CUES and leaf in ("Structural","Customer","Strategic Alliance"):
            effective += SECTOR_CUES[sector]
        hits = _count_hits(t, effective); hit_counts[leaf] = hits; tick = hits > 0
        if PUBLIC_MODE:
            nar = "Signals detected." if tick else "No clear signals detected."
        else:
            if leaf == "Human": nar = "Human Capital evidenced (people/roles/training)." if tick else "No strong people/skills cues detected."
            elif leaf == "Structural": nar = "Structural Capital present (SOPs/processes/systems/registers/ISO/QMS)." if tick else "No explicit systems/processes/registers referenced."
            elif leaf == "Customer": nar = "Customer Capital indicated (contracts/POs/CRM/pipeline/channels)." if tick else "Little/no explicit evidence of customer relationships."
            else: nar = "Strategic alliances present (partners/MoUs/JVs/universities/councils/grants)." if tick else "No clear references to strategic partners/alliances."
        ic_map[leaf] = {"tick": tick, "narrative": nar, "hits": hits}

    base = 3
    boosts = {
        "Identify": 2 if any(w in t for w in ["asset","intangible","know-how","dataset","algorithm"]) else 0,
        "Separate": 2 if any(w in t for w in ["register","inventory","taxonomy","asset list"]) else 0,
        "Protect": 3 if any(w in t for w in ["nda","confidentiality","trade secret","copyright","trademark","®","™","patent"]) else 0,
        "Safeguard": 2 if any(w in t for w in ["backup","version control","encryption","access control","retention"]) else 0,
        "Manage": 2 if any(w in t for w in ["sop","policy","owner","raci","governance","qms"]) else 0,
        "Control": 2 if any(w in t for w in ["rights","ownership","assign","exclusive","non-exclusive"]) else 0,
        "Use": 3 if any(w in t for w in ["licence","license","oem","white label","royalty","subscription","per seat","saas","pricing"]) else 0,
        "Monitor": 2 if any(w in t for w in ["kpi","dashboard","audit","monthly report","iso audit"]) else 0,
        "Value": 3 if any(w in t for w in ["valuation","pricing model","ias 38","frs 102","amortisation","fair value"]) else 0,
        "Report": 2 if any(w in t for w in ["board pack","management report","investor update","governance report"]) else 0,
    }
    if sector in SECTOR_CUES and any(c in t for c in SECTOR_CUES[sector]):
        boosts["Use"] = max(boosts["Use"], 1); boosts["Report"] = max(boosts["Report"], 1)

    scores: List[int] = []; narrs: List[str] = []
    for step in TEN_STEPS:
        s = max(1, min(10, base + boosts.get(step, 0))); scores.append(s)
        narrs.append(f"{step}: readiness ≈ {s}/10." if PUBLIC_MODE else f"{step}: readiness ≈ {s}/10 based on SME-language cues in evidence.")
    ten = {"scores": scores, "narratives": narrs}

    families_total = 4 + len(TEN_STEPS)
    families_hit = sum(1 for v in ic_map.values() if v["tick"]) + sum(1 for x in scores if x > base)
    quality = int(round(100 * families_hit / max(1, families_total)))

    ticks = [k for k, v in ic_map.items() if v["tick"]]; gaps = [k for k, v in ic_map.items() if not v["tick"]]
    if PUBLIC_MODE:
        summary = f"{st.session_state.get('case_name','Untitled Customer')} — baseline IC signals: {', '.join(ticks) if ticks else 'none detected'}."
    else:
        summary = (
            f"{st.session_state.get('case_name','Untitled Customer')} is a "
            f"{st.session_state.get('company_size','Micro (1–10)')} in {st.session_state.get('sector','Other')}.\n"
            f"Evidence suggests: {', '.join(ticks) if ticks else 'no obvious IC signals'}"
            f"{'; gaps: ' + ', '.join(gaps) if gaps else ''}.\n"
            "Ten-Steps scores are heuristic — experts should review and adjust."
        )
    return ic_map, ten, summary, hit_counts, quality

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
ss.setdefault("hit_counts", {})
ss.setdefault("evidence_quality", 0)
# Expert prompts
ss.setdefault("why_service", "")
ss.setdefault("stage", "")
ss.setdefault("plan_s", "")
ss.setdefault("plan_m", "")
ss.setdefault("plan_l", "")
ss.setdefault("markets_why", "")
ss.setdefault("sale_price_why", "")

SIZES = ["Micro (1–10)","Small (11–50)","Medium (51–250)","Large (250+)"]
SECTORS = ["Food & Beverage","MedTech","GreenTech","AgriTech","Biotech","Software/SaaS","FinTech","EdTech","Manufacturing","Creative/Digital","Professional Services","Mobility/Transport","Energy","Other"]

# -------------------- NAV ---------------------------
st.sidebar.markdown("### Navigate")
page = st.sidebar.radio("", ("Customer","Analyse Evidence","Expert View","Reports","Licensing Templates"), index=0, key="nav")

# -------------------- PAGES -------------------------

# 1) CUSTOMER (with required prompts)
if page == "Customer":
    st.header("Customer details")
    with st.form("customer_form"):
        c1, c2, c3 = st.columns([1.1,1,1])
        with c1:
            case_name = st.text_input("Customer / Company name *", ss.get("case_name",""))
        with c2:
            size = st.selectbox("Company size", SIZES, index=SIZES.index(ss.get("company_size", SIZES[0])))
        with c3:
            current_sector = ss.get("sector","Other")
            sector_index = SECTORS.index(current_sector) if current_sector in SECTORS else SECTORS.index("Other")
            sector = st.selectbox("Sector / Industry", SECTORS, index=sector_index)

        st.markdown("#### Expert Context (required)")
        why_service = st.text_area("1) Why is the customer seeking this service? *", ss.get("why_service",""), height=90)
        stage = st.text_area("2) What stage are the products/services at? *", ss.get("stage",""), height=90)
        c4, c5, c6 = st.columns(3)
        with c4:
            plan_s = st.text_area("3a) Short-term plan (0–6m) *", ss.get("plan_s",""), height=90)
        with c5:
            plan_m = st.text_area("3b) Medium-term plan (6–24m) *", ss.get("plan_m",""), height=90)
        with c6:
            plan_l = st.text_area("3c) Long-term plan (24m+) *", ss.get("plan_l",""), height=90)
        markets_why = st.text_area("4) Which markets fit and why? *", ss.get("markets_why",""), height=90)
        sale_price_why = st.text_area("5) If selling tomorrow, target price & why? *", ss.get("sale_price_why",""), height=90)

        st.caption("Uploads are held in session until analysis. Nothing is written to server until export.")
        uploads = st.file_uploader("Upload evidence (PDF, DOCX, TXT, CSV, XLSX, PPTX, images)",
                                   type=["pdf","docx","txt","csv","xlsx","pptx","png","jpg","jpeg","webp"],
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
                if uploads: ss["uploads"] = uploads
                st.success("Saved customer details & expert context.")
    if ss.get("uploads"):
        st.info(f"{len(ss['uploads'])} file(s) stored in session. Go to **Analyse Evidence** next.")

# 2) ANALYSE EVIDENCE
elif page == "Analyse Evidence":
    st.header("Analyse & build narrative (preview)")
    combined = ss.get("combined_text","")
    st.text_area("Preview extracted / combined evidence (first 5000 chars)", combined[:5000], height=220, key="combined_preview")

    if st.button("Run analysis now"):
        uploads: List[Any] = ss.get("uploads") or []
        extracted, _ = _read_text(uploads)

        # Build expert-context header to avoid blank preview
        context_lines = [
            f"## EXPERT CONTEXT — {ss.get('case_name','Untitled Customer')}",
            f"Why service: {ss.get('why_service','(n/a)')}",
            f"Stage: {ss.get('stage','(n/a)')}",
            f"Plans — S: {ss.get('plan_s','(n/a)')} | M: {ss.get('plan_m','(n/a)')} | L: {ss.get('plan_l','(n/a)')}",
            f"Markets & why: {ss.get('markets_why','(n/a)')}",
            f"Target sale & why: {ss.get('sale_price_why','(n/a)')}",
        ]
        header_text = "\n".join(context_lines)

        notes = ss.get("notes","").strip()
        combined_text = "\n\n".join([header_text, extracted.strip(), notes]) if notes else "\n\n".join([header_text, extracted.strip()])
        ss["combined_text"] = combined_text.strip()

        ic_map, ten, summary, hits, quality = _analyse(combined_text)
        ss["ic_map"] = ic_map; ss["ten_steps"] = ten; ss["narrative"] = summary
        ss["hit_counts"] = hits; ss["evidence_quality"] = quality

        if len((extracted or "").strip()) < 50:
            st.warning("Very little machine-readable evidence detected. Expert Context has been used to seed the analysis. Consider uploading TXT/CSV or adding notes.")

        st.success("Analysis complete. Open **Expert View** to refine and export.")

# 3) EXPERT VIEW
elif page == "Expert View":
    st.header("Narrative Summary")
    nar = st.text_area("Summary (editable)", value=ss.get("narrative",""), height=160, key="nar_edit")
    ss["narrative"] = nar

    colA, colB = st.columns([1,1])
    with colA:
        if not PUBLIC_MODE:
            st.subheader("Evidence Quality")
            st.progress(min(100, max(0, ss.get("evidence_quality", 0))) / 100.0)
            st.caption(f"{ss.get('evidence_quality',0)}% evidence coverage (heuristic)")

        st.subheader("4-Leaf Map")
        ic_map: Dict[str, Any] = ss.get("ic_map", {})
        for leaf in ["Human","Structural","Customer","Strategic Alliance"]:
            row = ic_map.get(leaf, {"tick": False, "narrative": f"No assessment yet for {leaf}.", "hits": 0})
            tick = "✓" if row["tick"] else "•"
            suffix = "" if PUBLIC_MODE else f"  _(hits: {row.get('hits',0)})_"
            st.markdown(f"- **{leaf}**: {tick}{suffix}")
            st.caption(row["narrative"])

        st.subheader("Expert Context (read-only)")
        st.markdown(f"- **Why service:** {ss.get('why_service','') or '—'}")
        st.markdown(f"- **Stage:** {ss.get('stage','') or '—'}")
        st.markdown(f"- **Plans:** S={ss.get('plan_s','') or '—'} | M={ss.get('plan_m','') or '—'} | L={ss.get('plan_l','') or '—'}")
        st.markdown(f"- **Markets & why:** {ss.get('markets_why','') or '—'}")
        st.markdown(f"- **Target sale & why:** {ss.get('sale_price_why','') or '—'}")

    with colB:
        st.subheader("10-Steps Readiness")
        ten = ss.get("ten_steps", {"scores":[5]*10, "narratives":[f"{s}: tbd" for s in TEN_STEPS]})
        st.dataframe({"Step": TEN_STEPS, "Score (1–10)": ten["scores"]}, hide_index=True, use_container_width=True)
        with st.expander("Narrative per step"):
            for s, n in zip(TEN_STEPS, ten["narratives"]):
                st.markdown(f"**{s}** — {n}")

# 4) REPORTS
elif page == "Reports":
    st.header("Reports & Exports")
    case_name = ss.get("case_name","Untitled_Customer")
    case_folder = OUT_ROOT / _safe(case_name)

    def _compose_ic() -> Tuple[str,str]:
        title = f"IC Report — {case_name}"
        ic_map = ss.get("ic_map", {})
        ten = ss.get("ten_steps", {"scores":[5]*10, "narratives":[f"{s}: tbd" for s in TEN_STEPS]})
        b: List[str] = []
        b.append(f"Executive Summary\n\n{ss.get('narrative','(no summary)')}\n")
        if not PUBLIC_MODE:
            b.append(f"Evidence Quality: ~{ss.get('evidence_quality',0)}% coverage (heuristic)\n")

        b.append("Expert Context")
        b.append(f"- Why service: {ss.get('why_service','')}")
        b.append(f"- Stage: {ss.get('stage','')}")
        b.append(f"- Plans: S={ss.get('plan_s','')} | M={ss.get('plan_m','')} | L={ss.get('plan_l','')}")
        b.append(f"- Markets & why: {ss.get('markets_why','')}")
        b.append(f"- Target sale & why: {ss.get('sale_price_why','')}\n")

        b.append("Four-Leaf Analysis")
        for leaf in ["Human","Structural","Customer","Strategic Alliance"]:
            row = ic_map.get(leaf, {"tick": False, "narrative": "", "hits": 0})
            tail = "" if PUBLIC_MODE else f" (hits: {row.get('hits',0)})"
            b.append(f"- {leaf}: {'✓' if row.get('tick') else '•'} — {row.get('narrative','')}{tail}")

        b.append("\nTen-Steps Readiness")
        for s, n in zip(TEN_STEPS, ten["narratives"]):
            b.append(f"- {n}")

        b.append("\nNotes")
        b.append("This document is provided for high-level evaluation only." if PUBLIC_MODE
                 else "CONFIDENTIAL. Advisory-first; expert review required for final scoring and accounting treatment.")
        return title, "\n".join(b)

    def _compose_lic() -> Tuple[str,str]:
        title = f"Licensing Report — {case_name}"
        b: List[str] = []
        b.append(f"Licensing Options & FRAND Readiness for {case_name}\n")
        b.append("Expert Context")
        b.append(f"- Why service: {ss.get('why_service','')}")
        b.append(f"- Target sale & why: {ss.get('sale_price_why','')}\n")
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
            title, body = _compose_ic(); data, fname, mime = _export_bytes(title, body)
            path, msg = _save_bytes(case_folder, fname, data)
            st.download_button("⬇️ Download IC Report", data, file_name=fname, mime=mime, key="dl_ic")
            (st.success if path else st.warning)(msg)
    with c2:
        if st.button("Generate Licensing Report (DOCX/TXT)", key="btn_lic"):
            title, body = _compose_lic(); data, fname, mime = _export_bytes(title, body)
            path, msg = _save_bytes(case_folder, fname, data)
            st.download_button("⬇️ Download Licensing Report", data, file_name=fname, mime=mime, key="dl_lic")
            (st.success if path else st.warning)(msg)
    st.caption("Server save root: disabled (public mode)" if PUBLIC_MODE else f"Server save root: {OUT_ROOT}")

# 5) LICENSING TEMPLATES
elif page == "Licensing Templates":
    st.header("Licensing Templates (editable DOCX/TXT)")
    case = ss.get("case_name","Untitled Customer"); sector = ss.get("sector","Other")
    template = st.selectbox("Choose a template:", ["FRAND Standard","Co-creation (Joint Development)","Knowledge (Non-traditional)"], index=0)
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
        folder = OUT_ROOT / _safe(case); path, msg = _save_bytes(folder, fname, data)
        st.download_button("⬇️ Download Template", data, file_name=fname, mime=mime, key="dl_tpl")
        (st.success if path else st.warning)(msg)
