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
def _usable_width(pdf: FPDF) -> float:
    """Printable width that is never too small for FPDF."""
    return max(20.0, float(pdf.w) - float(pdf.l_margin) - float(pdf.r_margin))

def _safe_multicell(pdf: FPDF, text: str, h: float = 6.0) -> None:
    """Multi-cell that never throws, with hard-wrap fallback."""
    w = _usable_width(pdf)
    try:
        pdf.multi_cell(w, h, text)
        return
    except Exception:
        pass
    # Fallback 1: force-break every 60 chars
    try:
        chunks = [text[i:i+60] for i in range(0, len(text), 60)] or [text]
        for c in chunks:
            pdf.multi_cell(w, h, c)
        return
    except Exception:
        pass
    # Fallback 2: last resort
    pdf.multi_cell(w, h, "?")

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
    if not text:
        return

    def _hard_wrap_token(tok: str, maxlen: int = 60) -> list[str]:
        return [tok[i:i + maxlen] for i in range(0, len(tok), maxlen)]

    raw = _latin1(text).replace("\t", "    ")
    raw = "".join(ch if (ord(ch) >= 32 or ch in "\n") else " " for ch in raw)

    lines: list[str] = []
    for ln in raw.split("\n"):
        ln = ln.rstrip()
        if not ln:
            lines.append("")
            continue
        tokens: list[str] = []
        for tok in ln.split(" "):
            if len(tok) > 60:
                tokens.extend(_hard_wrap_token(tok, 60))
            else:
                tokens.append(tok)
        lines.append(" ".join(tokens))

    pdf.set_auto_page_break(auto=True, margin=18)
    for ln in lines:
        if not ln.strip():
            pdf.ln(2)
            continue
        _safe_multicell(pdf, ln)  

def _bullet(pdf: PDF, text: str) -> None:
    pdf.set_font("Arial", "", 10)
    line = f"- {_latin1(text)}"
    _safe_multicell(pdf, line)

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
    pdf.set_font("Arial", "", 11)z

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
