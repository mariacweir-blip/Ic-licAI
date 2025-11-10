# ic_licai/importers.py — multi-format evidence importer for IC-LicAI
import os
from io import BytesIO
from pathlib import Path
import zipfile
import csv
import json

from docx import Document
from PyPDF2 import PdfReader

def extract_text_from_file(upload) -> str:
    """Return plain text from an uploaded evidence file."""
    name = upload.name.lower()
    data = upload.getvalue()

    try:
        # --- WhatsApp exports (.txt)
        if name.endswith(".txt"):
            return data.decode("utf-8", errors="ignore")

        # --- Word docs
        elif name.endswith(".docx"):
            bio = BytesIO(data)
            doc = Document(bio)
            return "\n".join(p.text for p in doc.paragraphs)

        # --- PDFs
        elif name.endswith(".pdf"):
            bio = BytesIO(data)
            reader = PdfReader(bio)
            return "\n".join(page.extract_text() or "" for page in reader.pages)

        # --- CSV or XLS-like
        elif name.endswith(".csv"):
            text = data.decode("utf-8", errors="ignore")
            rows = [", ".join(row) for row in csv.reader(text.splitlines())]
            return "\n".join(rows)

        # --- JSON (e.g. chat export)
        elif name.endswith(".json"):
            js = json.loads(data.decode("utf-8", errors="ignore"))
            return json.dumps(js, indent=2)

        # --- Zip archives (just list contents)
        elif name.endswith(".zip"):
            bio = BytesIO(data)
            with zipfile.ZipFile(bio) as z:
                names = z.namelist()
                return f"ZIP archive contains: {', '.join(names[:10])}"

        else:
            return f"[Unsupported file type: {name}]"

    except Exception as e:
        return f"[Error reading {name}: {e}]"


def combine_uploads(uploads) -> str:
    """Combine text from multiple uploads."""
    combined = []
    for f in uploads:
        combined.append(f"==== {f.name} ====")
        combined.append(extract_text_from_file(f))
    return "\n\n".join(combined)
