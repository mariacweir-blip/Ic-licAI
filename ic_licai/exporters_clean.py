# ic_licai/exporters.py — robust, ASCII-safe PDF/XLSX/JSON exporters
# - Prefers Arial/DejaVu if TTF exists; otherwise falls back to Helvetica
# - Replaces problematic unicode (• – — “ ” ’ …) to avoid FPDF width/encoding errors
# - XLSX export falls back to CSV if pandas/xlsxwriter not available

from __future__ import annotations

import io
import json
from pathlib import Path
from datetime import datetime

# PDF
from fpdf import FPDF

# XLSX (optional)
try:
    import pandas as pd  # type: ignore
except Exception:
    pd = None  # pandas is optional

# -----------------------------
# Text helpers
# -----------------------------
def ascii_safe(text) -> str:
    """Make text latin-1 friendly and replace common troublemakers."""
    if text is None:
        return ""
    t = str(text)
    # Replace typical offenders
    t = (t
         .replace("•", "- ")
         .replace("–", "-")
         .replace("—", "-")
         .replace("“", '"')
         .replace("”", '"')
         .replace("’", "'")
         .replace("…", "...")
         )
    # Best-effort latin-1
    try:
        t.encode("latin-1")
        return t
    except Exception:
        return t.encode("latin-1", "ignore").decode("latin-1")


def _wrap_lines(pdf: FPDF, text: str):
    """Streamlit-safe + FPDF-safe wrapper (line by line)."""
    for line in ascii_safe(text).splitlines():
        # Use width=0 to span remaining width of the page
        pdf.multi_cell(0, 6, line)


# -----------------------------
# Font handling
# -----------------------------
def _pick_font(pdf: FPDF) -> str:
    """
    Prefer Arial/DejaVu if available as TTF; otherwise fall back to Helvetica.
    Place your TTF in ./fonts/Arial.ttf or ./fonts/DejaVuSans.ttf
    """
    fonts_dir = Path("fonts")
    arial_ttf = fonts_dir / "Arial.ttf"
    dejavu_ttf = fonts_dir / "DejaVuSans.ttf"

    try:
        if arial_ttf.exists():
            pdf.add_font("Arial", "", str(arial_ttf), uni=True)
            pdf.add_font("Arial", "B", str(arial_ttf), uni=True)  # Bold maps to same TTF; FPDF handles style
            return "Arial"
        if dejavu_ttf.exists():
            pdf.add_font("DejaVu", "", str(dejavu_ttf), uni=True)
            pdf.add_font("DejaVu", "B", str(dejavu_ttf), uni=True)
            return "DejaVu"
    except Exception:
        # If font registration fails, just fall through to Helvetica
        pass

    return "helvetica"  # core font, latin-1 only


# -----------------------------
# PDF implementation
# -----------------------------
class _PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Decide font family once per document
        self._family = _pick_font(self)

    def header(self):
        self.set_font(self._family, "B", 12)
        self.cell(0, 8, ascii_safe("IC-LicAI Advisory Report"), ln=1, align="L")
        self.set_font(self._family, "", 9)
        self.cell(0, 6, ascii_safe("Generated " + datetime.utcnow().isoformat() + "Z"), ln=1, align="L")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font(self._family, "", 8)
        self.cell(0, 8, ascii_safe("FRAND-ready advisory. For internal use."), align="C")


