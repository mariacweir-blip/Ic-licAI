"""Evidence-led market growth calculations for IC-LicAI.

The functions in this module are deliberately independent of Streamlit so the
calculation and reporting logic can be tested without starting the application.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple


EVIDENCE_LABELS = {
    "dated_sources": "Dated third-party market sources",
    "customer_validation": "Customer interviews, pilots or purchase evidence",
    "competitor_evidence": "Competitor or alternative-solution evidence",
    "pricing_evidence": "Pricing, revenue or willingness-to-pay evidence",
    "partner_evidence": "Channel or strategic-partner evidence",
}


def non_negative_number(value: Any) -> float:
    """Return a non-negative float, treating missing or invalid values as zero."""
    try:
        return max(0.0, float(value or 0))
    except (TypeError, ValueError):
        return 0.0


def calculate_cagr(start_value: Any, end_value: Any, years: Any) -> Optional[float]:
    """Calculate compound annual growth as a percentage.

    ``None`` is returned when a meaningful calculation is not possible.
    """
    start = non_negative_number(start_value)
    end = non_negative_number(end_value)
    try:
        period = int(years)
    except (TypeError, ValueError):
        return None
    if start <= 0 or end <= 0 or period <= 0:
        return None
    return ((end / start) ** (1.0 / period) - 1.0) * 100.0


def validate_market_funnel(tam: Any, sam: Any, som: Any) -> List[str]:
    """Return plain-English warnings for inconsistent TAM/SAM/SOM values."""
    tam_value = non_negative_number(tam)
    sam_value = non_negative_number(sam)
    som_value = non_negative_number(som)
    warnings: List[str] = []
    if tam_value and sam_value > tam_value:
        warnings.append("SAM is greater than TAM; check the market definitions or figures.")
    if sam_value and som_value > sam_value:
        warnings.append("SOM is greater than SAM; check the obtainable-market assumptions.")
    if not tam_value and (sam_value or som_value):
        warnings.append("Add a TAM figure or explain why the wider market is not measurable.")
    if tam_value and not sam_value:
        warnings.append("SAM is missing, so the realistic serviceable market is not yet quantified.")
    if sam_value and not som_value:
        warnings.append("SOM is missing, so the near-term obtainable market is not yet quantified.")
    return warnings


def source_lines(source_text: Any) -> List[str]:
    """Split a source register into non-empty lines."""
    return [line.strip(" -\t") for line in str(source_text or "").splitlines() if line.strip(" -\t")]


def evidence_strength(data: Dict[str, Any]) -> Tuple[int, str, List[str]]:
    """Score evidence completeness, not market attractiveness.

    The score is transparent and intentionally conservative. It measures
    whether the user has supplied the evidence categories needed for a market
    discussion; it does not verify the truth of uploaded or entered material.
    """
    checks = set(data.get("evidence_checks") or [])
    sources = source_lines(data.get("sources"))
    score = 0
    present: List[str] = []

    for key, label in EVIDENCE_LABELS.items():
        if key in checks:
            score += 15
            present.append(label)

    if sources:
        score += 10
        present.append("At least one named source")
    if len(sources) >= 2:
        score += 10
        present.append("Two or more named sources")
    if str(data.get("assumptions") or "").strip():
        score += 5
        present.append("Assumptions and limitations recorded")

    score = min(100, score)
    if score >= 75:
        band = "GREEN — evidence base ready for professional review"
    elif score >= 45:
        band = "AMBER — useful evidence present, with gaps to address"
    else:
        band = "RED — insufficient evidence for a dependable market conclusion"
    return score, band, present


def market_metrics(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return calculated market metrics and validation warnings."""
    start_year = int(data.get("start_year") or 0)
    end_year = int(data.get("end_year") or 0)
    period = end_year - start_year
    start_value = non_negative_number(data.get("start_value"))
    end_value = non_negative_number(data.get("end_value"))
    tam = non_negative_number(data.get("tam"))
    sam = non_negative_number(data.get("sam"))
    som = non_negative_number(data.get("som"))
    cagr = calculate_cagr(start_value, end_value, period)
    evidence_score, evidence_band, evidence_present = evidence_strength(data)
    return {
        "start_value": start_value,
        "end_value": end_value,
        "period": period,
        "cagr": cagr,
        "tam": tam,
        "sam": sam,
        "som": som,
        "sam_share": (sam / tam * 100.0) if tam > 0 else None,
        "som_share": (som / sam * 100.0) if sam > 0 else None,
        "warnings": validate_market_funnel(tam, sam, som),
        "evidence_score": evidence_score,
        "evidence_band": evidence_band,
        "evidence_present": evidence_present,
    }


def _money(value: float, currency: str) -> str:
    label = (currency or "Currency").strip()
    return f"{label} {value:,.0f}"


