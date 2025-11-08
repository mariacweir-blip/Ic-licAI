   # -*- coding: utf-8 -*-
from typing import Dict, Any, List
from fpdf import FPDF
import json
import io
import pandas as pd

# -------- PDF helpers --------
class PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.l_margin = 18
        self.r_margin = 18
        self.t_margin = 18
        self.set_auto_page_break(auto=True, margin=18)
        self.header_title = ""

    def header(self):
        if self.header_title:
            self.set_font("Helvetica", "B", 12)
            self.cell(0, 8, self.header_title, ln=1)

# simple text wrapper that works with FPDF.multi_cell
def _wrap_text(pdf, text, width=None):
    # normalize to string
    if not isinstance(text, str):
        text = "" if text is None else str(text)

    # compute usable width if not provided
    if width is None:
        width = int(pdf.w - pdf.l_margin - pdf.r_margin)

    # ensure auto page break is on
    pdf.set_auto_page_break(auto=True, margin=18)

    # print paragraph line by line (blank lines = small spacer)
    for line in (text or "").split("\n"):
        if not line.strip():
            pdf.ln(2)
            continue
        pdf.multi_cell(width, 6, line)
       
def _wrap_text(pdf: PDF, text: str | None, width: int | None = None) -> None:
    """Safe paragraph printing: tolerate None/empty strings and blank lines."""
    if not text:
        return
    if width is None:
        width = int(pdf.w - pdf.l_margin - pdf.r_margin)
    for line in str(text).split("\n"):
        if not line.strip():
            pdf.ln(2)  # small spacer for blank lines
            continue
        pdf.multi_cell(width, 6, line)
def _bullet(pdf: PDF, text: str) -> None:
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(5, 6, "•")
    pdf.multi_cell(0, 6, text)

# -------- Exporters --------
def export_pdf(data: Dict[str, Any]) -> bytes:
    """
    Expected keys in data:
      - case: str
      - summary: str
      - ic_map: Dict[str, List[str]]
      - readiness: List[Dict[str, Any]]  (step/name/score,tasks)
      - licensing: List[Dict[str, Any]]  (model, notes[str or list])
      - narrative: str
    """
    pdf = PDF(format="A4")
    pdf.add_page()

    # Cover / Summary
    pdf.header_title = "Intangible Capital & Licensing Readiness Report"
    pdf.set_font("Helvetica", "", 12)
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Case: {data.get('case','(unspecified)')}", ln=1)
    pdf.ln(2)
    _wrap_text(pdf, data.get("summary", ""))

    # 4-Leaf IC map (first 6 items per leaf for brevity)
    pdf.add_page()
    pdf.header_title = "Intangible Capital Map (4-Leaf)"
    ic_map = data.get("ic_map", {}) or {}
    pdf.set_font("Helvetica", "", 10)
    for leaf, items in ic_map.items():
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 6, f"• {leaf}", ln=1)
        pdf.set_font("Helvetica", "", 10)
        for it in (items or [])[:6]:
            _bullet(pdf, it)
        pdf.ln(2)

    # Narrative
    if data.get("narrative"):
        pdf.add_page()
        pdf.header_title = "Advisory Narrative"
        _wrap_text(pdf, data.get("narrative", ""))

    # 10-Steps summary
    pdf.add_page()
    pdf.header_title = "10-Steps Readiness Summary"
    for row in data.get("readiness", []):
        step = row.get("step")
        name = row.get("name")
        score = row.get("score")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"Step {step}: {name} (score {score}/3)", ln=1)
        for t in row.get("tasks", []):
            _bullet(pdf, t)
        pdf.ln(2)

    # Licensing options (FIX: normalize notes to list)
    pdf.add_page()
    pdf.header_title = "Licensing Options (advisory)"
    for opt in data.get("licensing", []):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 6, f"{opt.get('model')}", ln=1)
        pdf.set_font("Helvetica", "", 10)
        notes = opt.get("notes", [])
        if isinstance(notes, str):
            notes = [notes]
        for t in notes:
            _bullet(pdf, t)
        pdf.ln(1)

    # Governance
    pdf.add_page()
    pdf.header_title = "Governance & Audit Note"
    _wrap_text(pdf, "This report is generated using an advisory-first workflow with human approval. "
                    "Evidence sources and decisions should be recorded in an IA register.")

    return bytes(pdf.output(dest="S"))

def export_xlsx(ic_map: Dict[str, List[str]]) -> bytes:
    """
    Simple IA Register sheet from ic_map.
    """
    rows = []
    for leaf, items in (ic_map or {}).items():
        for it in items:
            rows.append({"Capital": leaf, "Item": it})
    df = pd.DataFrame(rows, columns=["Capital", "Item"])
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="xlsxwriter") as xw:
        df.to_excel(xw, index=False, sheet_name="IA Register")
    return bio.getvalue()

def export_json(bundle: Dict[str, Any]) -> bytes:
    return json.dumps(bundle, ensure_ascii=False, indent=2).encode("utf-8")
