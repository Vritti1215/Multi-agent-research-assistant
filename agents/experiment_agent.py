from tools.llm_client import call_llm


def generate_experiment_design(topic: str, analysis: str) -> str:
    """Generates a concrete ML experiment plan — dataset, training setup,
    evaluation metrics, baselines, ablations, and hardware requirements —
    grounded in the actual analysis from this research run. On-demand,
    single LLM call."""
    prompt = f"""Design a concrete machine learning experiment plan in
Markdown for the goal below. Ground choices in what's actually covered
in the ANALYSIS below where relevant (existing methods, known baselines,
datasets already used in this area), not generic ML boilerplate.

GOAL: {topic}

Use exactly these section headers, in this order:
## Objective
## Dataset
## Model / Approach
## Training Settings
## Evaluation Metrics
## Baselines
## Ablation Studies
## Hardware Requirements
## Expected Challenges

Rules:
- "Dataset": name real, specific datasets where you're confident they
  exist and are relevant; otherwise describe precisely what data is
  needed and how to source/construct it.
- "Training Settings": concrete hyperparameter ranges (learning rate,
  batch size, epochs, optimizer) appropriate to the approach — not vague
  placeholders.
- "Evaluation Metrics": the specific metrics actually used for this kind
  of task, referencing what ANALYSIS shows other work uses for comparability.
- "Baselines": name real methods/models to compare against, from ANALYSIS
  where possible.
- "Ablation Studies": 3-5 specific components worth ablating and why
  each one matters.
- "Hardware Requirements": realistic compute estimate (GPU type, count,
  approximate training time) — be specific, not "some compute".
- Be concrete throughout — no vague filler.

GOAL: {topic}

ANALYSIS FOR GROUNDING:
{analysis}"""

    return call_llm(prompt, max_tokens=3500)
