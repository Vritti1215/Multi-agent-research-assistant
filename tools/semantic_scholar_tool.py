import os
import requests

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


def search_semantic_scholar(query: str, max_results: int = 8) -> list[dict]:
    """Search Semantic Scholar and return a list of paper dicts.
    Papers without an abstract are skipped since they're not usable for RAG.
    """
    headers = {}
    key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if key:
        headers["x-api-key"] = key

    params = {
        "query": query,
        "limit": max_results,
        "fields": "title,authors,abstract,url,year,citationCount",
    }
    resp = requests.get(BASE_URL, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json().get("data", [])

    results = []
    for p in data:
        if not p.get("abstract"):
            continue
        results.append({
            "title": p["title"],
            "authors": [a["name"] for a in p.get("authors", [])],
            "abstract": p["abstract"],
            "url": p.get("url", ""),
            "year": p.get("year"),
            "source": "semantic_scholar",
            "citation_count": p.get("citationCount", 0),
        })
    return results


if __name__ == "__main__":
    # quick manual test: python -m tools.semantic_scholar_tool
    for p in search_semantic_scholar("retrieval augmented generation hallucination", max_results=3):
        print(p["title"], "-", p["url"])
