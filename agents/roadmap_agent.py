from tools.llm_client import call_llm


def generate_roadmap(topic: str, analysis: str) -> str:
    """Generates a detailed, phased learning roadmap for understanding the
    topic — grounded in the actual analysis from this research run, so the
    later phases reflect the real state of the field rather than generic
    textbook ordering. On-demand, single LLM call."""
    prompt = f"""Create a detailed, phased learning roadmap in Markdown for
someone who wants to deeply understand: {topic}

Ground the later phases in what's actually covered in the ANALYSIS below
where relevant, so the roadmap reflects the real current state of this
field, not a generic textbook sequence.

Structure it as 4-7 phases, each with:
### Phase N: [Title] (estimated duration, e.g. "Week 1-2")
- **Concepts to learn:** 2-4 specific concepts or techniques
- **Suggested reading:** be specific about what kind of source (e.g.
  "the original Transformer paper" or "a survey on X techniques"),
  not vague suggestions like "read some papers"
- **Practice:** a concrete mini-project or exercise for this phase,
  where one makes sense

End with:
## Where This Connects to Current Research
A short paragraph linking the roadmap to what's actually happening in
the field right now, grounded in the analysis below.

Be concrete throughout — no vague filler like "learn the basics".

TOPIC: {topic}

ANALYSIS FOR GROUNDING:
{analysis}"""

    return call_llm(prompt, max_tokens=3000)
