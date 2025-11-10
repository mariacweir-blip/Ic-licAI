# app_clean.py — IC-LicAI Expert Console (UK English • navy buttons • yellow bg)
from __future__ import annotations

import io
import json
from pathlib import Path
from datetime import datetime

import streamlit as st

# Optional deps (DOCX + XLSX). We handle graceful fallbacks.
try:
    import pandas as pd  # type: ignore
except Exception:
    pd = None  # XLSX fallback to CSV (rare)
try:
    from docx import Document  # type: ignore
except Exception:
    Document = None  # DOCX fallback to TXT

# -------------------------------------------------
# Page config + Theme tweaks
# -------------------------------------------------
st.set_page_config(page_title="IC-LicAI Expert Console", layout="centered")

NAVY = "#0b1b3a"      # dark navy
YELLOW = "#FFF6CC"    # soft, readable yellow (not harsh)
ACCENT = "#D4AF37"    # gold accent

st.markdown(
    f"""
    <style>
      /* page background */
      .stApp {{ background: {YELLOW}; }}

      /* headings */
      h1, h2, h3, h4 {{ color: {NAVY}; }}

      /* big navy buttons (all st.button + st.download_button) */
      .stButton > button, .stDownloadButton > button {{
        background: {NAVY} !important;
        color: white !important;
        border: 0 !important;
        border-radius: 10px !important;
        padding: 0.9rem 1.2rem !important;
        width: 100% !important;
        font-weight: 700 !important;
      }}
      /* radio + labels */
      section[data-testid="stSidebar"] .stRadio label {{
        color: {NAVY};
        font-weight: 600;
      }}
      /* subtle cards */
      .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{
        background: #ffffff;
      }}
      /* breadcrumb */
      .crumb {{ color:{NAVY}; opacity:.9; font-size:.9rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# Session defaults (safe)
# -------------------------------------------------
ss = st.session_state
ss.setdefault("case_name", "Untitled Customer")
ss.setdefault("company_size", "Micro (1–10)")
ss.setdefault("sector", "")
ss.setdefault("notes", "")
ss.setdefault("uploaded_names", [])
ss.setdefault("combined_text", "")
ss.setdefault("analysis", {})      # {'4_leaf': {...}, 'ic_map': {...}, 'ten_steps': {...}}
ss.setdefault("narrative", "")     # human-written + auto scaffold
ss.setdefault("licensing", [])     # list of dicts: {'model':..., 'notes':[...]}
ss.setdefault("guide", {})         # flags/toggles if you need later

# -------------------------------------------------
# Reference lists
# -------------------------------------------------
SIZES = ["Micro (1–10)", "Small (11–50)", "Medium (51–250)", "Large (250+)"]
SECTORS = [
    "Food & Beverage", "MedTech", "GreenTech", "AgriTech", "Biotech",
    "Software/SaaS", "FinTech", "EdTech", "Manufacturing", "Creative/Digital",
    "Professional Services", "Mobility/Transport", "Energy", "Other",
]

# -------------------------------------------------
# Helpers (exports)
# -------------------------------------------------
def _bytes_docx_or_txt(title: str, body: str) -> tuple[bytes, str, str]:
    """
    Try to build DOCX (preferred). If python-docx is missing on the host,
    fall back to a clean TXT export.
    Returns: (bytes, filename, mimetype)
    """
    safe_name = title.strip().replace(" ", "_")
    if Document:
        doc = Document()
        doc.add_heading(title, level=1)
        for line in body.split("\n"):
            doc.add_paragraph(line)
        bio = io.BytesIO()
        doc.save(bio)
        return bio.getvalue(), f"{safe_name}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        data = body.encode("utf-8")
        return data, f"{safe_name}.txt", "text/plain"

def _export_xlsx_from_ic_map(ic_map: dict[str, list[str]]) -> tuple[bytes, str, str]:
    """
    Build a simple IA Register sheet from ic_map (4-leaf buckets).
    Falls back to CSV if pandas/xlsxwriter unavailable.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname_xlsx = f"IA_Register_{ts}.xlsx"
    fname_csv = f"IA_Register_{ts}.csv"

    rows = []
    for leaf, items in (ic_map or {}).items():
        for it in (items or []):
            rows.append({"Capital": leaf, "Item": it})

    if pd:
        df = pd.DataFrame(rows or [{"Capital": "", "Item": ""}])
        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="IA Register")
        return bio.getvalue(), fname_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    # CSV fallback
    body = "Capital,Item\n" + "\n".join([f"{r['Capital']},{r['Item']}" for r in rows])
    return body.encode("utf-8"), fname_csv, "text/csv"

