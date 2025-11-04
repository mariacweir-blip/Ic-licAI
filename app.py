import streamlit as st
from ic_licai.processing import parse_uploaded_files, draft_ic_assessment
from ic_licai.exporters import export_pdf, export_xlsx, export_json
import os
# --- EU Theme injection ---
import pathlib
def inject_eu_theme():
    try:
        css = (pathlib.Path("theme") / "eu.css").read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except Exception:
        pass
st.set_page_config(page_title="IC‑LicAI Demo", page_icon="🔐", layout="centered")
inject_eu_theme()
# --- Simple demo gate ---
st.title("IC‑LicAI: Licensing Advisory (Demo)")
pw = st.text_input("Enter demo password", type="password", help="Demo gate")
if pw != "ICdemo2025!":
    st.info("Hint: use the demo password you were given.")
    st.stop()

# --- Inputs ---
st.subheader("1) Case & Evidence")
case = st.text_input("Case name", value="Demo Case")
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
if st.button("▶ Run IC‑LicAI Analysis"):
    # light parse (currently demo scope)
    parsed = {"texts": [], "meta": []}
    if files_data:
        try:
            parsed = parse_uploaded_files(files_data)  # returns {"texts": [...], "meta": [...]}
        except Exception as e:
            st.warning(f"Parser note: {e}")

    # run assessment (heuristics demo)
    assessment = draft_ic_assessment((text_input or "") + "\n".join(parsed.get("texts", [])))

    # bundle for exports
    bundle = {
        "case": case,
        "summary": f"Advisory overview for {case}.",
        "ic_map": assessment.get("ic_map", {}),
        "readiness": assessment.get("readiness", []),
        "licensing": assessment.get("licensing", []),
    }

    # --- Show results ---
    st.subheader("Intangible Capital Map (4‑Leaf)")
    for leaf, items in bundle["ic_map"].items():
        st.write(f"**{leaf}**")
        for it in items[:6]:
            st.write(f"* {it}")

    st.subheader("10‑Steps Readiness Summary")
    for row in bundle["readiness"]:
        st.write(f"**Step {row['step']}: {row['name']}** — Score {row['score']}/3")
        for t in row["tasks"]:
            st.write(f"- {t}")

    st.subheader("Licensing Options (advisory)")
    for opt in bundle["licensing"]:
        st.write(f"**{opt['model']}**")
        st.write(opt["notes"])

    # --- Exports ---
    pdf_bytes = export_pdf(bundle)
    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode("latin-1")
    xlsx_bytes = export_xlsx(bundle["ic_map"])
    json_bytes = export_json(bundle)

    # normalize to bytes
    def _to_bytes(x, encoding="utf-8"):
        if x is None:
            return b""
        if isinstance(x, bytes):
            return x
        if hasattr(x, "getvalue"):
            return x.getvalue()
        if isinstance(x, str):
            return x.encode(encoding)
        try:
            return bytes(x)
        except Exception:
            return str(x).encode(encoding)

    pdf_bytes  = _to_bytes(pdf_bytes,  "latin-1")
    xlsx_bytes = _to_bytes(xlsx_bytes)
    json_bytes = _to_bytes(json_bytes, "utf-8")

    st.download_button("⬇ Download Advisory Report (PDF)",
                       data=pdf_bytes,
                       file_name="ICLicAI_Advisory_Report.pdf",
                       mime="application/pdf")

    st.download_button("⬇ Download IA Register (XLSX)",
                       data=xlsx_bytes,
                       file_name="ICLicAI_IA_Register.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.download_button("⬇ Download Case Data (JSON)",
                       data=json_bytes,
                       file_name="ICLicAI_Case.json",
                       mime="application/json")

    st.caption("Note: Demo uses heuristics for speed. Replace with your 4‑Leaf / 10‑Steps / IAS 38 / FRAND engines.")