def export_pdf(bundle: dict) -> bytes:
    """
    Build a concise licensing-focused PDF from the bundle.
    Expected keys:
      - case (str)
      - narrative (str)
      - guide (dict)
      - assessment.ic_map (dict[str, list])
    """
    case = ascii_safe(bundle.get("case", "Untitled Case"))
    narrative = ascii_safe(bundle.get("narrative", ""))
    guide = bundle.get("guide", {}) or {}
    assessment = bundle.get("assessment", {}) or {}
    ic_map = assessment.get("ic_map", {}) if isinstance(assessment.get("ic_map", {}), dict) else {}

    pdf = _PDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font(pdf._family, "", 11)

    # Title
    pdf.set_font(pdf._family, "B", 14)
    _wrap_lines(pdf, "Case: " + case)
    pdf.ln(2)

    # Narrative
    if narrative:
        pdf.set_font(pdf._family, "B", 12)
        _wrap_lines(pdf, "Licensing Advisory")
        pdf.set_font(pdf._family, "", 11)
        _wrap_lines(pdf, narrative)
        pdf.ln(2)

    # Expert checklist snapshot
    pdf.set_font(pdf._family, "B", 12)
    _wrap_lines(pdf, "Expert Checklist Snapshot")
    pdf.set_font(pdf._family, "", 11)
    for k in ["lic_intent", "assets_identified", "esg_confirmed", "contracts_reviewed", "governance_ok", "valuation_understood"]:
        v = guide.get(k, "")
        _wrap_lines(pdf, "- " + k.replace("_", " ").title() + ": " + str(v))
    pdf.ln(2)

    # IC Map summary
    if ic_map:
        pdf.set_font(pdf._family, "B", 12)
        _wrap_lines(pdf, "IC Map Snapshot")
        pdf.set_font(pdf._family, "", 11)
        for leaf, items in ic_map.items():
            try:
                count = len(items) if items is not None else 0
            except Exception:
                count = 0
            _wrap_lines(pdf, f"- {leaf}: {count}")
        pdf.ln(2)

    out = pdf.output(dest="S")
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    # Fallback: latin-1 encode
    return out.encode("latin-1", "ignore")


# -----------------------------
# XLSX / CSV implementation
# -----------------------------
def export_xlsx(bundle: dict) -> bytes:
    """
    Produce XLSX if pandas/xlsxwriter available; otherwise return CSV bytes.
    """
    if pd is None:
        # Minimal CSV fallback containing a few top-level fields
        rows = [
            ("case", ascii_safe(bundle.get("case", ""))),
            ("licence_choice", ascii_safe(bundle.get("licence_choice", ""))),
            ("sector", ascii_safe(bundle.get("sector", ""))),
            ("company_size", ascii_safe(bundle.get("company_size", ""))),
        ]
        body = "key,value\n" + "\n".join([k + "," + v.replace(",", ";") for k, v in rows]) + "\n"
        return body.encode("utf-8")

    bio = io.BytesIO()
    try:
        with pd.ExcelWriter(bio, engine="xlsxwriter") as xw:
            # Summary
            df_sum = pd.DataFrame([
                {"Field": "Case", "Value": bundle.get("case", "")},
                {"Field": "Licence Choice", "Value": bundle.get("licence_choice", "")},
                {"Field": "Sector", "Value": bundle.get("sector", "")},
                {"Field": "Company Size", "Value": bundle.get("company_size", "")},
            ])
            df_sum.to_excel(xw, index=False, sheet_name="Summary")

            # Narrative
            df_nav = pd.DataFrame([{"Narrative": bundle.get("narrative", "")}])
            df_nav.to_excel(xw, index=False, sheet_name="Narrative")

            # Guide flags
            guide = bundle.get("guide", {}) or {}
            df_g = pd.DataFrame(list(guide.items()), columns=["Key", "Value"])
            df_g.to_excel(xw, index=False, sheet_name="Guide")

            # IC Map counts
            assess = bundle.get("assessment", {}) or {}
            ic_map = assess.get("ic_map", {}) if isinstance(assess.get("ic_map", {}), dict) else {}
            rows = []
            for leaf, items in ic_map.items():
                try:
                    rows.append({"Leaf": str(leaf), "Count": int(len(items)) if items is not None else 0})
                except Exception:
                    rows.append({"Leaf": str(leaf), "Count": 0})
            pd.DataFrame(rows).to_excel(xw, index=False, sheet_name="IC_Map")
    except Exception:
        # Hard fallback to CSV if anything xlsx-related fails
        body = "key,value\ncase," + ascii_safe(bundle.get("case", "")) + "\n"
        return body.encode("utf-8")

    return bio.getvalue()


# -----------------------------
# JSON implementation
# -----------------------------
def export_json(bundle: dict) -> bytes:
    txt = json.dumps(bundle, ensure_ascii=False, default=str, indent=2)
    return txt.encode("utf-8")
