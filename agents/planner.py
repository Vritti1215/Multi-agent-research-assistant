import json
from tools.llm_client import call_llm


def planner_node(state: dict) -> dict:
    """Breaks the user's query into focused sub-questions the search agent
    can run individually against ArXiv / Semantic Scholar."""
    prompt = f"""Break this research query into 3-5 focused sub-questions
that together cover it well from different angles (definitions, methods,
evidence, critiques/limitations, real-world examples). Respond ONLY with
a JSON list of strings, no preamble, no markdown fences.

Query: {state['query']}"""

    text = call_llm(prompt, max_tokens=500)
    text = text.strip("`")
    if text.startswith("json"):
        text = text[4:].strip()

    try:
        sub_questions = json.loads(text)
    except json.JSONDecodeError:
        # fallback: treat the whole query as a single sub-question
        sub_questions = [state["query"]]

    return {"sub_questions": sub_questions, "iteration": 0}