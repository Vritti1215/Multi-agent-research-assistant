import time
from tools.arxiv_tool import search_arxiv
from tools.semantic_scholar_tool import search_semantic_scholar
from tools.openalex_tool import search_openalex
from tools.crossref_tool import search_crossref
from tools.europepmc_tool import search_europepmc


def search_node(state: dict) -> dict:
    """Runs every sub-question against multiple paper sources and dedupes
    by title. Always queries the 4 general-purpose sources (ArXiv,
    Semantic Scholar, OpenAlex, CrossRef); additionally queries Europe
    PMC when the planner classified this query as Medical — using a
    biomedical-specific source for biomedical queries gets meaningfully
    better results than treating every domain the same."""
    all_papers = list(state.get("papers", []))  # keep results from prior loop iterations
    seen_titles = {p["title"].lower() for p in all_papers}

    max_results = 12 if state.get("deep_mode") else 8

    sources = [search_arxiv, search_semantic_scholar, search_openalex, search_crossref]
    if state.get("domain") == "Medical":
        sources.append(search_europepmc)

    for i, sq in enumerate(state["sub_questions"]):
        if i > 0:
            # ArXiv's API asks for ~1 request per 3s per IP. Firing every
            # sub-question back-to-back was tripping their rate limiter.
            time.sleep(3)

        for fn in sources:
            try:
                for p in fn(sq, max_results=max_results):
                    if p["title"].lower() not in seen_titles:
                        seen_titles.add(p["title"].lower())
                        all_papers.append(p)
            except Exception as e:
                print(f"Search error ({fn.__name__} for '{sq}'): {e}")

    return {"papers": all_papers, "iteration": state.get("iteration", 0) + 1}
