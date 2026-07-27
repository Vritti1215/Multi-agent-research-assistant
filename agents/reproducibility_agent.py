from tools.llm_client import call_llm


def generate_reproducibility_check(query: str, analysis: str, papers: list[dict]) -> str:
    """Assesses reproducibility of the methods/findings referenced in the
    analysis — code/data availability signals, methodology detail,
    single vs. multiple benchmarks, sample size concerns. On-demand,
    single LLM call. This is a heuristic assessment from abstracts/analysis
    text, not a verified audit of actual repos — the output says so."""
    paper_titles = "\n".join(f"- {p['title']} ({p.get('year', 'n.d.')})" for p in papers[:15])

    prompt = f"""Assess the reproducibility of the research discussed below,
related to: {query}

Use exactly these section headers, in this order:
## Reproducibility Summary
## Checklist
## Red Flags
## What Would Improve Reproducibility
## Caveats on This Assessment

Rules:
- "Reproducibility Summary": 2-3 sentences giving an overall impression,
  plus a rough qualitative rating (e.g. "Likely reproducible with effort",
  "Significant barriers", "Insufficient information to assess").
- "Checklist": go through these specific items based on what the ANALYSIS
  indicates, marking each as Likely / Unclear / Unlikely with a one-line
  reason: code availability, data/dataset availability, methodology
  detail sufficiency, evaluation on multiple datasets/benchmarks vs. just
  one, sample size adequacy, random seed / variance reporting.
- "Red Flags": specific reproducibility concerns actually suggested by
  the analysis (e.g. single small dataset, no baseline comparison, vague
  methodology description) — don't invent concerns not suggested by the text.
- "What Would Improve Reproducibility": concrete, actionable suggestions.
- "Caveats on This Assessment": be explicit that this assessment is based
  on abstracts and synthesized analysis text, NOT a verified audit of
  actual code repositories or supplementary materials — it's a heuristic
  read, not a guarantee.

PAPERS CONSIDERED:
{paper_titles}

ANALYSIS:
{analysis}"""

    return call_llm(prompt, max_tokens=2500)
