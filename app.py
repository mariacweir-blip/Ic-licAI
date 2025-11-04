import streamlit as st
import pandas as pd
from io import BytesIO
from ic_licai.processing import parse_uploaded_files, draft_ic_assessment
from ic_licai.exporters import export_pdf, export_xlsx, export_json

st.set_page_config(page_title="IC‑LicAI Demo", layout="centered")

# --- Simple password gate ---
if "authed" not in st.session_state:
    st.session_state.authed = False

def gate():
    st.title("IC‑LicAI — Intangible Capital Licensing (Demo)")
    st.caption("Human‑centric • EU‑aligned • Advisory‑first")
    pwd = st.text_input("Enter demo password", type="password")
    if st.button("Unlock"):
        if pwd.strip() == "ICdemo2025!":
            st.session_state.authed = True
        else:
            st.error("Incorrect password")

if not st.session_state.authed:
    gate()
    st.stop()

st.title("IC‑LicAI — Demo")
st.caption("Upload evidence, run analysis, export advisory report.")

case = st.selectbox("Choose a scenario", ["VoltEdge (GreenTech battery)","Capabilis (Capability Licensing OS)","EuraLab (University TTO)"])

uploaded = st.file_uploader("Upload files (PDF/DOC/TXT)", type=["pdf","docx","txt"], accept_multiple_files=True)
notes = st.text_area("Paste interview notes / context", height=180, help="High‑level notes to seed the advisory output.")

mode = st.radio("Run mode", ["Live (demo heuristics)", "Safe demo (pre‑filled)"], horizontal=True)

if st.button("▶ Run IC‑LicAI Analysis"):
    files = []
    for f in uploaded or []:
        files.append((f.name, f.read()))
    parsed = parse_uploaded_files(files)
    # For demo, combine file texts + notes into one source string
    combined_text = "\n".join(parsed["texts"] + [notes])

    assessment = draft_ic_assessment(combined_text if mode.startswith("Live") else notes)

    # Prepare outputs bundle
    bundle = {
        "case": case,
        "summary": f"Advisory overview for {case}.",
        "ic_map": assessment["ic_map"],
        "readiness": assessment["readiness"],
        "licensing": assessment["licensing"],
    }

    st.subheader("Intangible Capital Map (4‑Leaf)")
    df_rows = []
    for leaf, items in assessment["ic_map"].items():
        for it in items:
            df_rows.append({"Capital": leaf, "Item": it})
    st.dataframe(pd.DataFrame(df_rows))

    st.subheader("10‑Steps Readiness (summary)")
    st.table(pd.DataFrame(assessment["readiness"])[["step","name","score"]])

    st.subheader("Licensing Options (advisory)")
    st.table(pd.DataFrame(assessment["licensing"]))

   # Exporters
pdf_bytes = export_pdf(bundle)
# Ensure Streamlit receives bytes, not str (fpdf2 sometimes returns str)
if isinstance(pdf_bytes, str):
    pdf_bytes = pdf_bytes.encode("latin-1")

xlsx_bytes = export_xlsx(assessment["ic_map"])
json_bytes = export_json(bundle)

# ---- normalize to bytes for download buttons ----
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

# PDF is latin-1 from fpdf2; others are utf-8/bytes
pdf_bytes  = _to_bytes(pdf_bytes,  "latin-1")
xlsx_bytes = _to_bytes(xlsx_bytes)
json_bytes = _to_bytes(json_bytes, "utf-8")

# Downloads
st.download_button("⬇ Download Advisory Report (PDF)", data=pdf_bytes,file_name="ICLicAI_Advisory_Report.pdf", mime="application/pdf")
st.download_button("⬇ Download IA Register (XLSX)", data=xlsx_bytes,file_name="ICLicAI_IA_Register.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
st.download_button("⬇ Download Case Data (JSON)", data=json_bytes,file_name="ICLicAI_Case.json", mime="application/json")

st.caption("Note: Demo uses heuristics for speed. Replace with your 4‑Leaf / 10‑Steps / IAS 38 / FRAND engines.")