def _make_ic_report_text(bundle: dict) -> tuple[str, str]:
    """
    Build a templated IC report body (Cover→Disclaimer→Index→Exec Summary→…).
    Returns (title, body).
    """
    name = bundle.get("case") or "Client"
    sector = bundle.get("sector") or "—"
    size = bundle.get("company_size") or "—"
    four = bundle.get("4_leaf", {})
    ten = bundle.get("ten_steps", {})
    narrative = bundle.get("narrative", "") or "This narrative will be refined by the expert."

    title = f"Intangible Capital Report — {name}"
    body = []
    body.append(f"= {title}")
    body.append("")
    body.append("© Areopa / ARICC. For review only. Not a valuation opinion.")
    body.append("")
    body.append("Index")
    body.append("1. Executive Summary")
    body.append("2. Intellectual Asset Inventory")
    body.append("3. Innovation Analysis")
    body.append("4. Market Scenario")
    body.append("5. Business Model")
    body.append("6. Assumptions")
    body.append("7. Valuation (to be provided by Areopa Valuation Team)")
    body.append("8. Conclusions")
    body.append("9. Action Plan")
    body.append("")
    body.append("Executive Summary")
    body.append(f"- Customer: {name}   |   Sector: {sector}   |   Size: {size}")
    body.append("- This document summarises findings from expert-driven analysis using the Areopa 4-Leaf Model and 10-Step method.")
    body.append("")
    body.append("Intellectual Asset Inventory (4-Leaf)")
    for leaf in ["Human", "Structural", "Customer", "Strategic Alliance"]:
        items = (four or {}).get(leaf, [])
        if not items:
            continue
        body.append(f"- {leaf} Capital:")
        for it in items:
            body.append(f"  • {it}")
    body.append("")
    body.append("Innovation Analysis (10-Steps – condensed)")
    for k, v in (ten or {}).items():
        body.append(f"- {k}: {v}")
    body.append("")
    body.append("Market Scenario")
    body.append(narrative)
    body.append("")
    body.append("Business Model")
    body.append("- Brief outline of current and target business model options.")
    body.append("")
    body.append("Assumptions")
    body.append("- Assumptions to be confirmed by expert and valuation team.")
    body.append("")
    body.append("Valuation")
    body.append("- **Reserved:** Produced by Areopa valuation (trade-secret models).")
    body.append("")
    body.append("Conclusions")
    body.append("- Summary of readiness, risks, and quick wins.")
    body.append("")
    body.append("Action Plan")
    body.append("- Next steps for asset development, governance and licensing.")
    return title, "\n".join(body)

def _make_lic_report_text(bundle: dict) -> tuple[str, str]:
    """
    Licensing-first advisory (coherent with FRAND language; no valuation).
    Returns (title, body).
    """
    name = bundle.get("case") or "Client"
    four = bundle.get("4_leaf", {})
    lic_opts = bundle.get("licensing", []) or []
    title = f"Licensing Readiness Report — {name}"

    body = []
    body.append(f"= {title}")
    body.append("")
    body.append("Scope")
    body.append("This report outlines licensing pathways aligned to the company’s intangible assets and FRAND principles.")
    body.append("")
    body.append("Core Intangibles (by 4-Leaf)")
    for leaf in ["Human", "Structural", "Customer", "Strategic Alliance"]:
        items = (four or {}).get(leaf, [])
        if items:
            body.append(f"- {leaf}:")
            for it in items:
                body.append(f"  • {it}")

    body.append("")
    body.append("Licensing Options")
    if not lic_opts:
        lic_opts = [
            {"model": "Revenue Licence", "notes": ["Royalty-based licence", "FRAND-aligned terms", "Annual audit clause"]},
            {"model": "Defensive Licence", "notes": ["Protective IP pooling", "Non-assertion within cluster partnership"]},
            {"model": "Co-Creation Licence", "notes": ["Shared ownership of Foreground IP", "Revenue-sharing clarity"]},
        ]
    for opt in lic_opts:
        body.append(f"- {opt.get('model')}:")
        for n in (opt.get("notes") or []):
            body.append(f"  • {n}")

    body.append("")
    body.append("Governance & Audit")
    body.append("Evidence sources should be tracked to an IA Register; decisions documented for audit and investor due-diligence.")
    return title, "\n".join(body)

# -------------------------------------------------
# Sidebar navigation (UK English)
# -------------------------------------------------
st.sidebar.caption("Navigate")
page = st.sidebar.radio(
    label="",
    options=["Customer", "Analyse Evidence", "Expert View", "Reports"],
    index=0,
)
st.sidebar.caption("EU theme • Areopa/ARICC demo")

