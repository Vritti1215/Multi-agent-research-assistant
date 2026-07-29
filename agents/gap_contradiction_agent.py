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

1. CONTRADICTIONS: cases where sources disagree, report conflicting
   numbers, or reach different conclusions — including SUBTLE
   disagreements (e.g. one source reports a technique works well and
   another reports limitations with it, even if they don't explicitly
   argue against each other). For each, give a brief possible reason if
   inferable (different datasets, metrics, sample sizes, time periods,
   assumptions, etc.). Don't force contradictions that aren't really
   there, but do look beyond only direct, explicit disagreements.
2. RESEARCH GAPS: specific, concrete gaps in what these sources cover —
   things the sources collectively do NOT address, evaluate, or agree
   on. Not generic statements like "more research is needed" — name the
   actual missing piece (e.g. "no source evaluates this technique on
   datasets larger than 10k samples").

Respond ONLY with JSON in exactly this shape, no markdown fences, no
preamble text before or after the JSON:
{{"contradictions": [{{"claim_a": "...", "claim_b": "...", "possible_reason": "..."}}], "gaps": ["...", "..."]}}

If there are genuinely no contradictions after looking carefully, return
an empty list for it — don't invent ones. Aim for 2-5 gaps if the
material supports that many.

VALIDATED CLAIMS:
{claims_block}

FULL ANALYSIS:
{state['analysis']}"""

    try:
        raw = call_llm(prompt, max_tokens=1500)
    except Exception as e:
        # This step (contradictions/gaps) is a nice-to-have, not core to
        # the report. A transient network blip or API hiccup here
        # shouldn't take down the whole /research request — degrade to
        # "none found" instead of crashing.
        print(f"[gap_contradiction_agent] LLM call failed, continuing without contradictions/gaps: {e}")
        return {"contradictions": [], "gaps": []}

    contradictions, gaps = _parse_json_response(raw)

    return {"contradictions": contradictions, "gaps": gaps}


def _parse_json_response(raw: str) -> tuple[list, list]:
    """Models sometimes wrap JSON in markdown fences or add a sentence of
    preamble before it, which breaks a naive json.loads and was silently
    producing empty contradictions/gaps every time. This tries a direct
    parse first, then falls back to extracting the first {...} block."""
    cleaned = raw.strip().strip("`")
    if cleaned.startswith("json"):
        cleaned = cleaned[4:].strip()

    try:
        parsed = json.loads(cleaned)
        return parsed.get("contradictions", []), parsed.get("gaps", [])
    except json.JSONDecodeError:
        pass

    # Fallback: grab everything between the first "{" and the last "}"
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(raw[start:end + 1])
            return parsed.get("contradictions", []), parsed.get("gaps", [])
        except json.JSONDecodeError:
            pass

    return [], []
