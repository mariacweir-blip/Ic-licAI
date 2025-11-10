# app_clean.py — IC-LicAI Expert Console (Cloud-friendly, single file)
# Sidebar nav + Case form + Evidence upload + Heuristic analysis + Expert View + .docx/.txt exports

import io
import json
from pathlib import Path
from datetime import date

import streamlit as st

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

def _compose_ic_report_text(bundle: dict) -> tuple[str, str]:
    title = f"Intangible Capital Report — {bundle.get('case')}"
    ic = bundle.get("ic_map", {})
    ts = bundle.get("ten_steps", {})
    sec = bundle.get("sector", "") or "General"

    body = []
    body.append(f"Company: {bundle.get('case')}")
    body.append(f"Size: {bundle.get('size')}")
    body.append(f"Sector: {sec}")
    body.append("")
    body.append("Four-Leaf Model:")
    for k, v in (ic.get("leaf") or {}).items():
        body.append(f" - {k}: {v}")
    body.append("")
    body.append("10-Steps:")
    body.append(f" - {ts.get('summary', '').strip() or 'Readiness view available in Expert View.'}")
    body.append(f" - Readiness: {ts.get('readiness', '')}")
    body.append("")
    body.append("Notes:")
    body.append(bundle.get("notes") or "(none)")
    return title, "\n".join(body)

def _compose_lic_report_text(bundle: dict) -> tuple[str, str]:
    title = f"Licensing Report — {bundle.get('case')}"
    lic = bundle.get("licensing") or []
    body = []
    body.append(f"Company: {bundle.get('case')}")
    body.append(f"Size: {bundle.get('size')}")
    body.append(f"Sector: {bundle.get('sector') or 'General'}")
    body.append("")
    body.append("Recommended FRAND-aligned options:")
    for opt in lic:
        body.append(f" - {opt['title']}: {opt['model']} (suits: {opt['suits']})")
    body.append("")
    body.append("Action pointers (90-day focus):")
    body.append(" - Productise one know-how package; publish clear rate card;")
    body.append(" - Pilot with 1–2 partners; capture outcomes;")
    body.append(" - Prepare co-creation addendum where collaboration is strategic.")
    return title, "\n".join(body)

# ---------------------------
# PAGES
# ---------------------------

if PAGE == "Case":
    st.title("Case")
    with st.form("case_form"):
        case_name = st.text_input("Case / Company name", value=ss.get("case_name", "Untitled Case"))
        company_size = st.selectbox("Company size", SIZES, index=SIZES.index(ss.get("company_size", SIZES[0])))
        sector = st.selectbox("Sector", SECTORS, index=SECTORS.index(ss.get("sector", SECTORS[-1])) if ss.get("sector") in SECTORS else len(SECTORS) - 1)
        notes = st.text_area("Advisor notes (paste interview snippets, bullets, etc.)", value=ss.get("notes", ""), height=180)
        uploaded_files = st.file_uploader(
            "Upload evidence (optional)",
            type=["pdf", "docx", "txt", "csv", "xlsx", "pptx", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="uploader_case",
        )
        submitted = st.form_submit_button("Save case")
    if submitted:
        ss["case_name"] = case_name
        ss["company_size"] = company_size
        ss["sector"] = sector
        ss["notes"] = notes
        ss["uploads_meta"] = [f.name for f in uploaded_files] if uploaded_files else []
        st.success("✅ Case details saved.")

    st.caption("Tip: Save, then switch to **Analyze Evidence**.")

elif PAGE == "Analyze Evidence":
    st.title("Analyze Evidence")
    st.write("This demo uses heuristics so you always see results on Cloud (no extra libs).")

    if st.button("▶ Run analysis"):
        ic_map = _heuristic_ic_map(ss.get("case_name"), ss.get("company_size"), ss.get("sector"), ss.get("uploads_meta"))
        ten_steps = _heuristic_10_steps(ss.get("company_size"))
        licensing = _heuristic_licensing(ss.get("company_size"), ss.get("sector"))
        narrative = _build_advisory_narrative(
            ss.get("case_name"),
            ss.get("company_size"),
            ss.get("sector"),
            ss.get("notes"),
            ic_map,
            ten_steps,
            licensing
        )
        ss["analysis"] = {
            "ic_map": ic_map,
            "ten_steps": ten_steps,
            "licensing": licensing,
            "narrative": narrative,
        }
        st.success("✅ Analysis complete. See **Expert View** and **Reports**.")
    else:
        st.info("Click **Run analysis** to generate the Expert View / Reports content.")

elif PAGE == "Expert View":
    st.title("Expert View")
    if not ss.get("analysis"):
        st.warning("Run **Analyze Evidence** first.")
    else:
        a = ss["analysis"]
        st.subheader("Advisory narrative (copyable)")
        st.text_area("Preview", a.get("narrative", ""), height=220, key="narrative_preview", label_visibility="collapsed")

        st.divider()
        st.subheader("Four-Leaf Model")
        leaf = a.get("ic_map", {}).get("leaf", {})
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Human**: {leaf.get('Human','')}")
            st.markdown(f"**Customer**: {leaf.get('Customer','')}")
        with c2:
            st.markdown(f"**Structural**: {leaf.get('Structural','')}")
            st.markdown(f"**Strategic alliance**: {leaf.get('Strategic alliance','')}")

        st.divider()
        st.subheader("10-Steps (readiness)")
        st.write(a.get("ten_steps", {}).get("summary", ""))
        st.info(a.get("ten_steps", {}).get("readiness", ""))

elif PAGE == "Reports":
    st.title("Reports")
    if not ss.get("analysis"):
        st.warning("Run **Analyze Evidence** first.")
    else:
        a = ss["analysis"]
        bundle = {
            "case": ss.get("case_name"),
            "size": ss.get("company_size"),
            "sector": ss.get("sector"),
            "notes": ss.get("notes"),
            "ic_map": a.get("ic_map", {}),
            "ten_steps": a.get("ten_steps", {}),
            "licensing": a.get("licensing", []),
            "narrative": a.get("narrative", ""),
        }

        st.subheader("Download editable reports")
        c1, c2 = st.columns(2)

        with c1:
            title, body = _compose_ic_report_text(bundle)
            data, fname, mime = _export_bytes_as_docx_or_txt(title, body)
            st.download_button("⬇ IC Report (.docx/.txt)", data=data, file_name=fname, mime=mime, key="dl_ic")

        with c2:
            title, body = _compose_lic_report_text(bundle)
            data, fname, mime = _export_bytes_as_docx_or_txt(title, body)
            st.download_button("⬇ Licensing Report (.docx/.txt)", data=data, file_name=fname, mime=mime, key="dl_lic")

        st.caption("Note: If `python-docx` isn’t available on Cloud, download defaults to .txt. We can enable .docx by adding it to requirements.txt later.")
