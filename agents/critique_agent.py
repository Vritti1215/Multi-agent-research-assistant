import json
from tools.llm_client import call_llm


def critique_node(state: dict) -> dict:
    """The Reflection pattern: critiques the finished report against the
    ORIGINAL question (not the sub-questions it was decomposed into), and
    decides what kind of fix is needed — a rewrite of the text, or
    genuinely missing evidence that needs another search pass. This is
    what makes the pipeline autonomous (Plan -> Act -> Write -> Critique
    -> Revise) rather than a one-shot generation."""
    prompt = f"""You are critiquing a research report against the ORIGINAL
question it was supposed to answer. Be a tough, honest critic — not a
rubber stamp. Most reports that cover the topic reasonably should PASS;
only flag real problems.

ORIGINAL QUESTION: {state['query']}

REPORT:
{state['final_report']}

Decide ONE verdict:
- "pass": the report genuinely and directly answers the original
  question with adequate depth and grounding.
- "revise": the underlying evidence is adequate, but the WRITING itself
  is unfocused, doesn't directly address the original question, is too
  shallow, or wanders off-topic. This needs a rewrite, not new evidence.
- "research_gap": the report is honest about its limits, but the
  underlying evidence itself is too thin to properly answer the
  question — more/better sources are needed, not just better writing.

Respond ONLY with JSON, no markdown fences, no preamble:
{{"verdict": "pass" | "revise" | "research_gap", "feedback": "specific, actionable feedback referencing the ORIGINAL question directly — empty string if verdict is pass"}}"""

    raw = call_llm(prompt, max_tokens=600)
    verdict, feedback = _parse(raw)

    updates = {"critique_verdict": verdict, "critique_feedback": feedback}
    if verdict == "revise":
        updates["revision_iteration"] = state.get("revision_iteration", 0) + 1
    return updates


def _parse(raw: str) -> tuple[str, str]:
    cleaned = raw.strip().strip("`")
    if cleaned.startswith("json"):
        cleaned = cleaned[4:].strip()

    for candidate in (cleaned, _extract_braces(raw)):
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
            verdict = parsed.get("verdict", "pass")
            if verdict not in ("pass", "revise", "research_gap"):
                verdict = "pass"
            return verdict, parsed.get("feedback", "")
        except json.JSONDecodeError:
            continue

    # Fail safe: if we can't parse the critique, don't loop forever —
    # treat it as a pass rather than risk an infinite/expensive retry.
    return "pass", ""


def _extract_braces(raw: str) -> str:
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start:end + 1]
    return ""
