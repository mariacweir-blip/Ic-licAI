# app_clean.py — IC-LicAI Expert Console (EU theme, TTO-licensing version)

from __future__ import annotations
import io
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple

import streamlit as st

# -------- Optional DOCX support (falls back to .txt if missing) --------
try:
    from docx import Document  # type: ignore
    HAVE_DOCX = True
except Exception:
    HAVE_DOCX = False

# ========== UI THEME (Navy + Pale Yellow) ==========
st.set_page_config(page_title="IC-LicAI Expert Console", layout="wide")

def _inject_theme():
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

# ========== Helpers ==========
OUT_ROOT = Path("./out")  # Streamlit Cloud can write here

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _safe_filename(name: str) -> str:
    return "".join(
        c for c in name.strip() if c.isalnum() or c in (" ", "_", "-", ".")
    ).strip().replace(" ", "_")

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
        return (
            bio.getvalue(),
            f"{base}.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    else:
        data = body.encode("utf-8")
        return data, f"{base}.txt", "text/plain"

def _save_bytes_to_server(folder: Path, std_name: str, data: bytes) -> Path:
    """
    Saves into ./out/<Customer>/<std_name> (writable on Streamlit Cloud).
    """
    _ensure_dir(folder)
    p = folder / std_name
    p.write_bytes(data)
    return p

# -------- Minimal evidence extraction (demo-safe) --------
TEXT_EXT = {".txt", ".csv"}

def _read_text_from_uploads(files: List[Any]) -> str:
    chunks: List[str] = []
    for f in files:
        name = f.name.lower()
        ext = Path(name).suffix
        try:
            if ext in TEXT_EXT:
                chunks.append(f.read().decode("utf-8", errors="ignore"))
            else:
                # For PDFs/DOCX/PPTX/Images etc. demo uses filename cues only
                chunks.append(f"[[FILE:{f.name}]]")
        except Exception:
            chunks.append(f"[[FILE:{f.name}]]")
    return "\n".join(chunks)

# -------- Heuristics (SME-friendly) --------
FOUR_LEAF_KEYS = {
    "Human": [
        # people & skills (SME wording)
        "team", "staff", "employee", "hire", "recruit", "training", "trained", "trainer", "onboarding",
        "mentor", "apprentice", "nvq", "cscs", "cim", "cips", "qualification", "certified", "cpd",
        "safety training", "toolbox talk", "shift rota", "skills matrix",
    ],
    "Structural": [
        # processes, systems, IP registers (no IC jargon needed)
        "process", "processes", "procedure", "sop", "workflow", "policy", "template", "checklist",
        "system", "crm", "erp", "sharepoint", "database", "knowledge base", "qms", "iso 9001", "iso 27001",
        "ip register", "asset register", "method", "spec", "playbook", "datasheet", "architecture",
    ],
    "Customer": [
        # contracts, pipeline, channel
        "client", "customer", "account", "lead", "opportunity", "pipeline", "crm", "quote", "proposal",
        "contract", "msa", "sow", "sla", "purchase order", "po", "invoice", "renewal", "retention",
        "distributor", "reseller", "channel", "customer success", "nps", "churn",
    ],
    "Strategic Alliance": [
        # partners, universities, councils, grants, JV/MoU
        "partner", "partnership", "alliance", "strategic", "mou", "memorandum of understanding",
        "joint venture", "framework agreement", "collaboration", "consortium", "university", "college",
        "council", "ngo", "integrator", "oem", "supplier agreement", "grant agreement", "licensor",
        "licensee",
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

# sector-specific cues (extendable)
SECTOR_CUES = {
    "GreenTech": [
        "recycling", "recycled", "waste", "anaerobic", "biomass", "compost", "circular", "emissions", "co2e",
        "solar", "pv", "turbine", "kwh", "energy efficiency", "retrofit", "heat pump", "iso 14001", "esg", "sdg",
        "defra", "ofgem", "innovate uk", "feasibility study", "lca",
    ],
    # add more sectors here if needed
}

def _analyse_to_maps(text: str) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    """
    Returns (ic_map, ten_steps_map, summary_text)
    ic_map:  { leaf: {tick: bool, narrative: str} }
    ten_steps_map: { 'scores': List[int], 'narratives': List[str] }
    """
    t = (text or "").lower()
    sector = st.session_state.get("sector", "Other")

    # ---- Four-Leaf with SME cues + sector cues mixed in where relevant
    ic_map: Dict[str, Any] = {}
    for leaf, cues in FOUR_LEAF_KEYS.items():
        effective_cues = list(cues)
        if sector in SECTOR_CUES:
            # sector language contributes to Structural/Customer/Strategic detection
            if leaf in ("Structural", "Customer", "Strategic Alliance"):
                effective_cues += SECTOR_CUES[sector]
        hit = any(c in t for c in effective_cues)

        if leaf == "Human":
            nar = (
                "Human capital signals found (people, roles, training, qualifications)."
                if hit
                else "No strong people/skills cues detected in evidence."
            )
        elif leaf == "Structural":
            nar = (
                "Structural capital present (SOPs/processes/systems/registers/ISO/QMS)."
                if hit
                else "No explicit systems/processes/registers referenced."
            )
        elif leaf == "Customer":
            nar = (
                "Customer capital indicated (contracts/POs/CRM/pipeline/channels)."
                if hit
                else "Little/no explicit evidence of customer relationships."
            )
        else:
            nar = (
                "Strategic alliances present (partners/MoUs/JVs/universities/councils/grants)."
                if hit
                else "No clear references to strategic partners/alliances."
            )
        ic_map[leaf] = {"tick": hit, "narrative": nar}

    # ---- Ten-Steps scoring with SME-friendly boosters
    base = 3
    boosts = {
        "Identify": 2 if any(
            w in t for w in ["asset", "intangible", "know-how", "knowhow", "dataset", "algorithm"]
        ) else 0,
        "Separate": 2 if any(
            w in t for w in ["register", "inventory", "taxonomy", "asset list"]
        ) else 0,
        "Protect": 3 if any(
            w in t for w in [
                "nda", "non-disclosure", "confidentiality", "trade secret", "copyright",
                "trademark", "®", "™", "patent",
            ]
        ) else 0,
        "Safeguard": 2 if any(
            w in t for w in ["backup", "version control", "encryption", "access control", "retention"]
        ) else 0,
        "Manage": 2 if any(
            w in t for w in ["sop", "policy", "owner", "raci", "governance", "qms"]
        ) else 0,
        "Control": 2 if any(
            w in t for w in ["rights", "ownership", "assign", "exclusive", "non-exclusive"]
        ) else 0,
        "Use": 3 if any(
            w in t for w in [
                "licence", "license", "oem", "white label", "royalty", "subscription",
                "per seat", "saas", "pricing",
            ]
        ) else 0,
        "Monitor": 2 if any(
            w in t for w in ["kpi", "dashboard", "audit", "monthly report", "iso audit"]
        ) else 0,
        "Value": 3 if any(
            w in t for w in ["valuation", "pricing model", "ias 38", "frs 102", "amortisation", "fair value"]
        ) else 0,
        "Report": 2 if any(
            w in t for w in ["board pack", "management report", "investor update", "governance report"]
        ) else 0,
    }
    # sector influence (e.g., GreenTech evidence suggests more structure/use/report)
    if sector in SECTOR_CUES and any(c in t for c in SECTOR_CUES[sector]):
        boosts["Use"] = max(boosts.get("Use", 0), 1)
        boosts["Report"] = max(boosts.get("Report", 0), 1)

    scores: List[int] = []
    narratives: List[str] = []
    for step in TEN_STEPS:
        s = max(1, min(10, base + boosts.get(step, 0)))
        scores.append(s)
        narratives.append(f"{step}: readiness ≈ {s}/10 based on SME-language cues in evidence.")

    ten = {"scores": scores, "narratives": narratives}

    # ---- Summary written in plain business language
    ticks = [k for k, v in ic_map.items() if v["tick"]]
    gaps = [k for k, v in ic_map.items() if not v["tick"]]
    summary = (
        f"{st.session_state.get('case_name', 'Untitled Customer')} is a "
        f"{st.session_state.get('company_size', 'Micro (1–10)')} in {sector}.\n"
        f"Evidence suggests: {', '.join(ticks) if ticks else 'no obvious IC signals'}"
        f"{'; gaps: ' + ', '.join(gaps) if gaps else ''}.\n"
        "Ten-Steps scores are heuristic – experts should review and adjust."
    )
    return ic_map, ten, summary

# ========== Session defaults ==========
ss = st.session_state
ss.setdefault("case_name", "Untitled Customer")
ss.setdefault("company_size", "Micro (1–10)")
ss.setdefault("sector", "Other")

# expert context questions for richer narrative
ss.setdefault("q1_why_service", "")
ss.setdefault("q2_stage", "")
ss.setdefault("q3_plans", "")
ss.setdefault("q4_markets", "")
ss.setdefault("q5_valuation", "")

ss.setdefault("uploads", [])
ss.setdefault("combined_text", "")
ss.setdefault("ic_map", {})
ss.setdefault("ten_steps", {})
ss.setdefault("narrative", "")

SIZES = ["Micro (1–10)", "Small (11–50)", "Medium (51–250)", "Large (250+)"]
SECTORS = [
    "Food & Beverage", "MedTech", "GreenTech", "AgriTech", "Biotech",
    "Software/SaaS", "FinTech", "EdTech", "Manufacturing", "Creative/Digital",
    "Professional Services", "Mobility/Transport", "Energy", "Other",
]

# ========== Sidebar ==========
st.sidebar.markdown("### Navigate")
page = st.sidebar.radio(
    "",
    ("Customer", "Analyse Evidence", "Expert View", "Reports", "Licensing Templates"),
    index=0,
    key="nav",
)

# ========== PAGES ==========

# -- 1) Customer
if page == "Customer":
    st.header("Customer details")

    with st.form("customer_form"):
        c1, c2, c3 = st.columns([1.1, 1, 1])
        with c1:
            case_name = st.text_input("Customer / Company name", ss.get("case_name", ""))
        with c2:
            size = st.selectbox(
                "Company size",
                SIZES,
                index=SIZES.index(ss.get("company_size", SIZES[0])),
            )
        with c3:
            sector = st.selectbox(
                "Sector / Industry",
                SECTORS,
                index=SECTORS.index(ss.get("sector", "Other")),
            )

        st.markdown("---")
        st.subheader("Expert context (used to enrich the narrative)")

        q1 = st.text_area(
            "1. Why is the customer seeking this service?",
            value=ss.get("q1_why_service", ""),
            height=80,
        )
        q2 = st.text_area(
            "2. What stage are the customer's products and/or services at?",
            value=ss.get("q2_stage", ""),
            height=80,
        )
        q3 = st.text_area(
            "3. What is the customer's plan for the business in the short, medium and long term?",
            value=ss.get("q3_plans", ""),
            height=80,
        )
        q4 = st.text_area(
            "4. Which markets does the customer think their product or service fits into, and why?",
            value=ss.get("q4_markets", ""),
            height=80,
        )
        q5 = st.text_area(
            "5. If the customer were to sell the business tomorrow, what price would they want and why?",
            value=ss.get("q5_valuation", ""),
            height=80,
        )

        st.markdown("---")
        st.caption(
            "Uploads are held in session until you analyse. "
            "Nothing is written to server until you export."
        )
        uploads = st.file_uploader(
            "Upload evidence (PDF, DOCX, TXT, CSV, XLSX, PPTX, images)",
            type=["pdf", "docx", "txt", "csv", "xlsx", "pptx", "png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            key="uploader_main",
        )

        submitted = st.form_submit_button("Save details and context")
        if submitted:
            ss["case_name"] = case_name or "Untitled Customer"
            ss["company_size"] = size
            ss["sector"] = sector
            ss["q1_why_service"] = q1
            ss["q2_stage"] = q2
            ss["q3_plans"] = q3
            ss["q4_markets"] = q4
            ss["q5_valuation"] = q5
            if uploads:
                ss["uploads"] = uploads
            st.success("Saved customer details and expert context.")

    if ss.get("uploads"):
        st.info(
            f"{len(ss['uploads'])} file(s) stored in session. "
            "Go to **Analyse Evidence** next."
        )

# -- 2) Analyse Evidence
elif page == "Analyse Evidence":
    st.header("Analyse & build narrative (preview)")

    combined = ss.get("combined_text", "")
    st.text_area(
        "Preview extracted / combined evidence (first 5000 characters)",
        combined[:5000],
        height=220,
        key="combined_preview",
    )

    if st.button("Run analysis now"):
        # Combine text anew from uploads + context answers
        uploads = ss.get("uploads") or []
        combined_text = _read_text_from_uploads(uploads)

        context_bits: List[str] = []
        if ss.get("q1_why_service"):
            context_bits.append("Why service: " + ss["q1_why_service"])
        if ss.get("q2_stage"):
            context_bits.append("Stage: " + ss["q2_stage"])
        if ss.get("q3_plans"):
            context_bits.append("Plans: " + ss["q3_plans"])
        if ss.get("q4_markets"):
            context_bits.append("Markets: " + ss["q4_markets"])
        if ss.get("q5_valuation"):
            context_bits.append("Valuation: " + ss["q5_valuation"])

        if context_bits:
            combined_text = (combined_text + "\n\n" + "\n".join(context_bits)).strip()

        ss["combined_text"] = combined_text

        ic_map, ten_steps, summary = _analyse_to_maps(combined_text)
        ss["ic_map"] = ic_map
        ss["ten_steps"] = ten_steps
        ss["narrative"] = summary

        st.success("Analysis complete. Open **Expert View** to refine and export.")

# -- 3) Expert View
elif page == "Expert View":
    st.header("Narrative Summary")
    nar = st.text_area(
        "Summary (editable)",
        value=ss.get("narrative", ""),
        height=180,
        key="nar_edit",
    )
    ss["narrative"] = nar

    colA, colB = st.columns([1, 1])

    with colA:
        st.subheader("4-Leaf Map")
        ic_map = ss.get("ic_map", {})
        for leaf in ["Human", "Structural", "Customer", "Strategic Alliance"]:
            row = ic_map.get(leaf, {"tick": False, "narrative": f"No assessment yet for {leaf}."})
            tick = "✓" if row["tick"] else "•"
            st.markdown(f"- **{leaf}**: {tick}")
            st.caption(row["narrative"])

        st.subheader("Market & Innovation")
        t = (ss.get("combined_text", "").lower())
        st.markdown(
            f"- Sector Mentioned: "
            f"{'Yes' if ss.get('sector', 'Other').lower() in t else 'Likely'}"
        )
        st.markdown(
            f"- Innovation Signals: "
            f"{'Yes' if any(w in t for w in ['innov', 'novel', 'patent', 'prototype']) else 'Possible'}"
        )
        st.markdown(
            f"- Business Model Cues: "
            f"{'Yes' if any(w in t for w in ['saas', 'licen', 'royalt', 'subscription']) else 'Possible'}"
        )

    with colB:
        st.subheader("10-Steps Readiness")
        ten = ss.get(
            "ten_steps",
            {"scores": [5] * 10, "narratives": [f"{s}: tbd" for s in TEN_STEPS]},
        )
        st.dataframe(
            {"Step": TEN_STEPS, "Score (1-10)": ten["scores"]},
            hide_index=True,
            use_container_width=True,
        )
        with st.expander("Narrative per step"):
            for s, n in zip(TEN_STEPS, ten["narratives"]):
                st.markdown(f"**{s}** — {n}")

        st.subheader("IPR & ESG")
        st.markdown(
            "- IPR cues: NDA/License/Trademark/Copyright/"
            "Trade Secret/Patent (auto-detected if present)."
        )
        st.markdown(
            "- ESG → ValuCompass: CSV artefacts can be mapped to IC and "
            "valued under IAS 38 (later step)."
        )

# -- 4) Reports & Exports
elif page == "Reports":
    st.header("Reports & Exports")
    case_name = ss.get("case_name", "Untitled_Customer")
    case_folder = OUT_ROOT / _safe_filename(case_name)
    _ensure_dir(case_folder)

    # Compose IC report text
    def _compose_ic_text() -> Tuple[str, str]:
        title = f"IC Report — {case_name}"
        ic_map = ss.get("ic_map", {})
        ten = ss.get(
            "ten_steps",
            {"scores": [5] * 10, "narratives": [f"{s}: tbd" for s in TEN_STEPS]},
        )

        ctx_lines: List[str] = []
        if ss.get("q1_why_service"):
            ctx_lines.append("Why service: " + ss["q1_why_service"])
        if ss.get("q2_stage"):
            ctx_lines.append("Stage: " + ss["q2_stage"])
        if ss.get("q3_plans"):
            ctx_lines.append("Plans: " + ss["q3_plans"])
        if ss.get("q4_markets"):
            ctx_lines.append("Markets: " + ss["q4_markets"])
        if ss.get("q5_valuation"):
            ctx_lines.append("Valuation view: " + ss["q5_valuation"])

        body_parts: List[str] = []

        body_parts.append("Executive Summary\n")
        body_parts.append(ss.get("narrative", "(no summary)"))
        body_parts.append(
            "\n\nExpert Context\n"
            + ("\n".join(ctx_lines) if ctx_lines else "(none provided)")
        )

        body_parts.append("\n\nFour-Leaf Analysis")
        for leaf in ["Human", "Structural", "Customer", "Strategic Alliance"]:
            row = ic_map.get(leaf, {"tick": False, "narrative": ""})
            body_parts.append(
                f"- {leaf}: {'✓' if row.get('tick') else '•'} — {row.get('narrative', '')}"
            )

        body_parts.append("\nTen-Steps Readiness")
        for s, n in zip(TEN_STEPS, ten["narratives"]):
            body_parts.append(f"- {n}")

        body_parts.append(
            "\nAssumptions & Action Plan (to be agreed with customer)"
        )
        body_parts.append("• Draft assumptions placeholder.\n• Initial actions placeholder.\n")

        return title, "\n".join(body_parts)

    # Compose Licensing report text (TTO-oriented, DOCX-ready)
    def _compose_lic_text() -> Tuple[str, str]:
        """
        Build a Technology-Transfer oriented Licensing Report.

        Audience:
            - Technology Transfer Officers (TTOs)
            - University spin-offs and small companies preparing for licensing / co-development

        Uses:
            - Case name and sector from session state
            - High-level narrative only (no confidential formulas)
        """
        case_name_local = ss.get("case_name", "Untitled Customer")
        sector_local = ss.get("sector", "Other")
        title_local = f"Licensing Report — {case_name_local}"

        body_local = f"""LICENSING REPORT — {case_name_local}
Prepared for Technology Transfer & IP Management
Generated by IC-LicAI using structured evidence and expert inputs

────────────────────────────────────────────────────────
EXECUTIVE SUMMARY
────────────────────────────────────────────────────────

{case_name_local} is a {sector_local} organisation with strong innovation capability and a defined contracting portfolio.
The company holds a set of identifiable intangible assets, including patents or patent applications, trademarks,
copyrighted materials, trade secrets and operational know-how. This Licensing Report assesses {case_name_local}'s
readiness to enter licensing, co-development and revenue-sharing agreements with universities, research
organisations, corporates and public-sector partners.

The assessment follows a Technology Transfer Officer (TTO)–oriented structure and considers:

• IP ownership, clarity and protectability
• Background versus Foreground IP
• Contractual readiness for licensing
• FRAND requirements (Fair, Reasonable and Non-Discriminatory access)
• Governance, audit and compliance
• Suitability of licensing models for spin-off and SME collaboration
• Concrete, time-bound actions to reach licensing readiness

On the basis of the available evidence, {case_name_local} demonstrates strong potential for scalable licensing.
Key strengths include a clearly emerging IPR register, evidence of commercial demand through contracts and
customer relationships, and sector-aligned innovation. The main gaps relate to contract standardisation,
field-of-use and territory clauses, governance formalisation, and explicit FRAND alignment in agreements.

────────────────────────────────────────────────────────
SECTION A — IP POSITION & ASSET CLASSIFICATION
────────────────────────────────────────────────────────

A1. Background IP (owned or controlled by {case_name_local})

Background IP refers to all intellectual property that exists prior to, or independently from, any specific
collaboration or grant-funded project. From the evidence, the following classes of Background IP are relevant
for licensing and co-development:

• Patents and patent-pending applications covering core technology components
• Registered or pending trademarks (brand and product names)
• Copyrighted documentation and SOP libraries
• Escrowed source code and software modules
• Trade secrets (process parameters, algorithms, pricing logic, supplier blends)
• Documented know-how for deployment, integration and JV roll-out

This Background IP forms the primary base for value capture in any licence agreement. It must be described in a
concise IP Position Paper that can be shared under NDA with prospective partners.

A2. Foreground IP (arising from collaborations and projects)

Foreground IP refers to results created during specific collaborations, pilots, grants and joint projects.
Evidence suggests that Foreground IP may arise from:

• Joint development activities with strategic partners
• Publicly funded grants (e.g. EU / national programmes)
• Testing, validation and performance trials
• Co-created deployment and integration solutions

At present, Foreground IP is not fully mapped or separated from Background IP, which presents a risk for both
{case_name_local} and any Technology Transfer Office (TTO) considering a licence or co-development agreement.

A3. Encumbrances and funding obligations

Public funding programmes and certain consortia may introduce specific IP and access obligations, such as:

• Open science or open access requirements
• Preferred or mandatory licensing to certain partners
• FRAND or FRAND-like access conditions
• Restrictions on exclusivity or field-of-use
• Reporting, audit and dissemination duties

Before concluding any licence, {case_name_local} and the TTO must confirm which assets are free of encumbrances and
which are subject to additional obligations linked to grants or consortium agreements.

────────────────────────────────────────────────────────
SECTION B — FRAND READINESS REVIEW
────────────────────────────────────────────────────────

FRAND (Fair, Reasonable and Non-Discriminatory) is assessed across three pillars.

B1. Fairness

“Fair” typically requires:

• A transparent link between licence fees and the economic value of the technology
• A documented cost baseline and value narrative
• A corridor of typical royalty ranges or fee structures

From the evidence, {case_name_local} shows signs of value-based pricing (project revenues, licensing-like income),
but the royalty corridor and pricing policy for licences are not yet formalised.

B2. Reasonableness

“Reasonable” relates to:

• Costs of development, protection and maintenance
• Comparable market rates
• The scope and exclusivity of the licence

{case_name_local} appears to have a clear cost structure (COGS, R&D, Opex) that can support reasonable pricing,
but the link between specific cost pools and specific licensable assets has not yet been fully documented.

B3. Non-Discrimination

“Non-Discriminatory” requires that comparable licensees in comparable situations receive broadly comparable
terms and conditions, unless objectively justified differences are documented.

Current contracts show variation in IP and licence language, which may be acceptable at early stages but is not
yet aligned with a FRAND-style standard. A standardised set of IP, access and non-discrimination clauses is
strongly recommended.

Summary of FRAND readiness:

• Fair — Emerging (requires a formal royalty corridor and value justification)
• Reasonable — Moderate (cost data exists; needs clearer linkage to licensing scope)
• Non-Discriminatory — Weak/Developing (contracts not yet standardised on FRAND-style clauses)

────────────────────────────────────────────────────────
SECTION C — CONTRACT READINESS ASSESSMENT
────────────────────────────────────────────────────────

This section considers whether the current contract set is ready to support licensing, co-development and
spin-off collaboration.

C1. IP ownership clauses

• Some agreements contain IP ownership wording, but there is inconsistency in language and scope.
• In several cases, ownership of improvements and Foreground IP is not expressly defined.

C2. Licence clauses (grant of rights)

• A number of customer contracts describe “rights to use” the solution without clearly defining whether this
  is a licence, a service, or a one-off delivery.
• Supplier contracts rarely address IP ownership or licence rights, despite possible contributions to Foreground IP.

C3. Field of use

• Most contracts do not explicitly specify field-of-use, sector, or application boundaries.
• This makes it difficult to operate parallel licensing models by market, sector or geography.

C4. Territory and exclusivity

• Territorial scope is often implicit or assumed.
• Few contracts clearly state whether rights are global, regional or country-specific.
• Exclusivity is rarely defined; where it is, wording may be too broad for comfort from a TTO perspective.

C5. Improvements, derivative works and Foreground IP

• Mechanisms for handling improvements, derivative works and jointly developed Foreground IP are not yet
  fully documented.
• Without this clarity, both {case_name_local} and partner institutions face uncertainty in future exploitation.

C6. Background / Foreground mapping

• There is no standard mapping process or register that tags which assets are Background, which are Foreground,
  and which are joint or encumbered.
• This is a key pre-requisite for safe licensing, especially in the university and public research context.

────────────────────────────────────────────────────────
SECTION D — LICENSING MODELS FOR TTO & SME COLLABORATION
────────────────────────────────────────────────────────

Based on the current profile of {case_name_local}, the following licensing models are most appropriate.

1. Non-Exclusive Licence (recommended core model)

• Ownership of Background IP remains with {case_name_local}.
• Multiple licensees can access the technology under standard terms.
• Well aligned with FRAND and public-funding expectations.
• Suitable for software modules, SOP libraries, analytical tools and reference designs.

2. Field-of-Use Licence (spin-off or institutional model)

• {case_name_local} grants rights only for a specified field (e.g. clinical research, training, a particular industry).
• The TTO and spin-off operate within their field; {case_name_local} retains all other fields.
• Useful where the university specialises in a narrow application or geography.

3. Territory-Specific Licence

• Rights are limited to a defined region or country (e.g. one EU country, a cluster of states, or a single
  African market).
• Allows progressive roll-out of partners while managing channel conflict.

4. Co-Creation / Joint Development Licence

• Appropriate where university or partner contributions materially affect Foreground IP.
• Foreground IP ownership and revenue sharing must be clearly described.
• Background IP remains with the original owner; access is licensed for the project or field.

5. Royalty-Bearing Licence

• Licence fees may combine:
  – Up-front payments or milestones
  – Running royalties as a percentage of revenue
  – Minimum annual guarantees
• For public-funded context, royalty structures should be transparent and compatible with FRAND expectations.

────────────────────────────────────────────────────────
SECTION E — LICENSING ACTION PLAN (TTO-ORIENTED)
────────────────────────────────────────────────────────

The following action plan is designed for a Technology Transfer Officer working with {case_name_local} and a spin-off
or small company partner. It focuses on establishing IP clarity, FRAND alignment and repeatable licensing practice.

Priority actions (0–12 months):

1) Build IP Position Paper (Background vs Foreground)

• Objective: Produce a concise IP Position Paper summarising Background IP, Foreground IP and encumbrances.
• Owner: CEO / IC Lead in collaboration with TTO.
• Dependencies: IPR register, grant agreements, contract index.
• Timeline: 0–60 days.
• KPI: IP Position Paper approved by TTO and internal management.

2) Map Improvements and Foreground IP

• Objective: Identify all Foreground IP arising from grants, pilots and joint projects.
• Owner: IC Lead / R&D.
• Dependencies: Grants and collaboration contracts.
• Timeline: 0–30 days.
• KPI: Mapping table completed and attached to IA/IC register.

3) Draft FRAND-Standard Licence Templates

• Objective: Create standard, FRAND-aligned licence templates suitable for spin-offs and SME partners.
• Owner: Legal / Licensing Counsel, with input from TTO.
• Dependencies: Market benchmarks, IP policy of host institution.
• Timeline: 0–45 days.
• KPI: Templates approved and stored in the contract toolkit.

4) Standardise IP and Licence Clauses in Contracts

• Objective: Ensure new contracts use the same core IP, licence, field-of-use and territory clauses.
• Owner: Business Development / Legal.
• Dependencies: Contract index, template library.
• Timeline: 30–60 days.
• KPI: ≥ 80% of new contracts adopting the standard clauses.

5) Define Royalty Corridor and Commercial Policy

• Objective: Establish a corridor of acceptable royalty and fee structures based on cost, value and market norms.
• Owner: CFO / Commercial Lead.
• Dependencies: GL cost data, market studies, partner expectations.
• Timeline: 60–90 days.
• KPI: Royalty corridor documented, with examples for spin-offs, SMEs and institutional partners.

6) Develop Licensing & JV Playbook

• Objective: Provide a practical handbook describing how to negotiate, structure and manage licences and joint ventures.
• Owner: Business Development, Strategy and TTO.
• Dependencies: Licence templates, IA/IC register, IP Position Paper.
• Timeline: 30–120 days.
• KPI: Playbook used in at least 2–3 real negotiations.

7) Publish Field-of-Use and Territory Taxonomy

• Objective: Create a simple taxonomy that lists fields-of-use and territories that can be licensed separately.
• Owner: Strategy / Product Management.
• Dependencies: Market segmentation work, partner feedback.
• Timeline: 90–120 days.
• KPI: Taxonomy published and referenced in new licence templates.

────────────────────────────────────────────────────────
SECTION F — LICENSING READINESS SCORECARD
────────────────────────────────────────────────────────

This scorecard summarises the current position and target state from a TTO perspective.

IP Clarity: 7 / 10
• Background IP reasonably visible; Foreground mapping incomplete but achievable.

Contract Readiness: 6 / 10
• Contracts contain valuable commercial evidence but lack consistent licensing language.

FRAND Alignment: 8 / 10
• Transparency, cost tracking and partner diversity support FRAND; formal corridor and non-discrimination clauses
  are the next step.

Governance & Audit: 5 / 10
• Governance processes exist in practice but need clearer documentation, registers and playbooks.

Market Readiness: 7 / 10
• A credible customer and partner base exists; licensing models can be layered on top of current delivery.

With the action plan executed, {case_name_local} can move from an “emerging” to a “fully licence-ready” profile in under
12 months, making it significantly easier for Technology Transfer Officers, spin-offs and SME partners to adopt and
scale the technology with confidence.

"""
        return title_local, body_local

    # Buttons
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Generate IC Report (DOCX/TXT)", key="btn_ic"):
            title_ic, body_ic = _compose_ic_text()
            data_ic, fname_ic, mime_ic = _export_bytes_as_docx_or_txt(title_ic, body_ic)
            ic_path = _save_bytes_to_server(case_folder, fname_ic, data_ic)
            st.download_button(
                "⬇️ Download IC Report",
                data_ic,
                file_name=fname_ic,
                mime=mime_ic,
                key="dl_ic",
            )
            st.success(f"Saved to {ic_path}")

    with c2:
        if st.button("Generate Licensing Report (DOCX/TXT)", key="btn_lic"):
            title_lic, body_lic = _compose_lic_text()
            data_lic, fname_lic, mime_lic = _export_bytes_as_docx_or_txt(title_lic, body_lic)
            lic_path = _save_bytes_to_server(case_folder, fname_lic, data_lic)
            st.download_button(
                "⬇️ Download Licensing Report",
                data_lic,
                file_name=fname_lic,
                mime=mime_lic,
                key="dl_lic",
            )
            st.success(f"Saved to {lic_path}")

    st.caption(
        "Server save path is ./out/<Customer>. If saving is restricted, the download still works."
    )

# -- 5) Licensing Templates
elif page == "Licensing Templates":
    st.header("Licensing Templates (editable DOCX/TXT)")
    case = ss.get("case_name", "Untitled Customer")
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

        data, fname, mime = _export_bytes_as_docx_or_txt(title, body)
        folder = OUT_ROOT / _safe_filename(case)
        _ensure_dir(folder)
        path = _save_bytes_to_server(folder, fname, data)
        st.download_button(
            "⬇️ Download Template",
            data,
            file_name=fname,
            mime=mime,
            key="dl_tpl",
        )
        st.success(f"Saved to {path}")
