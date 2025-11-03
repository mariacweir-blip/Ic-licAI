from typing import List, Dict, Any, Tuple
import io
from PyPDF2 import PdfReader

FOUR_LEAVES = ["Human Capital","Structural Capital","Customer Capital","Strategic Alliance Capital"]

def parse_uploaded_files(files: List[Tuple[str, bytes]]) -> Dict[str, Any]:
    """Light parser: extracts text from PDFs and captures filenames for other docs."""
    texts, meta = [], []
    for name, content in files:
        n = name.lower()
        if n.endswith(".pdf"):
            try:
                reader = PdfReader(io.BytesIO(content))
                pages = []
                for p in reader.pages[:5]:
                    pages.append(p.extract_text() or "")
                texts.append("\n".join(pages))
                meta.append({"file": name, "type":"pdf", "pages": len(reader.pages)})
            except Exception as e:
                texts.append(f"[PDF read error: {e}]")
                meta.append({"file": name, "type":"pdf", "pages": 0})
        else:
            try:
                texts.append(content.decode("utf-8", errors="ignore"))
            except Exception:
                texts.append(f"[Unsupported file for preview: {name}]")
            meta.append({"file": name, "type":"doc"})
    return {"texts": texts, "meta": meta}

def draft_ic_assessment(notes: str) -> Dict[str, Any]:
    """Placeholder IC map + 10-steps + licensing menu from notes."""
    tacit = ("process" in notes.lower()) or ("know-how" in notes.lower())
    explicit = any(w in notes.lower() for w in ["patent","trademark","contract"])
    ic_map = {
        "Human Capital": ["Subject-matter expertise","Training IP","Tacit routines"],
        "Structural Capital": ["SOPs & methods","Software/data assets","Brand elements"],
        "Customer Capital": ["Pilot contracts","Cohorts, CRMs","Service playbooks"],
        "Strategic Alliance Capital": ["MOUs/JVs","University/industry ties","Platform rules"]
    }
    readiness = [
        {"step":1,"name":"Identify","score":2,"tasks":["Complete artefact inventory","Tag leaf & tacit/explicit"]},
        {"step":2,"name":"Separate","score":1,"tasks":["Define asset boundaries","Create asset sheets"]},
        {"step":3,"name":"Protect","score":1 if explicit else 0,"tasks":["Rights review","NDA/access controls"]},
        {"step":4,"name":"Safeguard","score":1,"tasks":["Backups/continuity","Key-person cover"]},
        {"step":5,"name":"Manage","score":1,"tasks":["RACI & KPIs","Change control"]},
        {"step":6,"name":"Control","score":1,"tasks":["Access policy","Monitoring"]},
        {"step":7,"name":"License Strategy","score":1,"tasks":["Select models","Define constraints"]},
        {"step":8,"name":"Valuation (IAS 38)","score":0,"tasks":["Choose method","Collect inputs"]},
        {"step":9,"name":"Commercialisation","score":1,"tasks":["Channels/SLAs","Rollout"]},
        {"step":10,"name":"Governance & Audit","score":1,"tasks":["Board reporting","Re-rate schedule"]}
    ]
    licensing = [
        {"model":"Traditional IP license","notes":"Exclusive / non-exclusive; field-of-use; territory"},
        {"model":"Capability license","notes":"Method + training + certification + audit"},
        {"model":"Impact-linked license","notes":"Royalty linked to verified ESG KPIs"},
        {"model":"Consortium / pool","notes":"FRAND-aligned access, rate card, dispute resolution"}
    ]
    return {"ic_map": ic_map, "readiness": readiness, "licensing": licensing, "flags":{"tacit": tacit, "explicit": explicit}}
