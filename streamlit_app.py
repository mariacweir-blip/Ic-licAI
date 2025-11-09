import pathlib
import streamlit as st

# Robust loader that ignores BOMs / tabs / odd encodings in app_clean.py
try:
    p = pathlib.Path(__file__).with_name("app_clean.py")
    src = p.read_text(encoding="utf-8-sig")  # strips BOM if present
    # normalize line endings + tabs, just in case
    src = src.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")
    code = compile(src, str(p), "exec")
    g = {"__name__": "__main__", "__file__": str(p)}
    exec(code, g, g)
except Exception as e:
    st.error("Startup error while loading app_clean.py")
    st.exception(e)
