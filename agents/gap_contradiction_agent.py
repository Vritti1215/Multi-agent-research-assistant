import json
from tools.llm_client import call_llm


def gap_contradiction_node(state: dict) -> dict:
    """Single combined LLM call (contradictions + gaps together, not two
    separate calls) to conserve free-tier token budget. Runs once, after
    citation validation settles — not on every retry loop iteration."""
    claims_block = "\n".join(
        f"- {c['text']} (source: {c['source_paper_url']})"
        for c in state["validated_claims"]
    ) or "None validated."

    prompt = f"""Based on the analysis and validated claims below, identify:

1. CONTRADICTIONS: cases where sources disagree or reach conflicting
   conclusions. For each, give a brief possible reason if inferable
   (different datasets, metrics, sample sizes, time periods, etc.).
2. RESEARCH GAPS: specific, concrete gaps in what these sources cover —
   not generic statements like "more research is needed".

Respond ONLY with JSON in exactly this shape, no markdown fences:
{{"contradictions": [{{"claim_a": "...", "claim_b": "...", "possible_reason": "..."}}], "gaps": ["...", "..."]}}

If there are no clear contradictions, return an empty list for it. Aim
for 2-5 gaps if the material supports that many.

VALIDATED CLAIMS:
{claims_block}

FULL ANALYSIS:
{state['analysis']}"""

    raw = call_llm(prompt, max_tokens=1200).strip("`")
    if raw.startswith("json"):
        raw = raw[4:].strip()

    try:
        parsed = json.loads(raw)
        contradictions = parsed.get("contradictions", [])
        gaps = parsed.get("gaps", [])
    except json.JSONDecodeError:
        contradictions, gaps = [], []

    return {"contradictions": contradictions, "gaps": gaps}
