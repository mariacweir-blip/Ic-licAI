# -*- coding: utf-8 -*-
from typing import Dict, Any, List
from fpdf import FPDF
import json
import io
import pandas as pd

# ---------- helpers ----------

def _latin1(text: str) -> str:
    """Make text safe for FPDF core fonts (latin-1 only)."""
    if text is None:
        return ""
    s = str(text)
    # Replace Unicode bullets/emdashes/tabs with ASCII equivalents.
    s = (
        s.replace("•", "-")
         .replace("–", "-")
         .replace("—", "-")
         .replace("\t", " ")
         .replace("\u00A0", " ")  # NBSP to space
    )
    # Finally, encode/decode so any remaining non-latin1 becomes '?'
    return s.encode("latin-1", "replace").decode("latin-1")

class PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.l_margin = 18
        self.r_margin = 18
        self.t_margin = 18
        self.set_auto_page_break(auto=True, margin=18)
    def header(self):
        # keep header minimal; draw section titles in body instead
        if self.header_title:
            self.set_font("Arial", "B", 12)
            self.cell(0, 8, _latin1(self.header_title), ln=1)

def _wrap_text(pdf: PDF, text: str, width: int | None = None) -> None:
    """
    Safely print text with wrapping, even if a token is very long.
    """
    if not text:
        return

    txt = _latin1(text).replace("\t", " ")
    if width is None:
        width = int(pdf.w - pdf.l_margin - pdf.r_margin)

    # Split into lines, then hard-wrap tokens that exceed ~60 chars
    normalized: list[str] = []
    for raw_line in txt.split("\n"):
        raw_line = raw_line.rstrip()
        if not raw_line:
            normalized.append("")  # preserve blank lines
            continue
        tokens: list[str] = []
        for tok in raw_line.split(" "):
            if len(tok) > 60:
                parts = [tok[i:i+60] for i in range(0, len(tok), 60)]
                tokens.extend(parts)
            else:
                tokens.append(tok)
        normalized.append(" ".join(tokens))

    pdf.set_auto_page_break(auto=True, margin=18)
    for line in normalized:
        if not line.strip():
            pdf.ln(2)
            continue
        pdf.multi_cell(width, 6, line)

def _bullet(pdf, text):
    """Print a bullet (ASCII dash) and wrap long lines safely."""
    _wrap_text(pdf, f"- {text}")
    
# ---------- Exporters ----------

def export_pdf(data: Dict[str, Any]) -> bytes:
    """
    Expected keys:
      - case: str
      - summary: str
      - ic_map: Dict[str, List[str]] (leaf -> items)
      - readiness: List[Dict[str, Any]] (step/name/score/tasks)
      - licensing: List[Dict[str, Any]] (model, notes[str or list])
      - narrative: str
    """
    pdf = PDF(format="A4")
    pdf.add_page()

    # Cover / Executive Summary
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, _latin1("Intangible Capital & Licensing Readiness Report"), ln=1)
    pdf.ln(2)

    case = data.get("case") or "(unspecified)"
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 6, _latin1(f"Case: {case}"), ln=1)
    pdf.ln(2)

    _wrap_text(pdf, data.get("summary", ""))

    # 4-Leaf IC Map (first few items per leaf for brevity)
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, _latin1("Intangible Capital Map (4–Leaf)"), ln=1)
    pdf.ln(2)

    ic_map = data.get("ic_map", {}) or {}
    pdf.set_font("Arial", "", 10)
    for leaf, items in ic_map.items():
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 6, _latin1(f"{leaf}"), ln=1)
        pdf.set_font("Arial", "", 10)
        for it in list(items or [])[:6]:
            _bullet(pdf, it)
        pdf.ln(2)

    # Advisory Narrative
    if data.get("narrative"):
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, _latin1("Advisory Narrative"), ln=1)
        pdf.ln(2)
        _wrap_text(pdf, data.get("narrative", ""))

    # 10-Steps Readiness Summary
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, _latin1("10-Steps Readiness Summary"), ln=1)
    pdf.ln(1)

    for row in data.get("readiness", []) or []:
        step = row.get("step")
        name = row.get("name")
        score = row.get("score")
        left = f"Step {step}: {name}" if name is not None else f"Step {step}"
        right = f"  (Score {score}/3)" if score is not None else ""
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, _latin1(f"{left}{right}"), ln=1)
        for t in row.get("tasks", []) or []:
            _bullet(pdf, t)
        pdf.ln(2)

    # Licensing options (advisory)
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, _latin1("Licensing Options (advisory)"), ln=1)
    pdf.ln(1)

    for opt in data.get("licensing", []) or []:
        model = _latin1(f"{opt.get('model', '')}")
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 6, model, ln=1)
        pdf.set_font("Arial", "", 10)
        notes = opt.get("notes", [])
        if isinstance(notes, str):
            notes = [notes]
        for t in notes or []:
            _bullet(pdf, t)
        pdf.ln(1)

    # Governance note
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, _latin1("Governance & Audit Note"), ln=1)
    pdf.ln(1)
    _wrap_text(
        pdf,
        "This report is generated using an advisory-first workflow with human approval. "
        "Evidence sources and decisions should be recorded in an IA register."
    )

    # Return PDF bytes (handle both str and bytearray from FPDF)
    out = pdf.output(dest="S")
if isinstance(out, (bytes, bytearray)):
    return bytes(out)
else:
    # Older FPDF may return a str -> encode safely
    return out.encode("latin-1", "replace")


def export_xlsx(ic_map: Dict[str, List[str]]) -> bytes:
    """Simple IA Register sheet from ic_map."""
    rows: List[Dict[str, str]] = []
    icm = ic_map or {}
    for leaf, items in icm.items():
        for it in items or []:
            rows.append({"Capital": _latin1(leaf), "Item": _latin1(it)})
    df = pd.DataFrame(rows, columns=["Capital", "Item"])
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="xlsxwriter") as xw:
        df.to_excel(xw, index=False, sheet_name="IA Register")
    return bio.getvalue()

def export_json(bundle: Dict[str, Any]) -> bytes:
    return json.dumps(bundle, ensure_ascii=False, indent=2).encode("utf-8")
