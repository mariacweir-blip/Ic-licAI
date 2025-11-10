# app_clean.py — IC-LicAI Expert Console (clean full rewrite)
# UK English; licensing-first outputs as editable DOCX/TXT (no PDFs).
# Safe + simple: only tries to read .txt files for auto-analysis.
# Other file types are recorded by name so experts can review manually.

from __future__ import annotations

import io
from io import BytesIO
import streamlit as st

# ---------- Optional DOCX support ----------
try:
    from docx import Document  # python-docx (optional)
    DOCX_OK = True
except Exception:
    DOCX_OK = False

# ---------- Page & theme ----------
st.set_page_config(page_title="IC-LicAI Expert Console", layout="wide")

# Simple EU-ish theme: pale yellow page, navy headings, big buttons
st.markdown(
    """
    <style>
      .stApp { background: #FFF3BF; } /* pale yellow */
      h1, h2, h3 { color: #0B3D6E; }  /* navy */
      .btn-navy button {
          background-color:#0B3D6E !important;
          color:#ffffff !important;
          border:0 !important;
          border-radius:8px !important;
          padding:0.6rem 1rem !important;
          font-weight:600 !important;
          width:100%;
      }
      .block { background:#FFF7D6; padding:1rem 1rem 0.2rem 1rem; border-radius:10px; border:1px solid #E6DFAF; }
      .small { color:#555; font-size:0.9rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

ss = st.session_state

# ---------- Constants ----------
SECTORS = [
    "Food & Beverage", "MedTech", "GreenTech", "AgriTech", "Biotech",
    "Software/SaaS", "FinTech", "EdTech", "Manufacturing", "Creative/Digital",
    "Professional Services", "Mobility/Transport", "Energy", "Other",
]

SIZES = ["Micro (1–10)", "Small (11–50)", "Medium (51–250)", "Large (250+)"]

# ---------- Safe defaults ----------
ss.setdefault("case_name", "Untitled Customer")
ss.setdefault("sector", "Food & Beverage")
ss.setdefault("company_size", "Micro (1–10)")
ss.setdefault("notes", "")
ss.setdefault("uploaded_names", [])
ss.setdefault("combined_text", "")
ss.setdefault("analysis", {})   # will store ic_map, ten_steps, licensing, narrative

# ---------- Helpers ----------
def _export_bytes_as_docx_or_txt(title: str, body: str):
    """Return (data_bytes, filename, mime). Prefers DOCX if python-docx is available."""
    safe = (title or "Report").replace("/", "-").replace("\\", "-").strip()
    if DOCX_OK:
        doc = Document()
        if title:
            doc.add_heading(title, level=1)
        for para in (body or "").split("\n"):
            doc.add_paragraph(para)
        bio = BytesIO()
        doc.save(bio)
        return bio.getvalue(), f"{safe}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        txt = ((title + "\n\n") if title else "") + (body or "")
        return txt.encode("utf-8"), f"{safe}.txt", "text/plain"

def _compose_ic_report_text(bundle: dict[str, object]):
    """Return (title, body) for an IC report shell."""
    case = bundle.get("case") or "Untitled Customer"
    sector = bundle.get("sector", "")
    size = bundle.get("company_size", "")
    ic_map = bundle.get("ic_map", {}) or {}
    ten = bundle.get("ten_steps", {}) or {}

    lines = [
        "Executive Summary",
        f"- Customer: {case}",
        f"- Sector: {sector} | Size: {size}",
        "",
        "Intellectual Asset Inventory (Four-Leaf Model)",
        f"- Human: {ic_map.get('Human', '—')}",
        f"- Structural: {ic_map.get('Structural', '—')}",
        f"- Customer: {ic_map.get('Customer', '—')}",
        f"- Strategic Alliance: {ic_map.get('Strategic Alliance', '—')}",
        "",
        "10 Steps (Areopa) — highlights",
        f"{ten if ten else '—'}",
        "",
        "Innovation Analysis",
        "—",
        "",
        "Market Scenario",
        "—",
        "",
        "Business Model",
        "—",
        "",
        "Assumptions",
        "—",
        "",
        "Valuation (internal process — trade secret; to be added)",
        "—",
        "",
        "Conclusions",
        "—",
        "",
        "Action Plan",
        "—",
    ]
    return (f"{case} — Intangible Capital Report", "\n".join(lines))

def _compose_lic_report_text(bundle: dict[str, object]):
    """Return (title, body) for a Licensing-focused report."""
    case = bundle.get("case") or "Untitled Customer"
    sector = bundle.get("sector", "")
    size = bundle.get("company_size", "")
    ic_map = bundle.get("ic_map", {}) or {}
    lic = bundle.get("licensing", []) or []

    lines = [
        "Licensing Readiness Summary",
        f"- Customer: {case}",
        f"- Sector: {sector} | Size: {size}",
        "",
        "Core IC assets (Four-Leaf):",
        f"- Human: {ic_map.get('Human', '—')}",
        f"- Structural: {ic_map.get('Structural', '—')}",
        f"- Customer: {ic_map.get('Customer', '—')}",
        f"- Strategic Alliance: {ic_map.get('Strategic Alliance', '—')}",
        "",
        "FRAND/Compliance Notes",
        "- Fee corridor, audit, essentiality, non-discrimination (to be completed).",
        "",
        "Candidate Models",
    ]
    if lic:
        for i, opt in enumerate(lic, 1):
            model = str(opt.get("model", f"Option {i}")).strip()
            notes = opt.get("notes", [])
            note_text = ", ".join(notes) if notes else "—"
            lines.append(f"- {model}: {note_text}")
    else:
        lines += [
            "- Revenue Licence (royalty-based, FRAND-aligned).",
            "- Defensive Licence (IP pooling; non-assertion across cluster partners).",
            "- Co-Creation Licence (shared Foreground IP; revenue sharing).",
        ]
    lines += [
        "",
        "Next Steps",
        "- Confirm evidence register and NDAs.",
        "- Confirm IC mapping; tag tacit vs explicit.",
        "- Draft term sheet and select model(s) for negotiation.",
    ]
    return (f"{case} — Licensing Report", "\n".join(lines))

def _make_template_doc(template_name: str, case: str, sector: str):
    """Generate a licensing agreement template (DOCX if possible, else TXT)."""
    title = f"{case} — {template_name} Template"
    clauses = [
        f"Customer: {case}",
        f"Sector: {sector}",
        "",
        "1. Definitions",
        "2. Grant of Rights",
        "3. FRAND Terms (fee corridor, audit, essentiality, non-discrimination)",
        "4. Confidentiality / Trade Secrets",
        "5. Background vs Foreground IP",
        "6. Warranties & Indemnities",
        "7. Term & Termination",
        "8. Governing Law & Dispute Resolution (EU)",
    ]
    if "Co-creation" in template_name or "Co-creation" in template_name:
        clauses.insert(6, "5.1 Co-development Governance & Contribution Accounting")
    if "Knowledge" in template_name:
        clauses.insert(3, "3.1 Knowledge Artefact Description & Scope of Use (commercial/social)")

    if DOCX_OK:
        doc = Document()
        doc.add_heading(title, level=1)
        for c in clauses:
            doc.add_paragraph(c)
        bio = BytesIO()
        doc.save(bio)
        return bio.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        txt = title + "\n\n" + "\n".join(clauses)
        return txt.encode("utf-8"), "text/plain"

def _combine_text_from_uploads(files) -> str:
    """Read .txt uploads (utf-8) and stitch with notes; for other types, just list names."""
    chunks = []
    names = []
    for f in files or []:
        names.append(f.name)
        if f.name.lower().endswith(".txt"):
            try:
                chunks.append(f.read().decode("utf-8", errors="ignore"))
            except Exception:
                pass
    ss["uploaded_names"] = names
    return "\n\n".join([c for c in chunks if c])

def _auto_analyse(text: str) -> dict:
    """Tiny keyword-based demo to populate a Four-Leaf map + placeholders for 10 steps."""
    t = (text or "").lower()

    def has_any(words):  # simple keyword check
        return any(w in t for w in words)

    ic_map = {}
    ic_map["Human"] = (
        "Mentions of team, training or tacit know-how detected."
        if has_any(["team", "training", "skill", "mentor", "employee"])
        else "No strong human-capital terms detected yet."
    )
    ic_map["Structural"] = (
        "Internal systems, data, methods or processes referenced."
        if has_any(["process", "system", "software", "method", "ip"])
        else "No clear structural artefacts found."
    )
    ic_map["Customer"] = (
        "Evidence of customers, partners or user feedback present."
        if has_any(["client", "customer", "partner", "contract", "channel"])
        else "No customer-relationship evidence detected."
    )
    ic_map["Strategic Alliance"] = (
        "Collaborations, MOUs or supply-chain items found."
        if has_any(["alliance", "mou", "joint", "collaboration"])
        else "No alliance terms detected."
    )

    ten_steps = {
        "1 Identify": "List core intangibles; tag tacit/explicit.",
        "2 Protect": "NDAs, filings, trade secret coverage.",
        "3 Manage": "Registers, owners, controls.",
        "4 Value": "Areopa method (internal; add later).",
        "5–10": "Governance, exploitation, audit trail, monitoring.",
    }

    licensing = [
        {"model": "Revenue Licence", "notes": ["Royalty-based", "FRAND-aligned terms"]},
        {"model": "Defensive Licence", "notes": ["IP pooling", "Non-assertion in cluster"]},
        {"model": "Co-Creation Licence", "notes": ["Shared Foreground IP", "Revenue sharing"]},
    ]

    narrative = "Advisory preview generated from uploaded evidence (.txt) and expert notes."

    return {"ic_map": ic_map, "ten_steps": ten_steps, "licensing": licensing, "narrative": narrative}

# ---------- Sidebar navigation ----------
st.sidebar.caption("Navigate")
page = st.sidebar.radio("", ["Customer", "Analyse Evidence", "Expert View", "Reports"], index=0)
st.sidebar.caption("EU theme • Areopa/ARICC demo")

st.title("IC-LicAI Expert Console")

# ================================
# 1) Customer
# ================================
if page == "Customer":
    st.header("Customer details")

    with st.form("customer_form"):
        c1, c2 = st.columns(2)
        with c1:
            case_name = st.text_input("Customer / Company name", ss.get("case_name", ""))
            sector = st.selectbox("Sector / Industry", SECTORS, index=SECTORS.index(ss.get("sector", SECTORS[0])))
        with c2:
            company_size = st.selectbox("Company size", SIZES, index=SIZES.index(ss.get("company_size", SIZES[0])))
            notes = st.text_area("Quick notes (optional)", ss.get("notes", ""), height=100)

        uploads = st.file_uploader(
            "Upload evidence (optional)",
            type=["txt", "pdf", "docx", "csv", "xlsx", "pptx", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="uploader_main",
        )

        submitted = st.form_submit_button("Save details")
        if submitted:
            ss["case_name"] = case_name or "Untitled Customer"
            ss["sector"] = sector
            ss["company_size"] = company_size
            ss["notes"] = notes

            if uploads:
                combined = _combine_text_from_uploads(uploads)
                # Prepend notes to increase signal
                if notes:
                    combined = (notes.strip() + "\n\n" + combined).strip()
                ss["combined_text"] = combined
            st.success("Saved. You can now go to **Analyse Evidence**.")

    if ss.get("uploaded_names"):
        st.markdown("**Uploaded files (names only for non-TXT):** " + ", ".join(ss["uploaded_names"]))

# ================================
# 2) Analyse Evidence
# ================================
elif page == "Analyse Evidence":
    st.header("Analyse & build narrative (preview)")

    combined = ss.get("combined_text", "")
    st.text_area("Preview extracted / combined evidence (first 5000 chars)", combined[:5000], height=220)

    colA, colB = st.columns([1, 2])
    with colA:
        if st.button("Run quick auto-analysis", key="btn_auto"):
            ss["analysis"] = _auto_analyse(combined or ss.get("notes", ""))
            st.success("Analysis updated. See **Expert View** or **Reports**.")
    with colB:
        if ss.get("analysis"):
            st.markdown("**Advisory preview:**")
            st.write(ss["analysis"].get("narrative", ""))
        else:
            st.info("No analysis yet. Click **Run quick auto-analysis** to populate a draft.")

# ================================
# 3) Expert View (read-only JSON)
# ================================
elif page == "Expert View":
    st.header("Expert View")
    a = ss.get("analysis", {})
    if a:
        st.json(a)
    else:
        st.info("No analysis available yet. Go to ‘Analyse Evidence’ and run the analysis first.")

# ================================
# 4) Reports (IC report, Licensing report, Templates)
# ================================
elif page == "Reports":
    st.header("Reports")

    case_name = ss.get("case_name", "Untitled Customer")
    sector = ss.get("sector", "")
    company_size = ss.get("company_size", "")
    a = ss.get("analysis", {})

    c1, c2, c3 = st.columns(3)

    # Licensing Report
    with c1:
        st.subheader("Licensing Report")
        lic_bundle = {
            "case": case_name,
            "sector": sector,
            "company_size": company_size,
            "ic_map": a.get("ic_map", {}),
            "ten_steps": a.get("ten_steps", {}),
            "licensing": a.get("licensing", []),
            "narrative": a.get("narrative", ""),
        }
        title, body = _compose_lic_report_text(lic_bundle)
        data, fname, mime = _export_bytes_as_docx_or_txt(title, body)
        st.container().markdown('<div class="btn-navy">', unsafe_allow_html=True)
        st.download_button("⬇ Download Licensing Report", data, fname, mime, key="dl_licrep")
        st.markdown("</div>", unsafe_allow_html=True)

    # IC Report
    with c2:
        st.subheader("IC Report")
        ic_bundle = {
            "case": case_name,
            "sector": sector,
            "company_size": company_size,
            "ic_map": a.get("ic_map", {}),
            "ten_steps": a.get("ten_steps", {}),
            "narrative": a.get("narrative", ""),
        }
        title, body = _compose_ic_report_text(ic_bundle)
        data, fname, mime = _export_bytes_as_docx_or_txt(title, body)
        st.container().markdown('<div class="btn-navy">', unsafe_allow_html=True)
        st.download_button("⬇ Download IC Report", data, fname, mime, key="dl_icrep")
        st.markdown("</div>", unsafe_allow_html=True)

    # Licensing Templates
    with c3:
        st.subheader("Licensing Templates")
        template = st.selectbox(
            "Choose a template",
            ["FRAND Standard", "Co-creation (Joint Development)", "Knowledge (Non-traditional)"],
            key="tmpl_type",
        )
        if st.button("Generate Template", key="btn_tmpl"):
            doc_bytes, mime = _make_template_doc(template, case_name, sector)
            safe_t = template.replace(" ", "_").replace("(", "").replace(")", "").replace("-", "-")
            fname = f"{case_name}_{safe_t}.docx" if mime.startswith("application/") else f"{case_name}_{safe_t}.txt"
            st.container().markdown('<div class="btn-navy">', unsafe_allow_html=True)
            st.download_button("⬇ Download Template", data=doc_bytes, file_name=fname, mime=mime, key="dl_tmpl")
            st.markdown("</div>", unsafe_allow_html=True)