# Breadcrumb
st.caption(
    f'<span class="crumb">Customer → Analyse Evidence → Expert View → Reports</span>',
    unsafe_allow_html=True,
)

st.title("IC-LicAI Expert Console")

# -------------------------------------------------
# 1) CUSTOMER
# -------------------------------------------------
if page == "Customer":
    st.header("Customer details")
    with st.form("customer_form"):
        c1, c2 = st.columns(2)
        with c1:
            case_name = st.text_input("Customer / Company name", ss.get("case_name", ""))
        with c2:
            size = st.selectbox("Company size", SIZES, index=SIZES.index(ss.get("company_size", "Micro (1–10)")))
        with c1:
            sector = st.selectbox("Sector / Industry", SECTORS, index=SECTORS.index(ss.get("sector", "Food & Beverage")) if ss.get("sector") in SECTORS else 0)
        with c2:
            notes = st.text_area("Quick notes (optional)", ss.get("notes", ""), height=110)

        uploads = st.file_uploader(
            "Upload evidence (optional)",
            type=["pdf", "docx", "txt", "csv", "xlsx", "pptx", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="uploader_main",
        )
        submitted = st.form_submit_button("Save details")
    if submitted:
        ss["case_name"] = case_name or "Untitled Customer"
        ss["company_size"] = size
        ss["sector"] = sector
        ss["notes"] = notes or ""
        ss["uploaded_names"] = [f.name for f in uploads] if uploads else []
        # quick combined text scaffold (demo-safe)
        chunks = [notes or ""]
        if uploads:
            for f in uploads:
                # Only auto-read TXT to avoid cloud parser surprises
                if f.name.lower().endswith(".txt"):
                    try:
                        chunks.append(f.read().decode("utf-8", errors="ignore"))
                    except Exception:
                        pass
                else:
                    chunks.append(f"[uploaded: {f.name}]")
        ss["combined_text"] = "\n".join([c for c in chunks if c])
        st.success("Saved. You can now go to **Analyse Evidence**.")

# -------------------------------------------------
# 2) ANALYSE EVIDENCE (simple, safe heuristics)
# -------------------------------------------------
elif page == "Analyse Evidence":
    st.header("Analyse & build narrative (preview)")

    combined = ss.get("combined_text", "")
    st.text_area("Preview extracted / combined evidence", combined[:5000], height=180)

    if st.button("Run quick auto-analysis"):
        text = (combined or "").lower()

        def has_any(words):
            return any(w in text for w in words)

        human = ["team", "training", "skill", "mentor", "employee"]
        structural = ["process", "system", "software", "method", "ip"]
        customer = ["client", "customer", "partner", "contract", "channel"]
        strategic = ["alliance", "mou", "joint", "cluster", "collaboration"]

        four_leaf = {
            "Human": [
                "Mentions of skills, roles or tacit know-how." if has_any(human) else "No strong human-capital indicators detected."
            ],
            "Structural": [
                "Internal systems, processes or methods referenced." if has_any(structural) else "No clear structural artefacts detected."
            ],
            "Customer": [
                "Evidence of customers, partners or channels." if has_any(customer) else "No customer-capital evidence detected."
            ],
            "Strategic Alliance": [
                "External collaborations or MOUs indicated." if has_any(strategic) else "No alliance-capital evidence detected."
            ],
        }

        ten_steps = {
            "1. Identify": "Draft list of core intangibles.",
            "2. Protect": "Check NDAs, filings, trade secret scope.",
            "3. Manage": "Assign ownership and governance.",
            "4. Value": "Valuation reserved for Areopa team.",
            "5. Separate": "Foreground vs Background assets.",
            "6. Safeguard": "Access controls, audit trails.",
            "7. Control": "Licensing boundaries & rights.",
            "8. Commercialise": "Pathways for revenue and use.",
            "9. Monitor": "KPIs and evidence updates.",
            "10. Improve": "Action plan for asset growth.",
        }

        ss["analysis"] = {
            "4_leaf": four_leaf,
            "ic_map": {k: v for k, v in four_leaf.items()},
            "ten_steps": ten_steps,
        }
        # simple narrative seed
        ss["narrative"] = (
            f"{ss.get('case_name','Client')} operates in {ss.get('sector','—')} with a {ss.get('company_size','—')} profile. "
            "Initial evidence suggests opportunities to formalise human know-how, reinforce process documentation, "
            "map customer agreements, and structure alliances under FRAND-aligned terms."
        )
        st.success("Auto-analysis completed. Continue in **Expert View**.")

# -------------------------------------------------
# 3) EXPERT VIEW (human-in-the-loop)
# -------------------------------------------------
elif page == "Expert View":
    st.header("Expert View (edit the analysis)")

    a = ss.get("analysis", {})
    four = a.get("4_leaf", {})
    ten = a.get("ten_steps", {})

    with st.expander("4-Leaf Model"):
        c1, c2 = st.columns(2)
        with c1:
            h_txt = st.text_area("Human Capital", "\n".join(four.get("Human", [])), height=110, key="ed_h")
            c_txt = st.text_area("Customer Capital", "\n".join(four.get("Customer", [])), height=110, key="ed_cus")
        with c2:
            s_txt = st.text_area("Structural Capital", "\n".join(four.get("Structural", [])), height=110, key="ed_s")
            a_txt = st.text_area("Strategic Alliance Capital", "\n".join(four.get("Strategic Alliance", [])), height=110, key="ed_sa")

    with st.expander("10-Step Method (summary)"):
        t_txt = st.text_area(
            "Steps (edit freely)",
            "\n".join([f"{k}: {v}" for k, v in (ten or {}).items()]) or "",
            height=150,
        )

    with st.expander("Licensing Intent & FRAND"):
        intent = st.text_area("Licensing intent (target markets, partners, scope)", ss.get("intent_text", ""), height=110)
        frand = st.text_area("FRAND notes (fee corridor, audit, essentiality, non-discrimination)", ss.get("frand_notes", ""), height=110)

    if st.button("Save expert edits"):
        # normalise back into structures
        four_leaf = {
            "Human": [ln.strip() for ln in h_txt.split("\n") if ln.strip()],
            "Structural": [ln.strip() for ln in s_txt.split("\n") if ln.strip()],
            "Customer": [ln.strip() for ln in c_txt.split("\n") if ln.strip()],
            "Strategic Alliance": [ln.strip() for ln in a_txt.split("\n") if ln.strip()],
        }
        ten_dict = {}
        for ln in (t_txt or "").split("\n"):
            if ":" in ln:
                k, v = ln.split(":", 1)
                ten_dict[k.strip()] = v.strip()
        ss["analysis"] = {
            "4_leaf": four_leaf,
            "ic_map": {k: v for k, v in four_leaf.items()},
            "ten_steps": ten_dict or ten,
        }
        ss["intent_text"] = intent
        ss["frand_notes"] = frand
        st.success("Edits saved. Generate documents in **Reports**.")

# -------------------------------------------------
# 4) REPORTS (downloads)
# -------------------------------------------------
elif page == "Reports":
    st.header("Generate & download")

    name = ss.get("case_name", "Client")
    bundle = {
        "case": name,
        "company_size": ss.get("company_size", ""),
        "sector": ss.get("sector", ""),
        "4_leaf": ss.get("analysis", {}).get("4_leaf", {}),
        "ic_map": ss.get("analysis", {}).get("ic_map", {}),
        "ten_steps": ss.get("analysis", {}).get("ten_steps", {}),
        "narrative": ss.get("narrative", ""),
        "licensing": ss.get("licensing", []),
    }

    st.subheader("Editable reports (DOCX with TXT fallback)")
    c1, c2 = st.columns(2)

    with c1:
        title, body = _make_ic_report_text(bundle)
        data, fname, mime = _bytes_docx_or_txt(title, body)
        st.download_button("📥 IC Report (editable)", data=data, file_name=fname, mime=mime, key="dl_ic")

    with c2:
        title, body = _make_lic_report_text(bundle)
        data, fname, mime = _bytes_docx_or_txt(title, body)
        st.download_button("📥 Licensing Report (editable)", data=data, file_name=fname, mime=mime, key="dl_lic")

    st.divider()
    st.subheader("Registers & data")
    c3, c4 = st.columns(2)

    with c3:
        xdata, xfname, xmime = _export_xlsx_from_ic_map(bundle.get("ic_map", {}))
        st.download_button("📥 IA Register (XLSX/CSV)", data=xdata, file_name=xfname, mime=xmime, key="dl_xlsx")

    with c4:
        jbytes = json.dumps(
            {
                "case": bundle.get("case"),
                "sector": bundle.get("sector"),
                "company_size": bundle.get("company_size"),
                "notes": ss.get("notes", ""),
                "assessment": ss.get("analysis", {}),
            },
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        st.download_button("📥 Case JSON", data=jbytes, file_name=f"{name.replace(' ','_')}_Case.json", mime="application/json", key="dl_json")

    st.caption("Note: valuation is prepared separately by the Areopa valuation team using trade-secret models.")
