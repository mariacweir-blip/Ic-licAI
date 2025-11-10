# app_clean.py — IC-LicAI (stable, simplified sidebar build)
from __future__ import annotations
import io
import json
from pathlib import Path
from datetime import datetime
import streamlit as st

try:
    import pandas as pd  # optional for XLSX export
except Exception:
    pd = None

# -------------------- UI constants --------------------
SECTORS = [
    "Food & Beverage", "MedTech", "GreenTech", "AgriTech", "Biotech",
    "Software/SaaS", "FinTech", "EdTech", "Manufacturing", "Creative/Digital",
    "Professional Services", "Mobility/Transport", "Energy", "Other",
]
SIZES = ["Micro (1–10)", "Small (11–50)", "Medium (51–250)", "Large (250+)"]

# -------------------- Streamlit setup --------------------
st.set_page_config(page_title="IC-LicAI Expert Console", layout="centered")
ss = st.session_state

# Safe defaults
for k, v in {
    "case_name": "Untitled Case",
    "company_size": SIZES[0],
    "sector": SECTORS[0],
    "notes": "",
    "uploaded_names": [],
    "combined_text": "",
    "analysis": {},
    "leaf_human": "",
    "leaf_structural": "",
    "leaf_customer": "",
    "leaf_strategic": "",
    "intent_text": "",
    "frand_notes": "",
    "narrative": "",
}.items():
    ss.setdefault(k, v)

# -------------------- Helpers --------------------
def _read_txt_safely(file) -> str:
    try:
        if file.name.lower().endswith(".txt"):
            return file.getvalue().decode("utf-8", errors="ignore")
    except Exception:
        pass
    return ""

def combine_uploads(files) -> str:
    if not files:
        return ""
    return "\n\n".join(_read_txt_safely(f) for f in files if _read_txt_safely(f))

def make_txt_bytes(text: str) -> bytes:
    return text.encode("utf-8")

def make_json_bytes(data: dict) -> bytes:
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

def make_xlsx_bytes(ic_map: dict[str, list[str]]) -> bytes | None:
    if not pd:
        return None
    rows = []
    for leaf, items in (ic_map or {}).items():
        for i in items:
            rows.append({"Capital": leaf, "Item": i})
    df = pd.DataFrame(rows, columns=["Capital", "Item"]) if rows else pd.DataFrame(columns=["Capital", "Item"])
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="IA Register")
    return bio.getvalue()

# -------------------- Sidebar navigation --------------------
st.title("IC-LicAI Expert Console")
st.caption("Upload → Checklist → Analysis → Exports (licensing-first, human-in-the-loop)")

page = st.sidebar.radio(
    "Navigation",
    ["Case", "Checklist", "Analysis", "Exports"],
    index=0,
    key="nav_choice",
)

