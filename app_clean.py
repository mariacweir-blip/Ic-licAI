# app_clean.py — IC-LicAI Expert Console (Cloud-friendly, single file)
# Sidebar nav + Case form + Evidence upload + Heuristic analysis + Expert View + .docx/.txt exports

import io
import json
from pathlib import Path
from datetime import date

import streamlit as st

# --- DOCX helpers for licensing templates ---
from docx import Document
from docx.shared import Pt

def _docx_bytes(doc: Document) -> bytes:
    """Return a Document as bytes for Streamlit download_button."""
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

def _add_clause(doc: Document, title: str, body: str):
    doc.add_paragraph(f"{title}").runs[0].font.bold = True
    p = doc.add_paragraph(body)
    for r in p.runs:
        r.font.size = Pt(11)

def make_template_doc(template_name: str, case_name: str, sector: str) -> Document:
    """Build a short editable DOCX template for licensing."""
    name = case_name or "Client"
    sec = sector or "All Sectors"
    d = Document()
    d.add_heading(f"{template_name} Licence Agreement", level=1)
    d.add_paragraph(f"Parties: {name} (Licensor) and __________________ (Licensee)")
    d.add_paragraph(f"Sector / Field: {sec}")
    d.add_paragraph("Date: __________________")

    if template_name == "FRAND Standard":
        _add_clause(d, "1. Grant",
                    "Non-exclusive, non-transferable licence to use the Licensed Assets within the Field and Territory.")
        _add_clause(d, "2. FRAND Commercial Terms",
                    "Fees and/or royalties are Fair, Reasonable and Non-Discriminatory (FRAND); Most-Favoured-"
                    "Nation (MFN) protection across materially equivalent licensees.")
        _add_clause(d, "3. Scope & Restrictions",
                    "No sub-licensing without consent; no reverse engineering of trade secrets; no use outside Field.")
        _add_clause(d, "4. Reporting & Audit",
                    "Quarterly usage/royalty report; Licensor may audit with notice; rectification period applies.")
        _add_clause(d, "5. IP & Confidentiality",
                    "All IP remains with Licensor; Licensee keeps all non-public information confidential.")
        _add_clause(d, "6. Term & Termination",
                    "Initial term 12 months; renewals by mutual agreement; termination for breach after cure period.")
        _add_clause(d, "7. Compliance",
                    "Licensee complies with applicable law, ESG commitments (where agreed), and attribution rules.")
    elif template_name == "Co-creation (Joint Development)":
        _add_clause(d, "1. Purpose",
                    "Collaborative development of Improvements / New Works using Licensor know-how and Licensee input.")
        _add_clause(d, "2. Background vs Foreground IP",
                    "Background IP stays with each party; Foreground IP ownership either joint or allocated by module; "
                    "each party receives a licence to the other’s Foreground as needed to exploit results.")
        _add_clause(d, "3. FRAND Access",
                    "Commercial access to jointly created Foreground is FRAND-compliant for both parties.")
        _add_clause(d, "4. Revenue Share",
                    "Downstream revenue from Foreground allocated per an agreed split (e.g., 60/40).")
        _add_clause(d, "5. Governance",
                    "Joint steering group; sprint reviews; change control; publication/press policy.")
        _add_clause(d, "6. Confidentiality & Data",
                    "Mutual NDA; data governance; trade-secret handling and secure repositories.")
        _add_clause(d, "7. Exit",
                    "Orderly wind-down; buy-out and/or tail licence; survival of IP and confidentiality.")
    else:  # "Knowledge (Non-traditional)"
        _add_clause(d, "1. Licensed Asset",
                    "Codified knowledge artefacts (methods, playbooks, checklists, prompts, training packs).")
        _add_clause(d, "2. Rights",
                    "Use, adapt internally, and embed in Licensee processes; no public redistribution.")
        _add_clause(d, "3. Pricing Models",
                    "Option A: fixed annual fee per site; Option B: usage-based fee; Option C: social-benefit licence "
                    "with reduced fee and impact reporting.")
        _add_clause(d, "4. Evidence & Provenance",
                    "Licensee must retain evidence of use and attribution; Licensor can request exemplars.")
        _add_clause(d, "5. Termination",
                    "For breach/nonpayment or misuse; certified deletion of materials on termination.")
        _add_clause(d, "6. Ghana / JV / Grants (optional)",
                    "If applicable: trade-secreting process steps, Ghana contracts/JV for Waste & Water deployments, "
                    "and alignment with active SDG grant applications.")
    d.add_paragraph("\nSchedules: \nA) Licensed Assets    B) Field & Territory    C) Pricing    D) KPIs/Reports")
    return d

