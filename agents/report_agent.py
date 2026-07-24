from tools.llm_client import call_llm


def report_node(state: dict) -> dict:
    """Compiles the validated claims AND the fuller analysis into a
    detailed Markdown report. Leaning on analysis (not just the short
    validated-claims list) for prose keeps the report from reading as a
    thin bullet list stitched with generic filler."""
    claims_block = "\n".join(
        f"- {c['text']} (Source: {c['source_paper_url']}, confidence: {c['confidence']:.2f})"
        for c in state["validated_claims"]
    ) or "No claims passed grounding validation — rely on the analysis below, and note the limited source coverage explicitly in the report."

    prompt = f"""Write a detailed, specific research report in Markdown
answering: {state['query']}

Structure: Executive Summary, Key Findings, Points of Disagreement,
Research Gaps, Conclusion, References.

Rules:
- Be concrete: name real methods, papers, and findings from the analysis
  below. Never write filler like "there are various approaches" or
  "research suggests multiple methods exist" without naming them.
- Weave in the validated claims below as your most trustworthy anchors,
  but use the fuller analysis text to add real detail and nuance around them.
- If source coverage on some sub-topic was thin, say so explicitly in
  Research Gaps rather than glossing over it with vague language.
- Target at least 700 words if the material supports it — don't pad, but
  don't truncate real content either.
- References section: list every source cited, as [Title](url).

VALIDATED CLAIMS (grounded, high-trust anchors):
{claims_block}

FULL ANALYSIS (use for depth and detail, must not contradict validated claims):
{state['analysis']}"""

    report = call_llm(prompt, max_tokens=4000)
    return {"final_report": report}