# ============================================================
# 1. Case Page
# ============================================================
if page == "Case":
    st.header("Case Details")
    with st.form("case_form"):
        c1, c2 = st.columns(2)
        with c1:
            case_name = st.text_input("Case / Company name", ss["case_name"])
            size = st.selectbox("Company size", SIZES, index=SIZES.index(ss["company_size"]))
        with c2:
            sector = st.selectbox("Sector / Industry", SECTORS, index=SECTORS.index(ss["sector"]))
            notes = st.text_area("Quick notes (optional)", ss["notes"], height=100)
        uploads = st.file_uploader(
            "Upload evidence (optional)",
            type=["pdf", "docx", "txt", "csv", "xlsx", "pptx", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="uploader",
        )
        submitted = st.form_submit_button("Save case")
        if submitted:
            ss["case_name"] = case_name or "Untitled Case"
            ss["company_size"] = size
            ss["sector"] = sector
            ss["notes"] = notes
            ss["uploaded_names"] = [f.name for f in uploads] if uploads else []
            st.success("Saved case details.")

    # --- CASE FORM ---
st.subheader("Case")

# Keep uploaded file references and a combined text buffer
uploaded_files = st.file_uploader(
    "Upload evidence (optional)",
    type=["pdf", "docx", "txt", "csv", "xlsx", "pptx", "png", "jpg", "jpeg"],
    accept_multiple_files=True,
    key="uploader",
)

# Show quick list of selected files
if uploaded_files:
    st.caption("Files selected:")
    st.write([f.name for f in uploaded_files])

with st.form("case_form"):
    case_name = st.text_input("Case / Company name", value=ss.get("case_name", "Untitled Case"))
    company_size = st.selectbox(
        "Company size",
        ["Micro (1–10)", "Small (11–50)", "Medium (51–250)", "Large (250+)"],
        index=["Micro (1–10)", "Small (11–50)", "Medium (51–250)", "Large (250+)"].index(ss.get("company_size", "Micro (1–10)"))
    )
    sector = st.selectbox(
        "Sector",
        ["Food & Beverage", "MedTech", "GreenTech", "AgriTech", "Biotech",
         "Software/SaaS", "FinTech", "EdTech", "Manufacturing", "Creative/Digital",
         "Professional Services", "Mobility/Transport", "Energy", "Other"],
        index=0 if ss.get("sector") is None else
        max(0, ["Food & Beverage", "MedTech", "GreenTech", "AgriTech", "Biotech",
                "Software/SaaS", "FinTech", "EdTech", "Manufacturing", "Creative/Digital",
                "Professional Services", "Mobility/Transport", "Energy", "Other"].index(ss.get("sector", "Food & Beverage")))
    )
    notes = st.text_area("Advisor notes (optional)", value=ss.get("notes", ""), height=140)

    submitted = st.form_submit_button("Save case")

# Handle form save
if submitted:
    ss["case_name"] = case_name
    ss["company_size"] = company_size
    ss["sector"] = sector
    ss["notes"] = notes

    # Build a “combined text” buffer from any text-like uploads + notes
    combined_chunks = [notes]
    # (If you already have a parsing function, you can swap it in later)
    for f in (uploaded_files or []):
        name = f.name.lower()
        if name.endswith(".txt"):
            combined_chunks.append(f.read().decode("utf-8", errors="ignore"))
        # For now we don’t auto-parse PDFs/DOCX/PPTX here; the demo just uses names
        else:
            combined_chunks.append(name)
    ss["combined_text"] = "\n".join([c for c in combined_chunks if c])

    st.success("✅ Case saved. You can now run Auto-Analysis.")

st.divider()

# --- AUTO ANALYSIS (simple heuristics demo) ---
st.subheader("Analysis")
if st.button("Run Auto-Analysis"):
    text = (ss.get("combined_text") or "").lower()

    def has_any(*words):
        return any(w in text for w in words)

    leaf_map = {
        "Human": "Mentions of team, skills, training or tacit know-how detected."
                 if has_any("team", "training", "skills", "employee") else
                 "No strong human-capital terms detected yet.",
        "Structural": "Internal systems
        
    st.info("➡️ Go to **Checklist** next.")

# ============================================================
# 2. Checklist Page
# ============================================================
elif page == "Checklist":
    st.header("Expert Checklist (guide only)")
    leaf = ss.get("analysis", {}).get("4_leaf", {})
    pre_h = ss.get("leaf_human") or leaf.get("Human", "")
    pre_s = ss.get("leaf_structural") or leaf.get("Structural", "")
    pre_c = ss.get("leaf_customer") or leaf.get("Customer", "")
    pre_a = ss.get("leaf_strategic") or leaf.get("Strategic Alliance", "")

    with st.expander("Four-Leaf Model"):
        ss["leaf_human"] = st.text_area("Human Capital", pre_h, height=110)
        ss["leaf_structural"] = st.text_area("Structural Capital", pre_s, height=110)
        ss["leaf_customer"] = st.text_area("Customer Capital", pre_c, height=110)
        ss["leaf_strategic"] = st.text_area("Strategic Alliance Capital", pre_a, height=110)

    with st.expander("Licensing Intent and FRAND"):
        ss["intent_text"] = st.text_area("Licensing intent (target markets, partners, scope)", ss["intent_text"], height=120)
        ss["frand_notes"] = st.text_area("FRAND notes (fee corridor, audit, essentiality, non-discrimination)", ss["frand_notes"], height=120)

    st.info("➡️ Next: go to **Analysis** to build the narrative preview.")

# ============================================================
# 3. Analysis Page
# ============================================================
elif page == "Analysis":
    st.header("Analysis & Narrative Preview")
    if st.button("Build Narrative Preview"):
        parts = [
            f"Case: {ss['case_name']}  |  Sector: {ss['sector']}  |  Size: {ss['company_size']}",
            "",
            "Four-Leaf Summary:",
            f"- Human: {ss['leaf_human']}",
            f"- Structural: {ss['leaf_structural']}",
            f"- Customer: {ss['leaf_customer']}",
            f"- Strategic Alliance: {ss['leaf_strategic']}",
            "",
            "Licensing Readiness:",
            f"- Intent: {ss['intent_text']}",
            f"- FRAND: {ss['frand_notes']}",
            "",
            f"Notes: {ss['notes']}",
        ]
        ss["narrative"] = "\n".join(parts)
        st.success("Narrative built.")
    st.text_area("Narrative (editable)", ss["narrative"], height=280)
    st.info("➡️ Proceed to **Exports** to download outputs.")

# ============================================================
# 4. Exports Page
# ============================================================
elif page == "Exports":
    st.header("Exports")
    name = ss["case_name"].replace(" ", "_")
    ic_map = {
        "Human": [ss["leaf_human"]] if ss["leaf_human"] else [],
        "Structural": [ss["leaf_structural"]] if ss["leaf_structural"] else [],
        "Customer": [ss["leaf_customer"]] if ss["leaf_customer"] else [],
        "Strategic Alliance": [ss["leaf_strategic"]] if ss["leaf_strategic"] else [],
    }

    # TXT
    txt_bytes = make_txt_bytes(ss["narrative"] or "No narrative built yet.")
    st.download_button(
        "⬇️ Download Narrative (TXT)",
        data=txt_bytes,
        file_name=f"{name}_Advisory.txt",
        mime="text/plain",
    )

    # JSON
    bundle = {
        "case": ss["case_name"],
        "sector": ss["sector"],
        "size": ss["company_size"],
        "notes": ss["notes"],
        "ic_map": ic_map,
        "licensing": {"intent": ss["intent_text"], "frand": ss["frand_notes"]},
        "uploaded_files": ss["uploaded_names"],
        "narrative": ss["narrative"],
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    json_bytes = make_json_bytes(bundle)
    st.download_button(
        "⬇️ Download Case (JSON)",
        data=json_bytes,
        file_name=f"{name}_Case.json",
        mime="application/json",
    )

    # XLSX (if pandas)
    xlsx_bytes = make_xlsx_bytes(ic_map)
    if xlsx_bytes:
        st.download_button(
            "⬇️ Download IA Register (XLSX)",
            data=xlsx_bytes,
            file_name=f"{name}_IA_Register.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info("Install pandas/xlsxwriter for XLSX export support.")
