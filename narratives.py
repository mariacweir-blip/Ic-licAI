# narratives.py (clean ASCII-only version)
from typing import Dict, Any, List

def _bullet_lines(items: List[str], prefix: str = "- "):
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
        readiness_lines.append(f"Step {step}: {name} - Score {score}/3")
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

    text = f"""# {case} - Intangible Capital & Licensing Advisory (Demo)

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
    return text.replace("–", "-").replace("—", "-").replace("’", "'")

def build_narrative_profiled(case: str,
                             ic_map: Dict[str, List[str]],
                             readiness: List[Dict[str, Any]],
                             licensing: List[Dict[str, Any]],
                             profile: Dict[str, str] | None = None) -> Dict[str, str]:
    p = profile or {}
    size = str(p.get("size", "micro")).lower()

    def _asc(s: str) -> str:
        return (s or "").encode("latin-1", "ignore").decode("latin-1")

    assets_total = sum(len(v) for v in ic_map.values()) if isinstance(ic_map, dict) else 0

    if size == "micro":
        exec_note = (
            f"{case} is a Micro-SME (1-10 staff). Priority is quick, low-admin packaging of know-how "
            "into simple, licence-ready bundles with a short path to first revenue. Evidence capture and "
            "lightweight governance are kept practical (owner sign-off, basic register, rate card)."
        )
        plan_90 = (
            "W1-2: Snapshot evidence (brand guides, methods/recipes, training notes). Create a one-page IA register.\n"
            "W3-4: Apply the 10-Steps at a micro scale (identify, separate, protect, safeguard, manage, control). "
            "Define one productised offer (template + checklist + brief demo).\n"
            "W5-6: Prepare FRAND-aligned micro templates: simple territory/field-of-use, fixed fee or low royalty, "
            "clear audit and termination. Publish a short rate card.\n"
            "W7-8: Pilot with 1-2 friendly customers/partners. Capture outcomes and testimonials.\n"
            "W9-12: Close first licences; set renewal dates; maintain a monthly evidence snapshot."
        )
        frand = (
            "1) Fixed-fee Starter Licence (micro): flat fee per 6-12 months; uniform terms; audit on request.\n"
            "2) Simple Royalty Licence: 2.0% of net sales with an annual cap; MFN across equivalent micro licensees.\n"
            "3) Evaluation-to-Commercial path: 60-day evaluation at nominal fee; pre-agreed conversion price corridor."
        )
        governance = (
            "Owner/IC Lead approves each asset entry in a simple register (origin, owner, proof). "
            "One-page governance note, monthly review slot, renewal diary in calendar."
        )
    elif size == "small":
        exec_note = (
            f"{case} is a Small enterprise (11-50 staff). Focus on documenting repeatable methods and roles, "
            "and introducing light approvals for licence deals."
        )
        plan_90 = (
            "W1-2: Expand IA register with owners and repositories; W3-4: 10-Steps playbook; "
            "W5-6: FRAND templates with rate bands; W7-8: Pilot bundle; W9-12: First licences and board sign-off."
        )
        frand = (
            "1) Tiered Royalty (2.0-3.0% by volume),\n2) Field-of-use splits by channel,\n3) Service-plus-Licence hybrid."
        )
        governance = "IC Lead and monthly IC board; contract checklist; renewal workflow."
    else:
        exec_note = (
            f"{case}: profile not specified - applying generic advisory narrative aligned to 4-Leaf/10-Steps/FRAND."
        )
        plan_90 = (
            "W1-2 evidence; W3-4 10-Steps; W5-6 FRAND templates; W7-8 pilot; W9-12 close and governance."
        )
        frand = (
            "1) Grant-back limited to field;\n2) Field-of-use tiers;\n3) Usage credits with audit log."
        )
        governance = "Appoint IC Lead; monthly review; IA register with evidence links and renewal diary."

    executive = (
        f"{exec_note} Currently mapped assets: {assets_total} across the Four-Leaf Model. "
        "Focus is converting tacit to explicit artefacts, capturing evidence, and publishing uniform terms."
    )

    return {
        "executive": _asc(executive),
        "plan_90": _asc(plan_90),
        "frand": _asc(frand),
        "governance": _asc(governance),
    }
