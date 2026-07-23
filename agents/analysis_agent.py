from tools.llm_client import call_llm


def analysis_node(state: dict) -> dict:
    """Synthesizes the retrieved chunks into a grounded analysis, explicitly
    instructed to stick to the provided sources only."""
    context = "\n\n".join(
        f"[{c['title']}]({c['url']}): {c['text'][:500]}"
        for c in state["retrieved_chunks"]
    )

    if not context:
        return {"analysis": "No relevant sources were retrieved for this query."}

    prompt = f"""You are a research analyst. Using ONLY the sources below,
write an analysis answering: {state['query']}

Identify: key findings, points of disagreement between papers, and gaps
in the literature. Cite paper titles inline like [Title]. Do not use
any outside knowledge not present in the sources.

SOURCES:
{context}"""

    analysis = call_llm(prompt, max_tokens=2000)
    return {"analysis": analysis}