def _compose_full_ic_report_sections(bundle: dict) -> tuple[str, str]:
    """Return (title, body) for a full IC Report with templated sections."""
    case = (bundle.get("case") or "Untitled Case")
    sector = bundle.get("sector") or ""
    size = bundle.get("company_size") or ""
    notes = bundle.get("notes") or ""
    four_leaf = bundle.get("ic_map") or bundle.get("4_leaf") or {}
    ten_steps = bundle.get("ten_steps") or []
    narrative = bundle.get("narrative") or ""
    licensing = bundle.get("licensing") or []

    title = f"IC Report — {case}"

    # Build a clean, editable body (plain text -> will become DOCX via exporter)
    lines = []
    add = lines.append

    add(f"{case}")
    add(f"{sector} | {size}")
    add("")
    add("IC-LicAI — Intangible Capital Report")
    add("=" * 60)
    add("")

    # Cover Page
    add("# Cover page")
    add(f"Client: {case}")
    if sector: add(f"Sector: {sector}")
    if size: add(f"Company size: {size}")
    add("Date: [[Insert date]]")
    add("")
    add("Prepared by: Areopa / ARICC")
    add("")

    # Disclaimer
    add("# Disclaimer")
    add("This report is prepared for advisory purposes. It is not a legal, tax, or audit opinion. "
        "All figures and assumptions are subject to expert verification and client confirmation.")
    add("")

    # Index
    add("# Index")
    add("1. Executive summary")
    add("2. Intellectual asset inventory")
    add("3. Innovation analysis")
    add("4. Market scenario")
    add("5. Business model")
    add("6. Assumptions")
    add("7. Valuation (placeholder)")
    add("8. Conclusions")
    add("9. Action plan")
    add("")

    # Executive summary
    add("# 1. Executive summary")
    add("• Purpose: Provide a structured view of intangible assets and readiness for licensing/growth.")
    if notes:
        add(f"• Key notes: {notes}")
    if narrative:
        add(f"• Narrative highlights: {narrative}")
    add("• Headline recommendations: [[3–5 bullets]]")
    add("")

    # Intellectual asset inventory (4-Leaf)
    add("# 2. Intellectual asset inventory (4-Leaf Model)")
    def leaf_block(name, key):
        val = four_leaf.get(key) or four_leaf.get(name) or ""
        add(f"## {name} Capital")
        add(val if val else f"[[Describe {name} capital assets, evidence, and gaps]]")
        add("")
    leaf_block("Human", "Human")
    leaf_block("Structural", "Structural")
    leaf_block("Customer", "Customer")
    leaf_block("Strategic Alliance", "Strategic Alliance")

    # Innovation analysis
    add("# 3. Innovation analysis")
    add("[[Summarise product/service innovation, IP status, trade secrets, software, data, indices, "
        "and alignment with roadmap. Note NDAs, filings, confidentiality controls.]]")
    add("")

    # Market scenario
    add("# 4. Market scenario")
    add("[[TAM/SAM/SOM, target segments, EU/INT compliance considerations, competitor signals, "
        "partnership routes, channels.]]")
    add("")

    # Business model
    add("# 5. Business model")
    add("[[Current revenue model, target FRAND models, co-creation opportunities, non-traditional "
        "knowledge licensing.]]")
    if licensing:
        add("• Draft licensing options detected:")
        for opt in licensing:
            model = str(opt.get("model") or "").strip()
            notes_l = opt.get("notes") or []
            add(f"  – {model}" if model else "  – [[Model]]")
            for n in notes_l:
                add(f"     • {n}")
    add("")

    # Assumptions
    add("# 6. Assumptions")
    if ten_steps:
        add("• Derived from 10-Steps readiness review:")
        for i, step in enumerate(ten_steps, start=1):
            add(f"  Step {i}: {step}")
    add("• Additional assumptions: [[Insert market/ops/legal/tech assumptions]]")
    add("")

    # Valuation (placeholder)
    add("# 7. Valuation (placeholder)")
    add("This section is reserved for Areopa’s valuation team (trade-secret model).")
    add("[[Insert valuation summary once approved]]")
    add("")

    # Conclusions
    add("# 8. Conclusions")
    add("[[Key findings, priority risks, go/no-go checkpoints.]]")
    add("")

    # Action Plan
    add("# 9. Action plan (next 90 days)")
    add("• IC hygiene & governance: [[items]]")
    add("• Evidence register & NDAs: [[items]]")
    add("• Licensing track (FRAND/co-creation/knowledge): [[items]]")
    add("• Investor readiness: [[items]]")
    add("• KPIs & owners: [[items + owners + dates]]")
    add("")

    body = "\n".join(lines)
    return title, body

