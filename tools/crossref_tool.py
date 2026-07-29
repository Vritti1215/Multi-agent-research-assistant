import re
import requests

BASE_URL = "https://api.crossref.org/works"


def _strip_jats_tags(text: str) -> str:
    """CrossRef sometimes wraps abstracts in JATS XML tags like <jats:p>."""
    return re.sub(r"<[^>]+>", "", text or "").strip()


def search_crossref(query: str, max_results: int = 8) -> list[dict]:
    """Search CrossRef — free, no API key required. CrossRef often lacks
    abstracts (it's primarily a citation/metadata index), so entries
    without one are skipped, same as the other tools — they wouldn't be
    usable for RAG anyway."""
    params = {
        "query": query,
        "rows": max_results,
        "mailto": "research-assistant@example.com",  # CrossRef's "polite pool" for more reliable responses
    }
    try:
        resp = requests.get(BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"CrossRef request failed for '{query[:60]}...': {e}")
        return []

    results = []
    for item in resp.json().get("message", {}).get("items", []):
        abstract = _strip_jats_tags(item.get("abstract", ""))
        if not abstract:
            continue

        title_list = item.get("title") or []
        title = title_list[0] if title_list else "Untitled"

        authors = []
        for a in item.get("author", []):
            name = f"{a.get('given', '')} {a.get('family', '')}".strip()
            if name:
                authors.append(name)

        year = None
        date_parts = (item.get("published-print") or item.get("published-online") or {}).get("date-parts")
        if date_parts and date_parts[0]:
            year = date_parts[0][0]

        url = item.get("URL", "")
        results.append({
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "url": url,
            "pdf_url": url,  # CrossRef doesn't reliably expose direct PDF links; this is the DOI landing page, often paywalled
            "has_pdf": False,  # CrossRef essentially never gives a genuine direct PDF link
            "year": year,
            "source": "crossref",
            "citation_count": item.get("is-referenced-by-count", 0),
        })
    return results


if __name__ == "__main__":
    # quick manual test: python -m tools.crossref_tool
    for p in search_crossref("retrieval augmented generation hallucination", max_results=3):
        print(p["title"], "-", p["url"])
