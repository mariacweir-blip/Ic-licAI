import streamlit as st
import importlib, os, sys
from pathlib import Path

# Robust imports: try normal package import, else load modules by file path
try:
    from ic_licai.processing import parse_uploaded_files, draft_ic_assessment
    from ic_licai.exporters import export_pdf, export_xlsx, export_json
except Exception:
    import importlib.util
    from pathlib import Path

    here = Path(__file__).resolve().parent
    pkg = here / "ic_licai"

    def _load_module(name: str, file_path: Path):
        spec = importlib.util.spec_from_file_location(name, str(file_path))
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader, f"Cannot load {file_path}"
        spec.loader.exec_module(mod)
        return mod

    processing = _load_module("ic_processing", pkg / "processing.py")
    exporters = _load_module("ic_exporters", pkg / "exporters_clean.py")

# expose the functions we need
parse_uploaded_files = processing.parse_uploaded_files
draft_ic_assessment = processing.draft_ic_assessment
export_pdf = exporters.export_pdf
export_xlsx = exporters.export_xlsx
export_json = exporters.export_json

# ---------- PAGE ----------
st.set_page_config(page_title="IC-LicAI – Advisory Console", layout="centered")

# Session defaults (safe)
ss = st.session_state
ss.setdefault("case_name", "Sandy Beach")
ss.setdefault("notes", "")
ss.setdefault("analysis", {})        # parsed files + assessment
ss.setdefault("guide", {})           # expert selections
ss.setdefault("narrative", "")       # advisory text

st.title("IC-LicAI — Advisory Console")

# Temporary tabs placeholder (we'll fill these next)
tabs = st.tabs(["Upload", "Expert Guide", "Advisory", "Exports"])
# ---------------- TAB 1: UPLOAD ----------------
with tabs[0]:
    st.subheader("Upload source materials")

    case_name = st.text_input("Client / Case name", ss["case_name"])

    files = st.file_uploader(
        "Upload evidence (PDF, DOCX, TXT, CSV, MD)",
        type=["pdf", "docx", "txt", "csv", "md"],
        accept_multiple_files=True
    )

    notes = st.text_area("Short context notes (optional)", ss["notes"], height=120)

    if st.button("Run IC Analysis"):
        ss["case_name"] = case_name
        ss["notes"] = notes

        # Parse uploaded files (safe fallback if nothing uploaded)
        parsed = parse_uploaded_files(files) if files else {"texts": [], "tables": []}

        # Draft IC assessment (heuristics demo)
        concatenated_text = (notes or "") + "\n".join(parsed.get("texts", []))
        assessment = draft_ic_assessment(concatenated_text)
        # Save analysis results in session state for later tabs
        ss["analysis"] = {
            "assessment": assessment,
            "case": case,
            "notes": text_input,
        } 
        ss["analysis"] = {"parsed": parsed, "assessment": assessment}
        st.success("Analysis complete. Continue to Expert Guide →")

# ---------------- TAB 2: EXPERT GUIDE ----------------
with tabs[1]:
    st.subheader("Expert Guide — Licensing Readiness")

    st.markdown("Use this guide to assess SME maturity and identify assets suitable for licensing.")

    col1, col2 = st.columns(2)
    with col1:
        growth_intent = st.radio(
            "Licensing Intent",
            ["Defensive (protect IP)", "Revenue (licensing income)", "Collaborative (partner growth)"],
            index=1
        )
    with col2:
        readiness_stage = st.select_slider(
            "Readiness Stage",
            options=["Concept", "Validated", "Market Tested", "Commercialised"],
            value="Validated"
        )

    st.markdown("### Evidence Checklist")
    guide = {}
    guide["assets_identified"] = st.checkbox("Key intangible assets identified (human, structural, customer, strategic)")
    guide["contracts_reviewed"] = st.checkbox("Existing IP or collaboration contracts reviewed")
    guide["governance_defined"] = st.checkbox("Evidence register and approval sign-off defined")
    guide["valuation_understood"] = st.checkbox("Valuation and risk tolerance discussed")

    if st.button("Save Expert Inputs"):
        ss["guide"] = guide
        st.success("Expert guide data saved successfully. Continue to Advisory →")

 # ---------------- TAB 3: ADVISORY ----------------
with tabs[2]:
    st.subheader("Advisory Narrative")

    if "analysis" not in ss:
        st.info("⚙️ Run IC analysis first on the Upload tab.")
    else:
        analysis = ss.get("analysis") or {}
assessment = analysis.get("assessment")
if not assessment:
    st.info("⚙️ Run IC analysis first on the Upload tab (then return here).")
    st.stop()

# Simple heuristic narrative (placeholder – connects to your IC logic later)
guide = ss.get("guide", {})
intent = guide.get("assets_identified", False)
readiness = guide.get("valuation_understood", False)

