from tools.llm_client import call_llm


def analysis_node(state: dict) -> dict:
    """Synthesizes the retrieved chunks into a grounded analysis, explicitly
    instructed to stick to the provided sources only — and to be specific
    rather than generic."""
    context = "\n\n".join(
        f"[{c['title']}]({c['url']}): {c['text'][:600]}"
        for c in state["retrieved_chunks"]
    )

    if not context:
        return {"analysis": "No relevant sources were retrieved for this query."}

    prompt = f"""You are a meticulous research analyst. Using ONLY the
sources below, write a detailed analysis answering: {state['query']}

Requirements:
- Be SPECIFIC: name actual methods, techniques, findings, or numbers from
  the sources. Do not write vague statements like "researchers have found
  various approaches" — say which approaches, from which paper.
- Cover: key findings, points of disagreement or tension between sources,
  and explicit gaps in what the sources cover.
- Cite paper titles inline like [Title] every time you use a claim from it.
- If the sources only partially cover the query, say explicitly what's
  missing rather than padding with generic statements.
- Do not use any outside knowledge not present in the sources.
- Aim for at least 500 words if the sources support it.

SOURCES:
{context}"""

    analysis = call_llm(prompt, max_tokens=2500)
    return {"analysis": analysis}