# ---------------------------
# Page & Session bootstrap
# ---------------------------
st.set_page_config(page_title="IC-LicAI Expert Console", layout="centered")
ss = st.session_state

def _ss_default(k, v):
    if k not in ss:
        ss[k] = v

# Safe defaults so the page never breaks if analysis isn’t run yet
_ss_default("case_name", "Untitled Case")
_ss_default("company_size", "Micro (1–10)")
_ss_default("sector", "")
_ss_default("notes", "")
_ss_default("analysis", {})   # holds results after Analyze
_ss_default("uploads_meta", [])  # list of uploaded file names

# ---------------------------
# UI constants
# ---------------------------
SIZES = [
    "Micro (1–10)",
    "Small (11–50)",
    "Medium (51–250)",
    "Large (250+)",
]

SECTORS = [
    "Food & Beverage", "MedTech", "GreenTech", "AgriTech", "Biotech",
    "Software/SaaS", "FinTech", "EdTech", "Manufacturing", "Creative/Digital",
    "Professional Services", "Mobility/Transport", "Energy", "Other",
]

# Sidebar navigation
PAGE = st.sidebar.radio(
    "Navigate",
    ["Case", "Analyze Evidence", "Expert View", "Reports"],
    key="nav"
)

st.sidebar.caption("EU theme • Areopa/ARICC demo")

# ---------------------------
# Helpers: light heuristics
# ---------------------------
def _summarise_text_blurb(notes: str) -> str:
    notes = (notes or "").strip()
    if not notes:
        return "Short advisory narrative will appear here after analysis."
    # super-light heuristic: first 2 sentences or 250 chars
    if "." in notes:
        parts = [p.strip() for p in notes.split(".") if p.strip()]
        return (". ".join(parts[:2]) + ".")[:250]
    return notes[:250]

def _heuristic_ic_map(case_name: str, size: str, sector: str, uploads: list) -> dict:
    # pretend-mapped artefacts count derived from uploads/notes presence
    base = 4 if uploads else 2
    bump = 2 if "Micro" in (size or "") else (3 if "Small" in (size or "") else 4)
    total = base + bump
    return {
        "summary": f"{case_name or 'Client'} currently mapped assets: {total} across the Four-Leaf Model.",
        "leaf": {
            "Human": "Methods, know-how, tacit routines (owner/founder heavy).",
            "Structural": "Basic docs/templates; internal systems emerging.",
            "Customer": "Few repeat clients; references/testimonials valuable.",
            "Strategic alliance": "Seed partnerships; scope for JV or co-creation."
        }
    }

