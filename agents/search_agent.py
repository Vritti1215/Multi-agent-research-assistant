from tools.arxiv_tool import search_arxiv
from tools.semantic_scholar_tool import search_semantic_scholar


def search_node(state: dict) -> dict:
    """Runs every sub-question against both paper sources and dedupes by title."""
    all_papers = list(state.get("papers", []))  # keep results from prior loop iterations
    seen_titles = {p["title"].lower() for p in all_papers}

    max_results = 12 if state.get("deep_mode") else 8

    for sq in state["sub_questions"]:
        for fn in (search_arxiv, search_semantic_scholar):
            try:
                for p in fn(sq, max_results=max_results):
                    if p["title"].lower() not in seen_titles:
                        seen_titles.add(p["title"].lower())
                        all_papers.append(p)
            except Exception as e:
                print(f"Search error ({fn.__name__} for '{sq}'): {e}")

    return {"papers": all_papers, "iteration": state.get("iteration", 0) + 1}
