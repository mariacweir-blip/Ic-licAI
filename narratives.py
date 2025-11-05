# narratives.py  (clean, ASCII-safe)
from typing import Dict, Any, List

def _bullet_lines(items: List[str], prefix: str="- "):
    lines = []
    for it in (items or []):
        it = str(it).strip()
        if not it:
            continue
        it = it.replace("•", "-").replace("–", "-").replace("—", "-").replace("’", "'")
        lines.append(f"{prefix}{it}")
    return "\n".join(lines)

def render_basic_narrative(data: Dict[str, Any]) -> str:
    case = data.get("case", "Client")
    ic_map = data.get("ic_map", {})
    readiness = data.get("readiness", [])
    licensing = data.get("licensing", [])
    evidence = data.get("evidence", [])

    def pick(leaf):
        items = ic_map.get(leaf, [])
        return "\n".join([f"- {x}" for x in items[:6]]) if items else "- (to be captured)"

    human = pick("Human Capital")
    structural = pick("Structural Capital")
    customer = pick("Customer Capital")
    strategic = pick("Strategic Alliance Capital")

    readiness_lines = []
    for row in readiness:
        step = row.get("step")
        name = row.get("name", "")
        score = row.get("score", 0)
        tasks = row.get("tasks", [])[:4]
        readiness_lines.append(f"Step {step}: {name} — Score {score}/3")
        for t in tasks:
            readiness_lines.append(f"- {t}")
    readiness_block = "\n".join(readiness_lines) if readiness_lines else "(readiness tasks will be listed here)"

    licensing_lines = []
    for opt in licensing[:3]:
        model = opt.get("model", "Model")
        notes = opt.get("notes", "")
        licensing_lines.append(f"{model}\n{notes}")
    licensing_block = "\n\n".join(licensing_lines) if licensing_lines else "(licensing options will appear here)"

    evidence_block = _bullet_lines(evidence[:8])

    text = f"""# {case} — Intangible Capital & Licensing Advisory (Demo)

Executive Summary
Initial licensing-forward assessment using the Four-Leaf Model and 10-Steps. Actions focus on licence-readiness under FRAND-aligned terms.

Intangible Capital Overview (Four-Leaf)
Human Capital
{human}

Structural Capital
{structural}

Customer Capital
{customer}

Strategic Alliance Capital
{strategic}

10-Steps Readiness (Summary)
{readiness_block}

FRAND-Aligned Licensing Examples
- Capability Licence: per-practitioner tiers with clear enablement.
- Knowledge-as-a-Service Licence: playbooks and templates with renewal tied to usage.
- Strategic Deployment Licence: onboarding fee + revenue share with uniform obligations.

Defensible Licensing Strategy (Demo)
- Convert tacit know-how to explicit modules; set ownership and boundaries.
- Publish transparent pricing tiers (SME / Enterprise / Partner).
- Implement monitoring/renewal controls; partner enablement packs.

Evidence Extracts (for audit trail)
{evidence_block or "- (add snippets by uploading evidence)"}
"""
    return text.replace("-", "-").replace("–", "-").replace("—", "-").replace("’", "'")

def build_narrative(case: str, ic_map: Dict[str, List[str]], readiness: List[Dict[str, Any]], licensing: List[Dict[str, Any]]) -> Dict[str, str]:
    """Expanded advisory narrative for IC-LicAI demo (ASCII-safe)."""
    assets_total = sum(len(v) for v in ic_map.values()) if isinstance(ic_map, dict) else 0

    executive = (
        f"{case} holds {assets_total} mapped intangible items across the Four-Leaf Model. "
        "Licensing readiness is emerging. Immediate focus: convert tacit into explicit artefacts, "
        "capture evidence, and prepare FRAND-aligned terms (field-of-use, territory, royalty base, audit)."
    )

    plan_90 = (
        "W1–2: Evidence intake; IA register with owner/source/evidence/next step.\n"
        "W3–4: Apply 10-Steps: identify, separate, protect, safeguard, manage, control.\n"
        "W5–6: Draft FRAND templates (price corridor, MFN, audit, termination, renewal cadence).\n"
        "W7–8: Package one licence-ready bundle; select 2–3 pilot licensees with success metrics.\n"
        "W9–12: Close pilots; governance log and renewal diary; publish rate card and decision log."
    )

    frand = (
        "1) Grant-back limited to licensed field; 2–3% royalty benchmark; SME discount tier.\n"
        "2) Field-of-use split: healthcare 2.2% tier; adjacent fields +1.0% uplift; MFN within tier; annual cap.\n"
        "3) Usage credits: prepaid blocks; intra-group transfer permitted; floor price and audit log."
    )

    governance = (
        "Nominate IC Lead; monthly IC Board; all licences recorded in IA register with evidence links and versions; "
        "risk table per asset; renewal cadence and compliance checkpoints."
    )

    # Ensure ASCII compatibility for FPDF
    def _asc(s: str) -> str:
        return (s or "").encode("latin-1", "ignore").decode("latin-1")

    return {
        "executive": _asc(executive),
        "plan_90": _asc(plan_90),
        "frand": _asc(frand),
        "governance": _asc(governance),
    }

    def build_narrative_sandy(case: str, ic_map, readiness, licensing):
    """Case-specific narrative tuned for the 'Sandy Beach' demo."""
    assets_total = sum(len(v) for v in ic_map.values()) if isinstance(ic_map, dict) else 0

    executive = (
        f"{case} combines strong brand identity, proprietary formulations, and coastal-origin know-how "
        f"with {assets_total} mapped intangible assets.  The company’s market position rests on "
        "protected recipes, training content, and long-term distributor relationships.  "
        "Licensing readiness is high in Human and Customer Capital; the next milestone is "
        "formalising product and training bundles for franchise-style or co-brand licences."
    )

    plan_90 = (
        "W1–2: Consolidate evidence for recipes, training modules, and brand guidelines.  "
        "Tag each asset to owner, origin, and verification record.\n"
        "W3–4: Apply 10-Steps discipline to document explicit processes (mixing, packaging, training).  "
        "Protect trade-secret elements under NDAs.\n"
        "W5–6: Draft FRAND-aligned partner and franchise licence templates: "
        "territory, audit rights, brand-use, environmental standards.\n"
        "W7–8: Build a pilot bundle — 'Sandy Beach At Home' or 'Beach Essentials' — "
        "with product, training, and brand pack.  Select 2 pilot licensees.\n"
        "W9–12: Evaluate pilots; set price corridor and renewal cadence; "
        "issue investor briefing on intangible-asset-driven scalability."
    )

    frand = (
        "1) Brand + Recipe Licence: royalty 3 % of net sales; grant-back limited to quality improvements.\n"
        "2) Training and Certification Licence: annual per-trainer fee; uniform conditions; audit right.\n"
        "3) Co-Brand Distribution Licence: blended royalty 1.5 % plus regional marketing contribution; "
        "MFN across equivalent partners."
    )

    governance = (
        "IC Lead to chair monthly Brand & IP Board.  "
        "Each franchise or partner licence recorded in the IA register with evidence links, "
        "expiry, and audit schedule.  "
        "Quarterly review ensures compliance with sustainability, quality, and customer-experience metrics."
    )

    def _asc(s: str) -> str:
        return (s or "").encode("latin-1", "ignore").decode("latin-1")

    return {
        "executive": _asc(executive),
        "plan_90": _asc(plan_90),
        "frand": _asc(frand),
        "governance": _asc(governance),
    }