def _heuristic_10_steps(size: str) -> dict:
    scope = "micro scale" if "Micro" in (size or "") else "lightweight"
    return {
        "summary": f"Apply the 10-Steps at a {scope}: identify → separate → protect → safeguard → manage → control → audit → improve → monetise → renew.",
        "readiness": "Pragmatic readiness: focus on converting tacit→explicit and establishing a simple evidence register."
    }

def _heuristic_licensing(size: str, sector: str) -> list:
    # three FRAND-aligned options as examples
    return [
        {
            "title": "Fixed-Fee Starter Licence",
            "model": "Flat fee per 6–12 months; uniform terms; audit right; termination for breach.",
            "suits": "Micro/Small clients needing quick adoption with low admin."
        },
        {
            "title": "Simple Royalty Licence",
            "model": "2–3% of net sales with annual cap; MFN across equivalent licensees.",
            "suits": "Where downstream usage drives revenue; transparent reporting."
        },
        {
            "title": "Evaluation → Commercial Path",
            "model": "60–90 day evaluation at nominal fee; pre-agreed conversion corridor.",
            "suits": f"New adopters in {sector or 'target market'}; reduces buyer risk."
        },
    ]

def _build_advisory_narrative(case, size, sector, notes, ic_map, ten_steps, licensing) -> str:
    blurb = _summarise_text_blurb(notes)
    lines = []
    lines.append(f"{case} is a {size} in {sector or 'General'}.\n")
    lines.append(blurb + "\n")
    lines.append("Four-Leaf snapshot:")
    for k, v in ic_map.get("leaf", {}).items():
        lines.append(f" - {k}: {v}")
    lines.append("")
    lines.append("10-Steps readiness:")
    lines.append(f" - {ten_steps.get('readiness')}")
    lines.append("")
    lines.append("Licensing options (FRAND-aligned examples):")
    for opt in licensing:
        lines.append(f" - {opt['title']}: {opt['model']} (suits: {opt['suits']})")
    lines.append("")
    lines.append("Next 90 days (indicative):")
    lines.append(" - Snapshot evidence & start an IA register;")
    lines.append(" - Convert key tacit know-how into short templates & checklists;")
    lines.append(" - Pilot one licence path with a friendly customer/partner.")
    return "\n".join(lines)

# Export builders: .docx if available, else .txt
def _export_bytes_as_docx_or_txt(title: str, body: str) -> tuple[bytes, str, str]:
    """Return (data_bytes, filename, mime) preferring .docx; fallback to .txt on ImportError."""
    try:
        from docx import Document
        from docx.shared import Pt
        doc = Document()
        if title:
            p = doc.add_paragraph()
            run = p.add_run(title)
            run.bold = True
            run.font.size = Pt(14)
        for para in (body or "").split("\n"):
            doc.add_paragraph(para)
        bio = io.BytesIO()
        doc.save(bio)
        return bio.getvalue(), "ICLicAI_Report.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    except Exception:
        data = (title + "\n\n" + (body or "")).encode("utf-8")
        return data, "ICLicAI_Report.txt", "text/plain"