def licensing_implications(data: Dict[str, Any], metrics: Dict[str, Any]) -> List[str]:
    """Build cautious licensing implications from the recorded market evidence."""
    implications: List[str] = []
    cagr = metrics.get("cagr")
    if cagr is not None and cagr >= 10:
        implications.append(
            "The recorded growth scenario is high-growth; test scalable territorial, field-of-use and partner-led licensing routes."
        )
    elif cagr is not None and cagr >= 3:
        implications.append(
            "The recorded growth scenario is moderate; prioritise segments with the clearest evidence and repeatable licence economics."
        )
    elif cagr is not None:
        implications.append(
            "The recorded growth scenario is limited; use tightly defined pilots and evidence milestones before wider licensing."
        )

    checks = set(data.get("evidence_checks") or [])
    if "partner_evidence" in checks:
        implications.append("Channel or partner evidence may support co-creation or partner-led market entry.")
    else:
        implications.append("Validate channel partners and route-to-market responsibilities before relying on partner-led licensing.")
    if "pricing_evidence" not in checks:
        implications.append("Test willingness to pay and licence pricing before treating the market figures as revenue potential.")
    if "customer_validation" not in checks:
        implications.append("Obtain customer validation before moving from market opportunity to a licensing recommendation.")
    implications.append("Confirm ownership, rights, capacity and legal terms separately; market demand alone does not establish licence readiness.")
    return implications


def build_market_growth_report(data: Dict[str, Any], case_name: str, sector: str) -> Tuple[str, str]:
    """Create the editable report body used by the Streamlit export workflow."""
    metrics = market_metrics(data)
    currency = str(data.get("currency") or "Currency")
    figure_status = str(data.get("figure_status") or "Not stated")
    title = f"Market Growth Report — {case_name or 'Untitled Company'}"
    lines: List[str] = [
        "1. Purpose and status\n",
        "This report structures the market evidence supplied for professional review. It separates sourced evidence, internal estimates and assumptions. It is not an independent market study or investment recommendation.",
        f"\nCompany / project: {case_name or 'Untitled Company'}",
        f"Sector: {sector or 'Other'}",
        f"Status of quantitative figures: {figure_status}",
        "\n2. Target market",
        f"- Customer segments: {data.get('customer_segments') or 'Not yet recorded'}",
        f"- Geography: {data.get('geography') or 'Not yet recorded'}",
        f"- Market need: {data.get('market_need') or 'Not yet recorded'}",
        f"- Routes to market: {data.get('routes_to_market') or 'Not yet recorded'}",
        f"- Strategic partners: {data.get('strategic_partners') or 'Not yet recorded'}",
        "\n3. Market size and growth",
        f"- Starting market value ({data.get('start_year') or 'year not set'}): {_money(metrics['start_value'], currency)}",
        f"- Projected market value ({data.get('end_year') or 'year not set'}): {_money(metrics['end_value'], currency)}",
        f"- Calculated CAGR: {metrics['cagr']:.1f}%" if metrics["cagr"] is not None else "- Calculated CAGR: Not available; add valid starting and ending figures and years.",
        f"- TAM: {_money(metrics['tam'], currency)}",
        f"- SAM: {_money(metrics['sam'], currency)}",
        f"- SOM: {_money(metrics['som'], currency)}",
        "\n4. Competition and differentiation",
        f"- Competitors / alternatives: {data.get('competitors') or 'Not yet recorded'}",
        f"- Differentiation: {data.get('differentiation') or 'Not yet recorded'}",
        "\n5. Evidence register",
    ]
    sources = source_lines(data.get("sources"))
    if sources:
        lines.extend(f"- {source}" for source in sources)
    else:
        lines.append("- No named sources recorded.")

    lines.extend(
        [
            f"\nEvidence completeness score: {metrics['evidence_score']}/100",
            f"Evidence band: {metrics['evidence_band']}",
            "This score measures whether evidence categories are present. It does not verify the evidence or predict commercial success.",
            "\n6. Assumptions, risks and gaps",
            f"- Assumptions / limitations: {data.get('assumptions') or 'Not yet recorded'}",
        ]
    )
    if metrics["warnings"]:
        lines.extend(f"- Data check: {warning}" for warning in metrics["warnings"])
    else:
        lines.append("- TAM, SAM and SOM pass the basic internal consistency check.")

    lines.append("\n7. Licensing implications")
    lines.extend(f"- {item}" for item in licensing_implications(data, metrics))
    lines.extend(
        [
            "\n8. Professional review required",
            "Before external use, a qualified professional should verify the sources, dates, definitions, calculations, customer evidence, competitive assumptions and licensing implications.",
            "\nDisclaimer",
            "Advisory decision support only. This report is not legal, financial, accounting, tax, market-research or investment advice.",
        ]
    )
    return title, "\n".join(lines)
