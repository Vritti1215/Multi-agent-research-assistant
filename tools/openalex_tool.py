import os
import requests

BASE_URL = "https://api.openalex.org/works"

_warned_missing_key = False  # only print the setup hint once per run


def _reconstruct_abstract(inverted_index: dict) -> str:
    """OpenAlex stores abstracts as a word -> [positions] inverted index
    instead of plain text, to save space. Rebuild the actual sentence
    from it."""
    if not inverted_index:
        return ""
    position_map = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            position_map[pos] = word
    return " ".join(position_map[i] for i in sorted(position_map))


def _sanitize_query(query: str) -> str:
    """OpenAlex's post-Feb-2026 search now parses boolean syntax
    (AND/OR/NOT, quoted phrases) and rejects unexpected punctuation with
    a 400 instead of just ignoring it like the old engine did. Our
    sub-questions are full natural-language sentences ending in '?',
    which appears to trip this — strip anything that isn't a letter,
    digit, space, or hyphen."""
    import re
    return re.sub(r"[^\w\s-]", " ", query).strip()


def search_openalex(query: str, max_results: int = 8) -> list[dict]:
    """Search OpenAlex — free, but as of Feb 13 2026 requires an API key
    for every request (previously the `mailto=` contact-email approach
    worked without one; OpenAlex retired that). Get a free key at
    https://openalex.org/settings/api and set OPENALEX_API_KEY in .env.
    """
    global _warned_missing_key
    api_key = os.getenv("OPENALEX_API_KEY")

    params = {"search": _sanitize_query(query), "per_page": max_results}
    if api_key:
        params["api_key"] = api_key
    elif not _warned_missing_key:
        _warned_missing_key = True
        print(
            "OpenAlex now requires an API key (as of Feb 2026). Get a free "
            "one at https://openalex.org/settings/api and set "
            "OPENALEX_API_KEY in .env. Skipping OpenAlex until then."
        )

    if not api_key:
        return []  # don't bother calling — it'll just 400/409 without a key

    try:
        resp = requests.get(BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"OpenAlex request failed for '{query[:60]}...': {e}")
        return []

    results = []
    for w in resp.json().get("results", []):
        abstract = _reconstruct_abstract(w.get("abstract_inverted_index"))
        if not abstract:
            continue
        authors = [
            a.get("author", {}).get("display_name", "")
            for a in w.get("authorships", [])
            if a.get("author", {}).get("display_name")
        ]
        pdf_url = (w.get("open_access") or {}).get("oa_url")
        doi = w.get("doi") or w.get("id", "")
        results.append({
            "title": w.get("title") or "Untitled",
            "authors": authors,
            "abstract": abstract,
            "url": doi,
            "pdf_url": pdf_url or doi,
            "has_pdf": bool(pdf_url),  # only True for a genuine open-access PDF, not the DOI/OpenAlex landing page
            "year": w.get("publication_year"),
            "source": "openalex",
            "citation_count": w.get("cited_by_count", 0),
        })
    return results


if __name__ == "__main__":
    # quick manual test: python -m tools.openalex_tool
    for p in search_openalex("retrieval augmented generation hallucination", max_results=3):
        print(p["title"], "-", p["url"])
