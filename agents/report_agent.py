from tools.llm_client import call_llm


def report_node(state: dict) -> dict:
    """Compiles the validated, grounded claims into a polished Markdown report."""
    claims_block = "\n".join(
        f"- {c['text']} (Source: {c['source_paper_url']}, confidence: {c['confidence']:.2f})"
        for c in state["validated_claims"]
    ) or "No claims passed grounding validation."

    prompt = f"""Write a polished research report in Markdown answering:
{state['query']}

Structure: Executive Summary, Key Findings, Points of Disagreement,
Research Gaps, Conclusion, References.

Only use these validated, grounded claims — do not add unsupported facts:
{claims_block}

Analysis for additional context (do not contradict the validated claims above):
{state['analysis']}"""

    report = call_llm(prompt, max_tokens=3000)
    return {"final_report": report}
