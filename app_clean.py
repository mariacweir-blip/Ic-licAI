import streamlit as st
import importlib, os, sys
from pathlib import Path

# Safe import block (avoids indentation / encoding issues)
try:
    from ic_licai.processing import parse_uploaded_files, draft_ic_assessment
    from ic_licai.exporters import export_pdf, export_xlsx, export_json
except Exception:
    sys.path.append(str(Path(__file__).resolve().parent))
    from processing import parse_uploaded_files, draft_ic_assessment
    from exporters import export_pdf, export_xlsx, export_json

st.set_page_config(page_title="IC-LicAI Demo", layout="centered")
