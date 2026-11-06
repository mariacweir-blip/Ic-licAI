# IC‑LicAI Demo (Streamlit + Exports)

**Goal:** A working prototype to upload evidence, run a lightweight IC analysis, and export a **full advisory‑style PDF** plus XLSX + JSON.

This repo is **neutral EU‑style**, iPad‑friendly, and uses a **demo password**: `ICdemo2025!`

---

## 1) Run Locally (fastest)
```bash
# 1. Create a virtual env (recommended)
python3 -m venv .venv && source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

# 2. Install deps
pip install -r requirements.txt

# 3. Launch Streamlit
streamlit run streamlit_app.py
```

Open the given URL in your browser. Enter the password when prompted.

---

## 2) Deploy to Streamlit Cloud (for iPad demo)
1. Push these files to a **GitHub repo**.
2. In Streamlit Cloud, **create an app** from the repo. Entry point = `streamlit_app.py`.
3. Add a secrets file if you want to **change the password** (optional).
4. Open the app URL on your iPad and sign in with the password.

**Tip:** Keep a couple of example PDFs ready in iPad Files for upload.

---

## 3) Use with Google Colab (optional backend)
For the Nov demo we run **all in Streamlit** (simpler and more stable).  
If you still want Colab as a backend later:

- Expose a simple API endpoint from Colab using **FastAPI + ngrok** (or **Gradio**).
- Modify `app.py` to `requests.post()` to that endpoint, passing uploaded file bytes + notes.
- Use the response to populate `bundle` before export.

**We can wire that after the demo window.**

---

## 4) Where to replace demo logic with your engines
- `ic_licai/processing.py` → replace `draft_ic_assessment()` with your **4‑Leaf**, **10‑Steps**, **IAS 38**, **FRAND** logic.
- `ic_licai/exporters.py` → customise the PDF & XLSX outputs.
- Streamlit UI in `app_clean.py` (loaded by `streamlit_app.py`) → add roles, audit, governance, etc.

## Market Growth workspace

The **Market Growth** page provides an evidence-led workspace for:

- target customers, geographies, market need and routes to market;
- TAM, SAM and SOM consistency checks;
- compound annual growth (CAGR) calculation;
- competitor, pricing, customer and partner evidence;
- a transparent evidence-completeness indicator;
- licensing implications for professional review; and
- an editable Market Growth report included in **Reports & Exports**.

Market figures are explicitly labelled as sourced evidence, mixed evidence,
internal estimates or unverified assumptions. The tool does not independently
verify the evidence or treat market opportunity as proof of licence readiness.

---

## 5) Password
Default password is **ICdemo2025!** (hardcoded in `app.py` for demo).  
To change later, replace the string or move to Streamlit secrets.

---

## 6) Demo Cases
Three scenarios are preconfigured: **VoltEdge** (GreenTech), **Capabilis** (Capability Licensing OS), **EuraLab** (University TTO).  
Adjust content in `ic_licai/sample_content.json`.

---

## 7) Known limitations (by design for speed)
- No long‑running AI calls; demo heuristics used.
- PDF uses ReportLab for speed; replace with your house style later.
- No database; session memory only.
- No logo/branding per your instruction.

---

## 8) Next steps (post‑demo hardening)
- Role‑based auth, audit logs
- Real engine integration + valuation layer
- ARICC subdomain + SSL + secrets
- Word export (python-docx templates)
- Add fallback cache for “offline‑ish” safe demo
