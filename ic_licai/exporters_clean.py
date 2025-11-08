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
    # Replace Unicode bullets etc. with ASCII
    s = str(text).replace("•", "- ")
    # Replace any remaining non-latin1 with '?'
    return s.encode("latin-1", "replace").decode("latin-1")


class PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.l_margin = 18
        self.r_margin = 18
        self.t_margin = 18
        self.set_auto_page_break(auto=True, margin=18)

    def header(self):
        # we’ll draw section titles in the body; keep header minimal
        return


def _wrap_text(pdf: PDF, text: str | None, width: int | None = None) -> None:
    """
    Safe paragraph printing:
    - latin-1 sanitize
    - replace tabs
    - hard-wrap tokens with no natural break (e.g., long URLs)
    - use width=0 to let FPDF auto-calc available line width
    """
    if not text:
        return

    def _hard_wrap_token(tok: str, maxlen: int = 60) -> list[str]:
        # Split a single overlong token into chunks so FPDF can render it
        return [tok[i:i + maxlen] for i in range(0, len(tok), maxlen)]

    # sanitize + normalize
    txt = _latin1(text).replace("\t", "    ")

    # split into lines, then tokens; hard-wrap any token > maxlen
    normalized_lines: list[str] = []
    for raw_line in txt.split("\n"):
        raw_line = raw_line.rstrip()
        if not raw_line:
            normalized_lines.append("")  # preserve blank lines
            continue
        pieces: list[str] = []
        for tok in raw_line.split(" "):
            if len(tok) > 60:
                pieces.extend(_hard_wrap_token(tok, 60))
            else:
                pieces.append(tok)
        normalized_lines.append(" ".join(pieces))

    pdf.set_auto_page_break(auto=True, margin=18)

    # Use width=0 → FPDF auto width (avoids zero/negative width issues)
    for line in normalized_lines:
        if not line.strip():
            pdf.ln(2)
            continue
        pdf.multi_cell(0, 6, line)


def _bullet(pdf: PDF, text: str) -> None:
    # ASCII bullet + safe wrap
    line = f"- {_latin1(text)}"
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 6, line)

# ---------- Exporters ----------

def export_pdf(data: Dict[str, Any]) -> bytes:
    """
    Expected keys in data:
      - case: str
      - summary: str
      - ic_map: Dict[str, List[str]]  (leaf -> items)
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

    # 4-Leaf IC Map (first 6 per leaf for brevity)
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, _latin1("Intangible Capital Map (4-Leaf)"), ln=1)
    pdf.ln(2)

    ic_map = data.get("ic_map", {}) or {}
    for leaf, items in ic_map.items():
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 6, _latin1(f"- {leaf}"), ln=1)
        pdf.set_font("Arial", "", 10)
        for it in (items or [])[:6]:
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
        name = row.get("name", "")
        score = row.get("score")
        pdf.set_font("Arial", "", 10)
        left = f"Step {step}: {name}"
        right = f"Score {score}/3" if score is not None else ""
        pdf.cell(0, 6, _latin1(f"{left}   {right}"), ln=1)
        for t in row.get("tasks", []) or []:
            _bullet(pdf, t)
        pdf.ln(2)

    # Licensing Options (advisory)
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
        "Evidence sources and decisions should be recorded in an IA register.",
    )

    # Return PDF bytes (latin-1) – safe because we sanitize text to latin-1
    return pdf.output(dest="S").encode("latin-1")


def export_xlsx(ic_map: Dict[str, List[str]]) -> bytes:
    """
    Simple IA Register sheet from ic_map.
    """
    rows: List[Dict[str, str]] = []
    ic_map = ic_map or {}
    for leaf, items in ic_map.items():
        for it in items or []:
            rows.append({"Capital": _latin1(leaf), "Item": _latin1(it)})

    df = pd.DataFrame(rows, columns=["Capital", "Item"])
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="xlsxwriter") as xw:
        df.to_excel(xw, index=False, sheet_name="IA Register")
    return bio.getvalue()


def export_json(bundle: Dict[str, Any]) -> bytes:
    return json.dumps(bundle, ensure_ascii=False, indent=2).encode("utf-8")
