import json
from tools.llm_client import call_llm


def _extract_claims(analysis_text: str) -> list[str]:
    prompt = f"""Extract the 5-8 most important factual claims from this
text as a JSON list of strings (just the claim text, no citations, no
markdown fences).

TEXT:
{analysis_text}"""

    raw = call_llm(prompt, max_tokens=800).strip("`")
    if raw.startswith("json"):
        raw = raw[4:].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def _verify_claim_against_chunks(claim: str, chunks: list[dict]) -> tuple[float, dict | None]:
    """Single call per claim: shows the model ALL candidate chunks at once
    and asks which (if any) supports it. Much cheaper than one call per
    claim-chunk pair, and still demonstrates the grounding technique."""
    if not chunks:
        return 0.0, None

    sources_block = "\n\n".join(
        f"[{i}] ({c['title']}): {c['text'][:400]}" for i, c in enumerate(chunks)
    )
    prompt = f"""Which source below (if any) best supports this claim?
Reply ONLY with JSON: {{"source_index": <int or -1 if none support it>, "confidence": <0-1 float>}}

CLAIM: {claim}

SOURCES:
{sources_block}"""

    raw = call_llm(prompt, max_tokens=100).strip("`")
    if raw.startswith("json"):
        raw = raw[4:].strip()

    try:
        parsed = json.loads(raw)
        idx = parsed.get("source_index", -1)
        conf = float(parsed.get("confidence", 0.0))
    except (json.JSONDecodeError, ValueError, TypeError):
        return 0.0, None

    if idx is None or idx < 0 or idx >= len(chunks):
        return 0.0, None
    return conf, chunks[idx]


def citation_node(state: dict) -> dict:
    """Extracts claims from the analysis and verifies each is grounded in
    a retrieved chunk before it's allowed into the final report. This is
    the hallucination-prevention step."""
    claims = _extract_claims(state["analysis"])
    chunks = state["retrieved_chunks"]

    validated = []
    for claim in claims:
        confidence, match = _verify_claim_against_chunks(claim, chunks)
        if confidence >= 0.6 and match:
            validated.append({
                "text": claim,
                "source_paper_url": match["url"],
                "confidence": confidence,
            })

    return {"validated_claims": validated}
