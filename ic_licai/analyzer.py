# ic_licai/analyzer.py — lightweight IC/ESG/market text analyzer

import re
from collections import defaultdict

# --- keyword banks ---
FOUR_LEAF = {
    "human": ["skills", "training", "talent", "culture", "knowledge", "competence"],
    "structural": ["software", "process", "system", "method", "database", "ip", "manual"],
    "customer": ["client", "customer", "brand", "contract", "reputation", "service"],
    "strategic": ["partner", "alliance", "joint", "agreement", "licence", "collaboration"],
}

TEN_STEPS = [
    "identify", "separate", "protect", "safeguard", "manage",
    "control", "evidence", "governance", "monetise", "reassess"
]

MARKET_CUES = ["market", "growth", "demand", "innovation", "tech", "competition", "pricing"]


def analyze_text(text: str) -> dict:
    """Simple keyword grouping into Four-Leaf + 10-Steps + market cues."""
    results = defaultdict(list)
    lower = text.lower()

    # --- 4-Leaf grouping ---
    for leaf, kws in FOUR_LEAF.items():
        for k in kws:
            if k in lower:
                snippet = _extract_sentence(lower, k)
                results[f"4leaf_{leaf}"].append(snippet)

    # --- 10-Steps grouping ---
    for step in TEN_STEPS:
        if step in lower:
            snippet = _extract_sentence(lower, step)
            results[f"step_{step}"].append(snippet)

    # --- Market/Innovation cues ---
    for cue in MARKET_CUES:
        if cue in lower:
            snippet = _extract_sentence(lower, cue)
            results["market_innovation"].append(snippet)

    return dict(results)


def _extract_sentence(text: str, keyword: str, window: int = 100) -> str:
    """Return short snippet around a keyword."""
    idx = text.find(keyword)
    if idx == -1:
        return ""
    start = max(0, idx - window)
    end = min(len(text), idx + window)
    snippet = text[start:end]
    return re.sub(r"\s+", " ", snippet).strip()
