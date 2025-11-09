# coding: utf-8
# ic_licai/exporters_clean.py — robust ASCII-safe PDF/XLSX/JSON exporters
# Prefers Arial (standard FPDF font)
# Replaces problematic unicode characters (“—” “•” “…” etc.) to avoid FPDF width/encoding errors
# Adds pages lazily (only when a section has content)

from __future__ import annotations
import io
import json
from fpdf import FPDF
from typing import Dict, Any, List

try:
    import pandas as pd
except Exception:
    pd = None  # XLSX optional


# ----------------- Text Helpers -----------------
def _latin1(text: str) -> str:
    """Convert to Latin-1 safe text and replace common troublemakers."""
    if text is None:
        return ""
    s = str(text)
    for bad, good in {
        "•": "-",
        "–": "-",
        "—": "-",
        "’": "'",
        "“": '"',
        "”": '"',
        "…": "...",
        "\t": " ",
        "\u00A0": " ",
    }.items():
        s = s.replace(bad, good)
    return s.encode("latin-1", "replace").decode("latin-1")


# ----------------- PDF Class -----------------
class PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_auto_page_break(auto=True, margin=18)

    def header(self):
        # Leave header empty for clean report
        pass


def _section(pdf: PDF, heading: str):
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, _latin1(heading), ln=1)
    pdf.ln(2)


def _wrap_text(pdf: PDF, text: str):
    """Safely wrap long text blocks."""
    if not text:
        return
    txt = _latin1(text)
    pdf.set_font("Arial", "", 10)
    for line in txt.split("\n"):
        if not line.strip():
            pdf.ln(3)
            continue
        pdf.multi_cell(0, 6, line)


# ----------------- Exporters -----------------
def export_pdf(data: Dict[str, Any]) -> bytes:
    """Generate advisory/licensing PDF report."""
    pdf = PDF(format="A4")
    pdf.add_page()

    # ---- Cover / Executive Summary ----
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, _latin1("Intangible Capital & Licensing Readiness Report"), ln=1)
    pdf.ln(5)

    case = _latin1(data.get("case") or "Client")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, f"Client: {case}", ln=1)
    pdf.ln(2)

    _wrap_text(pdf, data.get("summary", ""))

    # ---- Body Sections (lazy pages) ----
    ic_map = data.get("ic_map", {}) or {}
    if isinstance(ic_map, dict) and any(v for v in ic_map.values()):
        _section(pdf, "Intangible Capital Map (4-Leaf)")
        for leaf, items in ic_map.items():
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 6, _latin1(f"• {leaf}"), ln=1)
            pdf.set_font("Arial", "", 10)
            for it in (items or [])[:6]:
                pdf.multi_cell(0, 6, _latin1(f"  - {it}"))
            pdf.ln(1)

    readiness = data.get("readiness", []) or []
    if isinstance(readiness, list) and readiness:
        _section(pdf, "10-Steps Readiness Summary")
        for row in readiness:
            step = row.get("step", "")
            name = row.get("name", "")
            score = row.get("score")
            left = f"{step}: {name}"
            right = f"(Score {score}/3)" if score is not None else ""
            pdf.cell(0, 6, _latin1(f"{left}  {right}"), ln=1)
            for t in row.get("tasks", []) or []:
                pdf.multi_cell(0, 6, _latin1(f"  - {t}"))
            pdf.ln(1)

    lic = data.get("licensing", []) or []
    if isinstance(lic, list) and lic:
        _section(pdf, "Licensing Options (Advisory)")
        for opt in lic:
            model = _latin1(str(opt.get("model", "")).strip())
            notes = opt.get("notes", [])
            if isinstance(notes, str):
                notes = [notes]
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 6, model or "Option", ln=1)
            pdf.set_font("Arial", "", 10)
            for n in notes:
                pdf.multi_cell(0, 6, _latin1(f"  - {n}"))
            pdf.ln(1)

    narr = data.get("narrative", "")
    if isinstance(narr, (dict, list)):
        narr = json.dumps(narr, ensure_ascii=False, indent=2)
    if isinstance(narr, str) and narr.strip():
        _section(pdf, "Advisory Narrative")
        _wrap_text(pdf, narr)

    # ---- Governance & Audit Note ----
    _section(pdf, "Governance & Audit Note")
    _wrap_text(
        pdf,
        "This report is generated using an advisory-first workflow with human approval. "
        "Evidence sources and decisions should be recorded in an IA Register."
    )

    out = pdf.output(dest="S")
    return out.encode("latin-1", "replace") if isinstance(out, str) else out


def export_xlsx(ic_map: Dict[str, List[str]]) -> bytes:
    """Export simple IA Register sheet from IC Map."""
    if not pd:
        return b"No pandas available"

    rows: List[Dict[str, str]] = []
    for leaf, items in (ic_map or {}).items():
        for i in items:
            rows.append({"Capital": _latin1(leaf), "Item": _latin1(i)})

    df = pd.DataFrame(rows, columns=["Capital", "Item"])
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="IA Register")
    return bio.getvalue()


def export_json(bundle: Dict[str, Any]) -> bytes:
    """Export bundle as UTF-8 JSON."""
    return json.dumps(bundle, ensure_ascii=False, indent=2).encode("utf-8")
