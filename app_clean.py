# app_clean.py — IC-LicAI Expert Console (clean, UK English)
# One-file build: sidebar pages, analysis, licensing report, IC report, templates, exports.

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import List, Dict, Any

import streamlit as st

# ---------- Look & feel (EU-ish – navy & soft yellow) ----------
st.set_page_config(page_title="IC-LicAI Expert Console", layout="wide")
st.markdown(
    """
    <style>
      :root { --navy:#0d315b; --yellow:#fff2bf; }
      .main { background: var(--yellow) !important; }
      h1,h2,h3,h4 { color: var(--navy) !important; }
      .stButton>button {
        background: var(--navy) !important; color: #fff !important;
        border-radius:8px; padding:10px 16px; font-weight:600;
      }
      .cta>button { width:100%; margin-top:6px; }
      .bigbtn>button { width:100%; padding:14px 18px; font-size:16px; }
      .metric { background:#fff; border:1px solid #e6e6e6; border-radius:8px; padding:8px 10px; }
      .box { background:#fff; border:1px solid #e6e6e6; border-radius:10px; padding:14px 14px; }
      .breadcrumb { color:#5b5b5b; font-size:13px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Session defaults ----------
ss = st.session_state
ss.setdefault("case_name", "Untitled Customer")
ss.setdefault("company_size", "Micro (1–10)")
ss.setdefault("sector", "Food & Beverage")
ss.setdefault("notes", "")
ss.setdefault("uploads", [])             # list of filenames for traceability
ss.setdefault("combined_text", "")       # combined text extracted (demo)
ss.setdefault("analysis", {})            # results dict
ss.setdefault("expert_view", {           # editable expert narrative fields
    "4_leaf": {"Human": "", "Structural": "", "Customer": "", "Strategic Alliance": ""},
    "licensing_intent": "", "frand_notes": ""
})

SECTORS = [
    "Food & Beverage", "MedTech", "GreenTech", "AgriTech", "Biotech",
    "Software/SaaS", "FinTech", "EdTech", "Manufacturing", "Creative/Digital",
    "Professional Services", "Mobility/Transport", "Energy", "Other",
]
SIZES = ["Micro (1–10)", "Small (11–50)", "Medium (51–250)", "Large (250+)"]

# ---------- Small helpers (no heavy deps) ----------
def _bytes_txt(text: str, filename: str) -> tuple[bytes, str, str]:
    data = text.encode("utf-8")
    return data, filename if filename.endswith(".txt") else f"{filename}.txt", "text/plain"

def _bytes_json(obj: Any, filename: str) -> tuple[bytes, str, str]:
    data = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
    return data, filename if filename.endswith(".json") else f"{filename}.json", "application/json"

def _bytes_csv(rows: List[Dict[str, str]], filename: str) -> tuple[bytes, str, str]:
    if not rows:
        rows = [{"Capital": "", "Item": ""}]
    headers = list(rows[0].keys())
    lines = [",".join(headers)]
    for r in rows:
        lines.append(",".join(str(r.get(h, "")).replace(",", " ") for h in headers))
    data = ("\n".join(lines)).encode("utf-8")
    return data, filename if filename.endswith(".csv") else f"{filename}.csv", "text/csv"

def _bytes_xlsx_or_csv(rows: List[Dict[str, str]], filename: str) -> tuple[bytes, str, str]:
    """Try XLSX via pandas/xlsxwriter; fallback to CSV if pandas not available."""
    try:
        import pandas as pd  # optional
        df = pd.DataFrame(rows)
        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="IA Register")
        return bio.getvalue(), filename if filename.endswith(".xlsx") else f"{filename}.xlsx", \
               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    except Exception:
        return _bytes_csv(rows, filename)

def _bytes_docx_or_txt(title: str, body: str, filename: str) -> tuple[bytes, str, str]:
    """Try python-docx; fallback to txt if not installed or on cloud."""
    try:
        from docx import Document  # type: ignore
        from docx.shared import Pt  # type: ignore
        doc = Document()
        doc.add_heading(title, level=1)
        for para in body.split("\n"):
            p = doc.add_paragraph(para)
            for run in p.runs:
                run.font.size = Pt(11)
        bio = io.BytesIO()
        doc.save(bio)
        return bio.getvalue(), filename if filename.endswith(".docx") else f"{filename}.docx", \
               "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    except Exception:
        return _bytes_txt(f"{title}\n\n{body}", filename)

def _has_any(text: str, words: List[str]) -> bool:
    t = (text or "").lower()
    return any(w in t for w in words)

def _auto_analyse(text: str) -> Dict[str, Any]:
    """Very light heuristic demo to prefill 4-Leaf, 10-Steps & hints."""
    human_w = ["team", "training", "skill", "mentor", "employee", "researcher"]
    structural_w = ["process", "system", "software", "method", "ip", "standard", "policy"]
    customer_w = ["client", "customer", "partner", "contract", "channel", "distribution"]
    strategic_w = ["alliance", "mou", "joint", "collaboration", "license", "cluster"]

    ic_map = {
        "Human": "Mentions of staff, skills, tacit know-how, or training detected."
                 if _has_any(text, human_w) else "No strong human capital terms detected yet.",
        "Structural": "Internal processes, methods, software, or governance referenced."
                      if _has_any(text, structural_w) else "No clear structural artefacts found.",
        "Customer": "Evidence of contracts, partners, routes-to-market, or feedback present."
                    if _has_any(text, customer_w) else "No visible customer capital yet.",
        "Strategic Alliance": "External collaborations, MOUs, clusters, or supply-chain items found."
                              if _has_any(text, strategic_w) else "No alliance evidence found.",
    }

    ten_steps = [
        "1 Identify assets", "2 Separate & define", "3 Protect (NDA/IP)", "4 Safeguard (policies)",
        "5 Manage & control", "6 Evidence & register", "7 Readiness & risk",
        "8 Initial valuation (IAS 38 lens)", "9 Monetise/licence (FRAND options)", "10 Review & improve"
    ]

    esg_market = {
        "esg_link": "Map ESG actions to IA artefacts (Value Compass CSV) then treat as IA.",
        "market_innovation": "Summarise market need, USP/innovation, standard compliance.",
        "business_model": "Indicate licensing revenue lines and service add-ons.",
    }

    licensing = {
        "options": [
            {"model": "Revenue Licence", "notes": ["Royalty-based, FRAND-aligned, audit clause"]},
            {"model": "Defensive Licence", "notes": ["Protective pooling, non-assert within cluster"]},
            {"model": "Co-creation Licence", "notes": ["Foreground shared IP, revenue sharing"]},
        ],
        "frand_core": ["Fee corridor", "Non-discrimination", "SEPs where relevant", "Essentiality note", "Audit"],
    }

    return {"ic_map": ic_map, "ten_steps": ten_steps, "esg_market": esg_market, "licensing": licensing}

# ---------- Sidebar ----------
st.sidebar.markdown("**Navigate**")
page = st.sidebar.radio(
    "", ["Customer", "Analyse Evidence", "Expert View", "Reports"],
    index=0, label_visibility="collapsed",
)

# ---------- Breadcrumb ----------
st.markdown(
    f"<div class='breadcrumb'>Customer → Analyse Evidence → Expert View → Reports</div>",
    unsafe_allow_html=True,
)

st.title("IC-LicAI Expert Console")

# =========================================================
# 1) CUSTOMER PAGE
# =========================================================
if page == "Customer":
    st.header("Customer details")
    with st.form("customer_form"):
        c1, c2 = st.columns(2)
        with c1:
            case_name = st.text_input("Customer / Company name", ss.get("case_name", ""))
            size = st.selectbox("Company size", SIZES, index=SIZES.index(ss.get("company_size", SIZES[0])))
        with c2:
            sector = st.selectbox("Sector / Industry", SECTORS, index=SECTORS.index(ss.get("sector", SECTORS[0])))
            notes = st.text_area("Quick notes (optional)", ss.get("notes", ""), height=100)

        uploads = st.file_uploader(
            "Upload evidence (optional)",
            type=["pdf", "docx", "txt", "csv", "xlsx", "pptx", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="uploader_main",
        )
        submitted = st.form_submit_button("Save details", use_container_width=False)
        if submitted:
            ss["case_name"] = case_name or "Untitled Customer"
            ss["company_size"] = size
            ss["sector"] = sector
            ss["notes"] = notes or ""
            ss["uploads"] = [f.name for f in uploads] if uploads else []
            # For the demo, only auto-read TXT files to avoid cloud parsing surprises
            chunks: List[str] = [notes] if notes else []
            if uploads:
                for f in uploads:
                    if f.name.lower().endswith(".txt"):
                        try:
                            chunks.append(f.read().decode("utf-8", errors="ignore"))
                        except Exception:
                            pass
                    else:
                        # Keep filename as trace evidence
                        pass
            ss["combined_text"] = "\n\n".join([c for c in chunks if c])
            st.success("Saved case details.")

    st.info("Next: go to **Analyse Evidence** to auto-build a first pass.")

# =========================================================
# 2) ANALYSE EVIDENCE PAGE (auto + preview)
# =========================================================
elif page == "Analyse Evidence":
    st.header("Analyse & build narrative (preview)")

    combined = ss.get("combined_text", "")
    st.text_area("Preview extracted / combined evidence (demo – first 5,000 chars)",
                 combined[:5000], height=220)

    if st.button("Run quick auto-analysis", key="btn_auto"):
        ss["analysis"] = _auto_analyse(combined)
        st.success("Analysis generated. Continue to **Expert View** to refine.")

    if ss.get("analysis"):
        a = ss["analysis"]
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("4-Leaf highlights (auto)")
            for k, v in a.get("ic_map", {}).items():
                st.markdown(f"**{k}** — {v}")
        with c2:
            st.subheader("10-Steps (Areopa) – checklist view (auto)")
            st.markdown("\n".join([f"- {s}" for s in a.get("ten_steps", [])]))

        st.subheader("ESG • Market • Innovation (auto hints)")
        st.write(a.get("esg_market", {}))

# =========================================================
# 3) EXPERT VIEW PAGE (editable + FRAND notes)
# =========================================================
elif page == "Expert View":
    st.header("Expert view")
    a = ss.get("analysis", {})
    ev = ss.get("expert_view", {})
    leaf = ev.get("4_leaf", {}).copy()

    # Pre-fill from auto if still empty
    leaf.setdefault("Human", a.get("ic_map", {}).get("Human", ""))
    leaf.setdefault("Structural", a.get("ic_map", {}).get("Structural", ""))
    leaf.setdefault("Customer", a.get("ic_map", {}).get("Customer", ""))
    leaf.setdefault("Strategic Alliance", a.get("ic_map", {}).get("Strategic Alliance", ""))

    c1, c2 = st.columns(2)
    with c1:
        leaf["Human"] = st.text_area("Human Capital", leaf["Human"], height=120)
        leaf["Customer"] = st.text_area("Customer Capital", leaf["Customer"], height=120)
    with c2:
        leaf["Structural"] = st.text_area("Structural Capital", leaf["Structural"], height=120)
        leaf["Strategic Alliance"] = st.text_area("Strategic Alliance Capital", leaf["Strategic Alliance"], height=120)

    st.markdown("---")
    st.subheader("Licensing intent & FRAND notes")
    lic_intent = st.text_area("Licensing intent (target markets, partners, scope)", ev.get("licensing_intent", ""), height=120)
    frand_notes = st.text_area("FRAND notes (fee corridor, audit, essentiality, non-discrimination)", ev.get("frand_notes", ""), height=120)

    if st.button("Save expert edits", key="btn_save_expert"):
        ss["expert_view"] = {"4_leaf": leaf, "licensing_intent": lic_intent, "frand_notes": frand_notes}
        st.success("Expert edits saved. Proceed to **Reports** to generate outputs.")

# =========================================================
# 4) REPORTS PAGE (Licensing Report • IC Report • IA Register/JSON • Templates)
# =========================================================
elif page == "Reports":
    st.header("Reports & templates")

    case = ss.get("case_name", "Untitled Customer")
    sector = ss.get("sector", "")
    size = ss.get("company_size", "")
    a = ss.get("analysis", {})
    ev = ss.get("expert_view", {})
    uploads = ss.get("uploads", [])

    # ----- Big buttons row -----
    b1, b2, b3 = st.columns([1, 1, 1.2])
    with b1:
        st.markdown("**Licensing Report**")
        if st.button("Generate Licensing Report (DOCX/TXT)", key="btn_lic", type="primary"):
            title = f"Licensing Report – {case}"
            lic = a.get("licensing", {})
            body_lines = [
                f"Customer: {case}",
                f"Sector: {sector} | Size: {size}",
                "",
                "1) Licensing options (auto suggestions)",
            ]
            for opt in lic.get("options", []):
                body_lines.append(f"  • {opt.get('model')}: " + "; ".join(opt.get("notes", [])))
            body_lines += [
                "",
                "2) FRAND baseline (auto hints)",
                "  • " + "; ".join(lic.get("frand_core", [])),
                "",
                "3) Expert intent (editable fields)",
                f"  • Intent: {ev.get('licensing_intent','') or '—'}",
                f"  • FRAND notes: {ev.get('frand_notes','') or '—'}",
                "",
                "Traceability (filenames only):",
                "  • " + (", ".join(uploads) or "No files uploaded"),
            ]
            body = "\n".join(body_lines)
            data, fname, mime = _bytes_docx_or_txt(title, body, f"{case}_Licensing_Report")
            st.download_button("⬇ Download Licensing Report", data, file_name=fname, mime=mime, key="dl_lic")

    with b2:
        st.markdown("**IC Report**")
        if st.button("Generate IC Report (DOCX/TXT)", key="btn_ic", type="primary"):
            title = f"IC Report – {case}"
            four = ev.get("4_leaf", {})
            steps = a.get("ten_steps", [])
            esg = a.get("esg_market", {})
            body = "\n".join([
                f"Customer: {case}",
                f"Sector: {sector} | Size: {size}",
                "",
                "Executive summary (draft):",
                f"- Human: {four.get('Human','—')}",
                f"- Structural: {four.get('Structural','—')}",
                f"- Customer: {four.get('Customer','—')}",
                f"- Strategic Alliance: {four.get('Strategic Alliance','—')}",
                "",
                "Innovation & Market (hints):",
                f"- ESG link: {esg.get('esg_link','—')}",
                f"- Market/Innovation: {esg.get('market_innovation','—')}",
                f"- Business model: {esg.get('business_model','—')}",
                "",
                "10-Steps checklist:",
                *[f"  • {s}" for s in steps],
                "",
                "Traceability (filenames only):",
                "  • " + (", ".join(uploads) or "No files uploaded"),
            ])
            data, fname, mime = _bytes_docx_or_txt(title, body, f"{case}_IC_Report")
            st.download_button("⬇ Download IC Report", data, file_name=fname, mime=mime, key="dl_ic")

    with b3:
        st.markdown("**Data Exports**")
        # IA Register (very simple rows built from 4-Leaf)
        four = ev.get("4_leaf", {})
        rows = [
            {"Capital": "Human", "Item": four.get("Human", "")},
            {"Capital": "Structural", "Item": four.get("Structural", "")},
            {"Capital": "Customer", "Item": four.get("Customer", "")},
            {"Capital": "Strategic Alliance", "Item": four.get("Strategic Alliance", "")},
        ]
        xbytes, xname, xmime = _bytes_xlsx_or_csv(rows, f"{case}_IA_Register.xlsx")
        st.download_button("⬇ Download IA Register (XLSX/CSV)", xbytes, file_name=xname, mime=xmime, key="dl_ia")

        bundle = {
            "case": case, "sector": sector, "company_size": size,
            "uploads": uploads,
            "analysis": a, "expert_view": ev,
        }
        jbytes, jname, jmime = _bytes_json(bundle, f"{case}_ICLicAI_Case.json")
        st.download_button("⬇ Download Case JSON", jbytes, file_name=jname, mime=jmime, key="dl_json")

    st.markdown("---")
    st.subheader("Licensing templates (editable DOCX/TXT)")
    c1, c2, c3 = st.columns(3)
    def _emit_template(name: str, bullets: List[str], fname_stub: str):
        body = f"{name}\n\n" + "\n".join([f"- {b}" for b in bullets])
        data, fname, mime = _bytes_docx_or_txt(name, body, f"{case}_{fname_stub}")
        st.download_button(f"⬇ {name}", data, file_name=fname, mime=mime, key=f"tmpl_{fname_stub}", help="Download editable template")

    with c1:
        _emit_template(
            "FRAND Standard Licence",
            [
                "Purpose & scope (fields to complete)",
                "Fee corridor & non-discrimination",
                "Audit & reporting cadence",
                "Term, territory, termination",
                "Essentiality statement (where relevant)",
            ],
            "FRAND_Standard_Licence",
        )
    with c2:
        _emit_template(
            "Co-creation (Joint Development) Licence",
            [
                "Background IP, Foreground IP, Sideground IP",
                "Contribution ledger & cost share",
                "Revenue share model & milestone triggers",
                "Publication & confidentiality",
            ],
            "CoCreation_Licence",
        )
    with c3:
        _emit_template(
            "Knowledge (Non-traditional) Licence",
            [
                "Codified knowledge (copyright/GTI/trade secret) description",
                "Permitted use & attribution",
                "Social benefit or commercial channel",
                "Revocation & ethics clause",
            ],
            "Knowledge_NonTraditional_Licence",
        )