summary_text = "Based on current assessment, "
if intent and readiness:
    
    summary_text += (
        "the company demonstrates readiness for initial licensing steps. "
        "Evidence and governance appear adequate for partner or FRAND models."
    )
elif intent:
    summary_text += (
        "assets are identified but valuation and governance require further alignment."
            )
else:
    summary_text += (
        "further evidence gathering and IC-mapping are recommended before licensing."
            )

    st.text_area(
        "Generated Advisory Summary",
        summary_text,
        height=200,
        key="advisory_summary",
        )

if st.button("Save Advisory Narrative"):
            ss["advisory_summary"] = summary_text
            st.success("Advisory narrative saved. Continue to Exports →")

# ---- EU theme helper ----
def inject_eu_theme(): 
    pass

st.set_page_config(page_title="IC-LicAI Demo", layout="centered")
inject_eu_theme()
        
st.set_page_config(page_title="IC-LicAI Demo", layout="centered")
inject_eu_theme()

# --- Inputs ---
st.subheader("1) Case & Evidence")
case = st.text_input("Case name", value="Demo Case")
# --- Case profile (drives narrative tone) ---
st.subheader("Company profile")
size_label = st.selectbox(
    "Company size",
    ["Micro (1–10)", "Small (11–50)", "Medium (51–250)", "Enterprise (250+)"],
    index=0,  # default Micro
    help="Select the typical size for this case to adapt the advisory narrative."
)
sector = st.text_input("Sector (optional)", value="", help="e.g., food, medtech, services")

# Normalise size for the narrative engine
size_map = {
    "micro (1–10)": "micro",
    "small (11–50)": "small",
    "medium (51–250)": "medium",
    "enterprise (250+)": "enterprise",
}
size_key = size_map.get(size_label.lower(), "micro")
profile = {"size": size_key, "sector": sector.strip().lower()}
uploaded = st.file_uploader("Upload evidence (PDF, TXT, DOCX, etc.) — optional", type=None, accept_multiple_files=True)
notes = st.text_area("Paste interview notes or summary (optional)", height=160)

# demo note helper
demo_choice = st.selectbox("Or pick a demo note", ["(none)","VoltEdge","Capabilis","EuraLab"])
demo_text = ""
try:
    if demo_choice == "VoltEdge":
        demo_text = open("demo_assets/VoltEdge_note.txt", "r", encoding="utf-8").read()
    elif demo_choice == "Capabilis":
        demo_text = open("demo_assets/Capabilis_note.txt", "r", encoding="utf-8").read()
    elif demo_choice == "EuraLab":
        demo_text = open("demo_assets/EuraLab_note.txt", "r", encoding="utf-8").read()
except Exception:
    demo_text = demo_choice if demo_choice != "(none)" else ""

# assemble text input
text_input = "\n\n".join([t for t in [notes, demo_text] if t])

# prepare file tuples
files_data = []
if uploaded:
    for f in uploaded:
        try:
            files_data.append((f.name, f.getvalue()))
        except Exception:
            pass

st.divider()

# --- Run ---
if st.button("▶ Run IC-LicAI Analysis"):
    # light parse (currently demo scope)
    parsed = {"texts": [], "meta": []}
    files_data = []
    if uploaded:
        for f in uploaded:
            try:
                files_data.append((f.name, f.getvalue()))
            except Exception:
                pass
    if files_data:
        try:
            parsed = parse_uploaded_files(files_data)  # returns {"texts":[...], "meta":[...]}
        except Exception as e:
            st.warning(f"Parser note: {e}")

    # run assessment (heuristics demo)
    text_input = (notes or "") + "\n".join(parsed.get("texts", []))
    assessment = draft_ic_assessment(text_input)

# --- ensure assessment exists before building narrative ---
# If no files were parsed, guarantee a safe default structure
parsed = locals().get("parsed", {"texts": [], "meta": []})

# Build the text body (notes + any parsed texts)
base_text = (notes or "").strip()
joined_docs = "\n".join(parsed.get("texts", []))
text_input = (base_text + ("\n" if base_text and joined_docs else "") + joined_docs).strip()

# Run the lightweight IC assessment now, so `assessment` is defined
assessment = draft_ic_assessment(text_input)
# Build advisory narrative using the selected profile
import importlib
narratives_mod = importlib.import_module("narratives")

if hasattr(narratives_mod, "build_narrative_profiled"):
    narrative = narratives_mod.build_narrative_profiled(
        case,
        assessment.get("ic_map", {}),
        assessment.get("readiness", []),
        assessment.get("licensing", []),
        profile  # <-- size/sector from the UI
    )
    # ---- Advisory Narrative ----
st.subheader("Advisory Narrative")

narrative = locals().get("narrative", "") or ""

# Convert dicts/lists safely to string
if isinstance(narrative, (dict, list)):
    import json
    narr = json.dumps(narrative, indent=2)
