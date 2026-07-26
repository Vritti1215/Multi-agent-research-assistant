import json
from tools.llm_client import call_llm


def _extract_claims(analysis_text: str) -> list[str]:
    prompt = f"""Extract the 8-12 most important, SPECIFIC factual claims
from this text as a JSON list of strings (just the claim text, no
citations, no markdown fences). Prefer concrete claims (a named method,
a finding, a number, a named limitation) over vague summary statements.

TEXT:
{analysis_text}"""

    raw = call_llm(prompt, max_tokens=1000).strip("`")
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


def _compute_confidence_score(validated: list[dict], claims_extracted: int, papers_found: int) -> dict:
    """Explainable confidence score, computed entirely from data already
    in hand — deliberately NOT an LLM call, to keep this feature free.

    Three factors, weighted:
    - avg_grounding (50%): how confidently claims matched their sources
    - coverage (30%): what fraction of extracted claims actually got grounded
    - paper_support (20%): how many papers backed the analysis at all,
      saturating at 8+ (more than that doesn't meaningfully add confidence)

    Returns the breakdown, not just the final number, so the UI can show
    WHY the score is what it is instead of a bare figure.
    """
    if not validated:
        return {
            "score": 0.0, "avg_grounding": 0.0, "coverage": 0.0, "paper_support": 0.0,
            "reason": "No claims passed grounding validation, so there's nothing to base a confidence score on.",
        }

    avg_grounding = sum(c["confidence"] for c in validated) / len(validated)
    coverage = len(validated) / max(claims_extracted, 1)
    paper_support = min(papers_found / 8, 1.0)
    score = round((0.5 * avg_grounding + 0.3 * coverage + 0.2 * paper_support) * 100, 1)

    # Identify the weakest factor to explain what's actually holding the score back
    factors = {"grounding strength": avg_grounding, "claim coverage": coverage, "source breadth": paper_support}
    weakest = min(factors, key=factors.get)
    if score >= 70:
        reason = f"Strong overall grounding — claims consistently matched their sources, with {weakest} being the (still solid) relative weak point."
    elif score >= 40:
        reason = f"Moderate confidence — {weakest} is the main thing pulling the score down; more sources or a narrower query could help."
    else:
        reason = f"Low confidence — {weakest} is notably weak, meaning this report leans more on the model's synthesis than tightly-grounded evidence."

    return {
        "score": score,
        "avg_grounding": round(avg_grounding * 100, 1),
        "coverage": round(coverage * 100, 1),
        "paper_support": round(paper_support * 100, 1),
        "reason": reason,
    }


def citation_node(state: dict) -> dict:
    """Extracts claims from the analysis and verifies each is grounded in
    a retrieved chunk before it's allowed into the final report. This is
    the hallucination-prevention step.

    Threshold is 0.5 rather than a stricter cutoff: too strict and thin
    or off-the-beaten-path topics end up with almost nothing validated,
    which starves the report agent and produces generic filler instead.
    0.5 still requires a real match, just not a near-perfect one.
    """
    claims = _extract_claims(state["analysis"])
    chunks = state["retrieved_chunks"]

    validated = []
    for claim in claims:
        confidence, match = _verify_claim_against_chunks(claim, chunks)
        if confidence >= 0.5 and match:
            validated.append({
                "text": claim,
                "source_paper_url": match["url"],
                "confidence": confidence,
            })

    breakdown = _compute_confidence_score(validated, len(claims), len(state.get("papers", [])))

    return {
        "validated_claims": validated,
        "confidence_score": breakdown["score"],
        "confidence_breakdown": breakdown,
    }
