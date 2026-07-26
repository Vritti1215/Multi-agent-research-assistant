from tools.llm_client import call_llm


def generate_proposal(topic: str, analysis: str, gaps: list[str]) -> str:
    """Generates a formal research proposal grounded in the analysis and
    research gaps from a completed run — the proposal targets a real gap
    the pipeline actually found, rather than being generic boilerplate
    about the topic. Single LLM call, called on-demand (not automatically
    on every research run) to keep it free-tier friendly.
    """
    gaps_block = "\n".join(f"- {g}" for g in gaps) or "No specific gaps were identified in the prior analysis — propose based on the general topic instead."

    prompt = f"""Write a formal, detailed research proposal in Markdown for
the topic below. Ground it in the analysis and identified research gaps
provided — the proposal should target ONE specific real gap, not restate
the topic generically.

TOPIC: {topic}

Use exactly these section headers, in this order:
## Problem Statement
## Background & Motivation
## Objectives
## Methodology
## Dataset Suggestions
## Evaluation Plan
## Timeline
## Required Resources
## Expected Outcomes
## Risks & Mitigations
## Future Scope

Rules:
- "Problem Statement": pick ONE specific gap from RESEARCH GAPS below and
  frame the entire proposal around it, not the whole topic broadly.
- "Background & Motivation": explain why this gap matters, referencing
  specific findings from the ANALYSIS below.
- "Objectives": 3-5 concrete, measurable objectives — not vague aims.
- "Methodology": name real techniques/approaches, building on what's
  already established per ANALYSIS below, and explain precisely what's
  novel about this proposal's approach.
- "Dataset Suggestions": name real, publicly known datasets relevant to
  the topic where you're confident they exist; otherwise describe
  precisely what kind of dataset is needed and how it could be built.
- "Evaluation Plan": specific metrics and baselines this work would be
  compared against.
- "Timeline": a realistic phase-by-phase breakdown (e.g. by month/quarter),
  each phase with a concrete deliverable.
- "Required Resources": compute, data access, tooling, or expertise
  genuinely needed — be specific (e.g. "a single A100 GPU for ~2 weeks
  of fine-tuning runs", not "some compute").
- "Risks & Mitigations": genuine technical or practical risks specific to
  THIS proposal, each paired with a concrete mitigation — not generic
  risks like "the project might take longer than expected".
- Be concrete throughout — no vague filler language anywhere.

RESEARCH GAPS FROM PRIOR ANALYSIS:
{gaps_block}

ANALYSIS FOR CONTEXT:
{analysis}"""

    return call_llm(prompt, max_tokens=4000)
