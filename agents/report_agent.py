from tools.llm_client import call_llm


def report_node(state: dict) -> dict:
    """Compiles everything into a formal, publication-style literature
    review rather than a loose summary — Abstract through References."""
    claims_block = "\n".join(
        f"- {c['text']} (Source: {c['source_paper_url']}, confidence: {c['confidence']:.2f})"
        for c in state["validated_claims"]
    ) or "No claims passed grounding validation — rely on the analysis below, and note the limited source coverage explicitly."

    contradictions_block = "\n".join(
        f'- "{c.get("claim_a", "")}" vs "{c.get("claim_b", "")}" — possible reason: {c.get("possible_reason", "unclear")}'
        for c in state.get("contradictions", [])
    ) or "None identified among the retrieved sources."

    gaps_block = "\n".join(f"- {g}" for g in state.get("gaps", [])) or "None explicitly identified."

    confidence = state.get("confidence_score", 0)
    revision_feedback = state.get("critique_feedback", "")
    previous_report = state.get("final_report", "")

    if revision_feedback and previous_report:
        # REVISION MODE: the critique agent found the evidence adequate
        # but the writing itself unfocused/shallow relative to the
        # ORIGINAL question. Rewrite targeting that feedback specifically
        # — don't regenerate blindly from scratch.
        prompt = f"""You previously wrote the research report below in
response to: {state['query']}

A critique found this specific problem with the report (not the
evidence — the writing itself):
{revision_feedback}

Rewrite the report to directly fix that problem, keeping the same
Markdown section structure (Abstract, Introduction, Background, Related
Work / Key Findings, Points of Disagreement, Research Gaps, Future
Directions, Conclusion, References) and staying grounded in the same
validated claims and analysis below — do not invent new claims, only
improve focus, depth, and directness in answering the original question.

CONFIDENCE SCORE: {confidence}/100

VALIDATED CLAIMS:
{claims_block}

CONTRADICTIONS:
{contradictions_block}

RESEARCH GAPS:
{gaps_block}

FULL ANALYSIS (do not contradict the validated claims above):
{state['analysis']}

PREVIOUS REPORT (to revise):
{previous_report}"""

        report = call_llm(prompt, max_tokens=4000)
        return {"final_report": report}

    prompt = f"""Write a formal literature-review-style research report in
Markdown answering: {state['query']}

Use exactly these section headers, in this order:
## Abstract
## Introduction
## Background
## Related Work / Key Findings
## Points of Disagreement
## Research Gaps
## Future Directions
## Conclusion
## References

Rules:
- Mention the confidence score once, near the top of the Abstract (e.g.
  "This review is grounded with an estimated confidence of X/100, based
  on source coverage and claim-grounding strength").
- Be concrete: name real methods, papers, and findings from the analysis
  below. Never write filler like "various approaches exist" without
  naming them.
- "Points of Disagreement": use the CONTRADICTIONS list below as your
  anchor. Explain each one and why it might exist.
- "Research Gaps": use the GAPS list below as your anchor — elaborate on
  these, don't invent unrelated ones.
- Weave in the validated claims as your most trustworthy anchors, using
  the fuller analysis for depth and nuance.
- Target at least 700 words if the material supports it.
- References: list every source cited, as [Title](url).

CONFIDENCE SCORE: {confidence}/100

VALIDATED CLAIMS:
{claims_block}

CONTRADICTIONS:
{contradictions_block}

RESEARCH GAPS:
{gaps_block}

FULL ANALYSIS (do not contradict the validated claims above):
{state['analysis']}"""

    report = call_llm(prompt, max_tokens=4000)
    return {"final_report": report}
