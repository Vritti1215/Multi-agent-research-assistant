import arxiv


def search_arxiv(query: str, max_results: int = 8) -> list[dict]:
    """Search ArXiv and return a list of paper dicts."""
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    results = []
    for r in search.results():
        results.append({
            "title": r.title,
            "authors": [a.name for a in r.authors],
            "abstract": r.summary.replace("\n", " "),
            "url": r.entry_id,
            "year": r.published.year,
            "source": "arxiv",
            "citation_count": None,
            "pdf_url": r.pdf_url,
        })
    return results


if __name__ == "__main__":
    # quick manual test: python -m tools.arxiv_tool
    for p in search_arxiv("retrieval augmented generation hallucination", max_results=3):
        print(p["title"], "-", p["url"])
