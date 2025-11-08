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
    # ---- EU theme helper ----
    def inject_eu_theme(): pass

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
    else:
        narrative = narratives_mod.build_narrative(
            case,
            assessment.get("ic_map", {}),
            assessment.get("readiness", []),
            assessment.get("licensing", []),
        )

    # bundle for exports
    bundle = {
        "case": case,
        "summary": f"Advisory overview for {case}.",
        "ic_map": assessment.get("ic_map", {}),
        "readiness": assessment.get("readiness", []),
        "licensing": assessment.get("licensing", []),
        "narrative": narrative,
    }

    # --- Show results ---
    st.subheader("Intangible Capital Map (4–Leaf)")
    for leaf, items in bundle["ic_map"].items():
        st.write(f"**{leaf}**")
        for it in items[:6]:
            st.write(f"- {it}")

    st.subheader("10–Steps Readiness (summary)")
    for row in bundle["readiness"]:
        st.write(f"**Step {row['step']}: {row['name']}** – Score {row['score']}/3")
        for t in row["tasks"]:
            st.write(f"- {t}")

    st.subheader("Licensing Options (advisory)")

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
    st.write(bundle["narrative"])

    # ---- normalize to bytes for download buttons -----
    def _to_bytes(x, encoding="utf-8"):
        if x is None:
            return b""
        if isinstance(x, bytes):
            return x
        if hasattr(x, "getvalue"):  # BytesIO or similar
            return x.getvalue()
        if isinstance(x, str):
            return x.encode(encoding)
        try:
            return bytes(x)
        except Exception:
            return str(x).encode(encoding)

    # PDF likely latin-1 from fpdf2; others utf-8/bytes
    pdf_bytes  = _to_bytes(export_pdf(bundle), "latin-1")
    xlsx_bytes = _to_bytes(export_xlsx(assessment.get("ic_map", {})))  # already bytes, safe
    json_bytes = _to_bytes(export_json(bundle), "utf-8")

    # Downloads
    st.download_button("⬇ Download Advisory Report (PDF)", data=pdf_bytes,
                       file_name="ICLicAI_Advisory_Report.pdf", mime="application/pdf")
    st.download_button("⬇ Download IA Register (XLSX)", data=xlsx_bytes,
                       file_name="ICLicAI_IA_Register.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.download_button("⬇ Download Case Data (JSON)", data=json_bytes,
                       file_name="ICLicAI_Case.json", mime="application/json")
else:
    st.info("Upload case files and click **Run IC-LicAI Analysis** to generate outputs.")
