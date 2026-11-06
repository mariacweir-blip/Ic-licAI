"""Innovation-capacity assessment and reporting for IC-LicAI.

The functions are independent of Streamlit so scoring can be tested and the
method can be reused in exports.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


DIMENSIONS: Dict[str, Dict[str, str]] = {
    "strategy": {
        "label": "Innovation strategy",
        "prompt": "Clear priorities, customer problems, portfolio choices and a route from ideas to value.",
    },
    "leadership": {
        "label": "Leadership & culture",
        "prompt": "Leadership sponsorship, psychological safety, learning behaviours and ownership of decisions.",
    },
    "people": {
        "label": "People & skills",
        "prompt": "Relevant technical, commercial and delivery skills, with time and development plans.",
    },
    "knowledge": {
        "label": "Knowledge, data & IP",
        "prompt": "Knowledge capture, evidence use, data quality, IP awareness and access controls.",
    },
    "process": {
        "label": "Process & portfolio",
        "prompt": "Repeatable discovery, experimentation, selection, development and stop/go decisions.",
    },
    "partnerships": {
        "label": "Partnerships & market learning",
        "prompt": "Customer discovery, external collaboration and rapid use of market feedback.",
    },
    "resources": {
        "label": "Resources & funding",
        "prompt": "Budget, facilities, tools, capacity and funding matched to the innovation portfolio.",
    },
    "measurement": {
        "label": "Measurement & governance",
        "prompt": "Decision rights, risk management, learning metrics, benefits tracking and board visibility.",
    },
}

MATURITY_LABELS = {
    0: "Not present",
    1: "Ad hoc",
    2: "Developing",
    3: "Repeatable",
    4: "Embedded and improving",
}

EVIDENCE_LABELS = {
    0: "No evidence",
    1: "Claimed or anecdotal",
    2: "Documented",
    3: "Independently verified or consistently measured",
}


def _bounded_int(value: Any, low: int, high: int) -> int:
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return low


def capacity_metrics(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return dimension scores, overall maturity and evidence confidence."""
    source = data.get("dimensions") or {}
    rows: List[Dict[str, Any]] = []
    for key, meta in DIMENSIONS.items():
        row = source.get(key) or {}
        maturity = _bounded_int(row.get("maturity"), 0, 4)
        evidence = _bounded_int(row.get("evidence"), 0, 3)
        score = round((maturity / 4.0) * 75.0 + (evidence / 3.0) * 25.0, 1)
        rows.append(
            {
                "key": key,
                "label": meta["label"],
                "maturity": maturity,
                "maturity_label": MATURITY_LABELS[maturity],
                "evidence": evidence,
                "evidence_label": EVIDENCE_LABELS[evidence],
                "notes": str(row.get("notes") or "").strip(),
                "score": score,
            }
        )

    overall = round(sum(row["score"] for row in rows) / len(rows), 1)
    confidence = round(sum(row["evidence"] for row in rows) / (3.0 * len(rows)) * 100.0)
    if overall >= 75:
        band = "Scaling capacity"
    elif overall >= 55:
        band = "Established but uneven"
    elif overall >= 35:
        band = "Developing capacity"
    else:
        band = "Early or fragile capacity"

    ranked = sorted(rows, key=lambda row: (row["score"], row["label"]))
    priorities = ranked[:3]
    strengths = list(reversed(ranked[-3:]))
    warnings = []
    if confidence < 45:
        warnings.append("The assessment relies heavily on claims or missing evidence.")
    if any(not row["notes"] for row in rows):
        warnings.append("Add concise evidence notes to every dimension for a traceable review.")
    if max(row["score"] for row in rows) - min(row["score"] for row in rows) >= 35:
        warnings.append("Capacity is uneven; strong areas may be constrained by the weakest dimensions.")

    return {
        "rows": rows,
        "overall": overall,
        "confidence": confidence,
        "band": band,
        "priorities": priorities,
        "strengths": strengths,
        "warnings": warnings,
    }


def build_innovation_capacity_report(
    data: Dict[str, Any], case_name: str, sector: str
) -> Tuple[str, str]:
    metrics = capacity_metrics(data)
    title = f"Innovation Capacity Report — {case_name or 'Untitled Company'}"
    body: List[str] = [
        "Executive Summary",
        f"Organisation: {case_name or 'Untitled Company'}",
        f"Sector: {sector or 'Other'}",
        f"Overall innovation-capacity score: {metrics['overall']}/100 — {metrics['band']}",
        f"Evidence confidence: {metrics['confidence']}/100",
        "",
        "Dimension Assessment",
    ]
    for row in metrics["rows"]:
        note = row["notes"] or "No evidence note recorded."
        body.append(
            f"- {row['label']}: {row['score']}/100; maturity {row['maturity']}/4 "
            f"({row['maturity_label']}); evidence {row['evidence']}/3 "
            f"({row['evidence_label']}). {note}"
        )

    body.extend(["", "Strongest Capacity Signals"])
    for row in metrics["strengths"]:
        body.append(f"- {row['label']}: {row['score']}/100")

    body.extend(["", "Priority Capacity Gaps"])
    for row in metrics["priorities"]:
        body.append(
            f"- {row['label']}: {row['score']}/100. Strengthen the practice, assign an owner, "
            "and add dated evidence of consistent use."
        )

    body.extend(["", "90-Day Action Plan"])
    for number, row in enumerate(metrics["priorities"], 1):
        body.append(
            f"{number}. {row['label']}: define one repeatable practice, one accountable owner, "
            "one measurable outcome and one evidence artefact."
        )

    if data.get("evidence_file_names"):
        body.extend(["", "Evidence Files"])
        body.extend(f"- {name}" for name in data["evidence_file_names"])

    if metrics["warnings"]:
        body.extend(["", "Limitations"])
        body.extend(f"- {warning}" for warning in metrics["warnings"])

    body.extend(
        [
            "",
            "Method Note",
            "Each dimension combines a self-assessed maturity level (75% of the score) and evidence strength "
            "(25%). The result is a structured discussion aid, not an audit, certification or prediction of success.",
            "",
            "Disclaimer",
            "Advisory only. Scores should be reviewed with the organisation and tested against dated evidence.",
        ]
    )
    return title, "\n".join(body)