def _compose_full_ic_report_sections(bundle: dict) -> tuple[str, str]:
    """Return (title, body) for a full IC Report with templated sections."""
    case = (bundle.get("case") or "Untitled Case")
    sector = bundle.get("sector") or ""
    size = bundle.get("company_size") or ""
    notes = bundle.get("notes") or ""
    four_leaf = bundle.get("ic_map") or bundle.get("4_leaf") or {}
    ten_steps = bundle.get("ten_steps") or []
    narrative = bundle.get("narrative") or ""
    licensing = bundle.get("licensing") or []

    title = f"IC Report — {case}"

    # Build a clean, editable body (plain text -> will become DOCX via exporter)
    lines = []
    add = lines.append

    add(f"{case}")
    add(f"{sector} | {size}")
    add("")
    add("IC-LicAI — Intangible Capital Report")
    add("=" * 60)
    add("")

    # Cover Page
    add("# Cover page")
    add(f"Client: {case}")
    if sector:
        add(f"Sector: {sector}")
    if size:
        add(f"Company size: {size}")
    add("Date: [[Insert date]]")
    add("")
    add("Prepared by: Areopa / ARICC")
    add("")

    # Disclaimer
    add("# Disclaimer")
    add("This report is prepared for advisory purposes. It is not a legal, tax, or audit opinion. "
        "All figures and assumptions are subject to expert verification and client confirmation.")
    add("")

    # Index
    add("# Index")
    add("1. Executive summary")
    add("2. Intellectual asset inventory")
    add("3. Innovation analysis")
    add("4. Market scenario")
    add("5. Business model")
    add("6. Assumptions")
    add("7. Valuation (placeholder)")
    add("8. Conclusions")
    add("9. Action plan")
    add("")

    # Executive summary
    add("# 1. Executive summary")
    add("• Purpose: Provide a structured view of intangible assets and readiness for licensing/growth.")
    if notes:
        add(f"• Key notes: {notes}")
    if narrative:
        add(f"• Narrative highlights: {narrative}")
    add("• Headline recommendations: [[3–5 bullets]]")
    add("")

    # Intellectual asset inventory (4-Leaf)
    add("# 2. Intellectual asset inventory (4-Leaf Model)")

    def leaf_block(name, key):
        val = four_leaf.get(key) or four_leaf.get(name) or ""
        add(f"## {name} Capital")
        add(val if val else f"[[Describe {name} capital assets, evidence, and gaps]]")
        add("")

    leaf_block("Human", "Human")
    leaf_block("Structural", "Structural")
    leaf_block("Customer", "Customer")
    leaf_block("Strategic Alliance", "Strategic Alliance")

    # Innovation analysis
    add("# 3. Innovation analysis")
    add("[[Summarise product/service innovation, IP status, trade secrets, software, data, indices, "
        "and alignment with roadmap. Note NDAs, filings, confidentiality controls.]]")
    add("")

    # Market scenario
    add("# 4. Market scenario")
    add("[[TAM/SAM/SOM, target segments, EU/INT compliance considerations, competitor signals, "
        "partnership routes, channels.]]")
    add("")

    # Business model
    add("# 5. Business model")
    add("[[Current revenue model, target FRAND models, co-creation opportunities, non-traditional "
        "knowledge licensing.]]")
    if licensing:
        add("• Draft licensing options detected:")
        for opt in licensing:
            model = str(opt.get("model") or "").strip()
            notes_l = opt.get("notes") or []
            add(f"  – {model}" if model else "  – [[Model]]")
            for n in notes_l:
                add(f"     • {n}")
    add("")

    # Assumptions
    add("# 6. Assumptions")
    if ten_steps:
        add("• Derived from 10-Steps readiness review:")
        for i, step in enumerate(ten_steps, start=1):
            add(f"  Step {i}: {step}")
    add("• Additional assumptions: [[Insert market/ops/legal/tech assumptions]]")
    add("")

    # Valuation (placeholder)
    add("# 7. Valuation (placeholder)")
    add("This section is reserved for Areopa’s valuation team (trade-secret model).")
    add("[[Insert valuation summary once approved]]")
    add("")

    # Conclusions
    add("# 8. Conclusions")
    add("[[Key findings, priority risks, go/no-go checkpoints.]]")
    add("")

    # Action Plan
    add("# 9. Action plan (next 90 days)")
    add("• IC hygiene & governance: [[items]]")
    add("• Evidence register & NDAs: [[items]]")
    add("• Licensing track (FRAND/co-creation/knowledge): [[items]]")
    add("• Investor readiness: [[items]]")
    add("• KPIs & owners: [[items + owners + dates]]")
    add("")

    body = "\n".join(lines)
    return title, body