else:
    narr = str(narrative).strip()

st.text_area("Preview (copyable)", narr, height=260)

st.download_button(
    "Download Narrative (.txt)",
    data=narr.encode("utf-8"),
    file_name=f"{case}_Advisory_Narrative.txt",
    mime="text/plain",
)
        
# --- Build export bundle (safe fallbacks) ---
case = locals().get("case", "") or st.session_state.get("case_name", "") or "Untitled Case"
assessment = locals().get("assessment", {}) or {}
narrative = locals().get("narrative", "") or ""
summary_text = assessment.get("summary", "") or "Advisory summary (auto): initial IC map + 10-Steps readiness + FRAND options prepared."

bundle = {
    "case": case,
    "summary": summary_text,
    "ic_map": assessment.get("ic_map", {}) or {},
    "readiness": assessment.get("readiness", []) or [],
    "licensing": assessment.get("licensing", []) or [],
    "narrative": narrative,
}

    # --- Show results ---
# --- Show results ---
st.subheader("Intangible Capital Map (4–Leaf)")
for leaf, items in bundle["ic_map"].items():
    st.write(f"**{leaf}**")
    for it in items[:6]:
        st.write(f"- {it}")

st.subheader("10–Steps Readiness Summary")
for row in bundle["readiness"]:
    st.write(f"**Step {row['step']}**: {row['name']} (Score {row['score']}/3)")
    for t in row["tasks"]:
        st.write(f"- {t}")

st.subheader("Licensing Options (advisory)")
lic = bundle.get("licensing", [])
for opt in lic:
    st.markdown(f"**{opt['model']}**")
    notes = opt.get("notes", [])
    if isinstance(notes, str):
        notes = [notes]
    for t in notes:
        st.write(f"- {t}")
lic = bundle.get("licensing", [])
for opt in lic:
    # Heading
    st.markdown(f"**{opt.get('model', '').strip()}**")
    # Notes can be a string or a list -> normalize to list
    notes = opt.get("notes", [])
    if isinstance(notes, str):
        notes = [notes]
    for line in notes:
        st.write(f"- {line}")
st.subheader("Advisory Narrative")

# Make sure `narrative` exists even if an earlier step didn’t set it
narrative = locals().get("narrative", "") or ""

# Use narrative directly (do NOT read from bundle here)
# Ensure narrative is text before stripping
if isinstance(narrative, (dict, list)):
    import json
    narr = json.dumps(narrative, indent=2)
else:
    narr = str(narrative or "").strip()

st.text_area("Preview (copyable)", narr, height=260, key="narrative_preview_v2")
st.download_button(
    "Download Narrative (.txt)",
    data=narr.encode("utf-8"),
    file_name=f"{case}_Advisory_Narrative.txt",
    mime="text/plain",
    key="narrative_download_v2",
)
# ---- normalize to bytes for download buttons ----
def _to_bytes(x, encoding="utf-8"):
    if x is None:
        return b""
    # accept both bytes and bytearray
    if isinstance(x, (bytes, bytearray)):
        return bytes(x)
    # BytesIO or similar
    if hasattr(x, "getvalue"):
        return x.getvalue()
    # plain string
    if isinstance(x, str):
        return x.encode(encoding)
    # JSON-encode objects (last resort)
    try:
        import json
        return json.dumps(x).encode(encoding)
    except Exception:
        return str(x).encode(encoding)

# --- Prepare downloadable data (safe) ---
pdf_bytes = xlsx_bytes = json_bytes = None

try:
    pdf_bytes = _to_bytes(export_pdf(bundle))
except Exception as e:
    st.error(f"PDF export failed: {e}")

try:
    xlsx_bytes = _to_bytes(export_xlsx(bundle.get("ic_map", {})))
except Exception as e:
    st.error(f"XLSX export failed: {e}")

try:
    json_bytes = _to_bytes(export_json(bundle))
except Exception as e:
    st.error(f"JSON export failed: {e}")

# --- Downloads ---
if any([pdf_bytes, xlsx_bytes, json_bytes]):
    if pdf_bytes:
        st.download_button(
            "Download Advisory Report (PDF)",
            data=pdf_bytes,
            file_name=f"{case}_ICLicAI_Advisory_Report.pdf",
            mime="application/pdf",
        )
    if xlsx_bytes:
        st.download_button(
            "Download IA Register (XLSX)",
            data=xlsx_bytes,
            file_name=f"{case}_ICLicAI_IA_Register.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    if json_bytes:
        st.download_button(
            "Download Case Data (JSON)",
            data=json_bytes,
            file_name=f"{case}_ICLicAI_Case.json",
            mime="application/json",
        )
else:
    st.info("Upload case files and click **Run IC-LicAI Analysis** to generate downloads.")
