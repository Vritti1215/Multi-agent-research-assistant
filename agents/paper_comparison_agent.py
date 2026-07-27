from tools.llm_client import call_llm


def generate_paper_comparison(papers: list[dict]) -> str:
    """Synthesizes a comparison of the given papers — methods, findings,
    and differences — not just a side-by-side of metadata. On-demand,
    single LLM call."""
    papers_block = "\n\n".join(
        f"### {p['title']} ({p.get('year', 'n.d.')})\n{p.get('abstract', 'No abstract available.')}"
        for p in papers
    )

    prompt = f"""Compare the papers below in Markdown.

Use exactly these section headers, in this order:
## Overview
## Methodology Comparison
## Key Findings Comparison
## Strengths and Weaknesses
## Which to Use When

Rules:
- "Overview": 2-3 sentences on what these papers have in common and how
  they differ at a high level.
- "Methodology Comparison": a comparison table or structured breakdown
  of the actual approaches/methods used in each paper.
- "Key Findings Comparison": what each paper actually found, and where
  they agree or disagree.
- "Strengths and Weaknesses": for each paper specifically, not generic.
- "Which to Use When": practical guidance on which paper's approach fits
  which use case.
- Refer to papers by their actual titles, not "Paper 1/Paper 2".
- Be concrete — no vague filler.

PAPERS:
{papers_block}"""

    return call_llm(prompt, max_tokens=3000)
