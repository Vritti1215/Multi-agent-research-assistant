from tools.llm_client import call_llm


def generate_peer_review(query: str, report: str, confidence_breakdown: dict) -> str:
    """Critiques the generated report the way a real peer reviewer would
    critique a paper — rigor, weak claims, what's missing — rather than
    just praising it. On-demand, single LLM call."""
    conf_note = (
        f"Confidence score was {confidence_breakdown.get('score', 0)}/100. "
        f"{confidence_breakdown.get('reason', '')}"
    )

    prompt = f"""You are a rigorous, skeptical peer reviewer — the kind
that catches weak claims and unjustified leaps, not one that rubber-stamps
everything. Review the RESEARCH REPORT below, written in response to:
{query}

Use exactly these section headers, in this order:
## Summary Assessment
## Strengths
## Weaknesses & Concerns
## Unsupported or Overreaching Claims
## Questions for the Authors
## Recommendation

Rules:
- "Summary Assessment": 2-3 sentences, direct, no hedging praise.
- "Weaknesses & Concerns": be specific — quote or closely paraphrase the
  actual claim you're concerned about, don't speak in generalities.
- "Unsupported or Overreaching Claims": look specifically for claims in
  the report that go beyond what the evidence would reasonably support —
  this is the most important section, don't skip or soften it.
- "Questions for the Authors": 3-5 pointed questions a genuine reviewer
  would ask.
- "Recommendation": give a real verdict — Accept, Minor Revision, Major
  Revision, or Reject — with one sentence of justification. Don't default
  to a safe middle answer if the evidence doesn't support it.
- Take into account this context on how grounded the report actually is: {conf_note}
- Be constructive but genuinely critical — a review that finds nothing
  wrong is not a useful review.

RESEARCH REPORT:
{report}"""

    return call_llm(prompt, max_tokens=3000)
