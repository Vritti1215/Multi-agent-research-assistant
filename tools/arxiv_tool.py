import arxiv

# delay_seconds and num_retries give the library its own internal backoff
# on top of the spacing we add between sub-questions in search_agent.py —
# belt and suspenders against ArXiv's rate limiting.
_client = arxiv.Client(page_size=100, delay_seconds=3.0, num_retries=5)


def search_arxiv(query: str, max_results: int = 8) -> list[dict]:
    """Search ArXiv and return a list of paper dicts."""
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    results = []
    for r in _client.results(search):  # arxiv >=2.0 requires Client.results(search), not search.results()
        results.append({
            "title": r.title,
            "authors": [a.name for a in r.authors],
            "abstract": r.summary.replace("\n", " "),
            "url": r.entry_id,
            "year": r.published.year,
            "source": "arxiv",
            "citation_count": None,
            "pdf_url": r.pdf_url,
            "has_pdf": True,  # ArXiv always has a genuine direct PDF link
        })
    return results


if __name__ == "__main__":
    # quick manual test: python -m tools.arxiv_tool
    for p in search_arxiv("retrieval augmented generation hallucination", max_results=3):
        print(p["title"], "-", p["url"])
