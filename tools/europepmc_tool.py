import requests

BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def search_europepmc(query: str, max_results: int = 8) -> list[dict]:
    """Search Europe PMC — free, no API key required, specialized in
    biomedical/life-sciences literature. Only queried for Medical-domain
    queries (see search_agent.py) since it's not useful outside that
    domain. Papers without an abstract are skipped, same as other tools."""
    params = {
        "query": query,
        "format": "json",
        "resultType": "core",
        "pageSize": max_results,
    }
    try:
        resp = requests.get(BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Europe PMC request failed for '{query[:60]}...': {e}")
        return []

    results = []
    for item in resp.json().get("resultList", {}).get("result", []):
        abstract = item.get("abstractText", "")
        if not abstract:
            continue

        authors = [a.strip() for a in item.get("authorString", "").split(",") if a.strip()]

        pdf_url = ""
        for ft in (item.get("fullTextUrlList", {}) or {}).get("fullTextUrl", []):
            if ft.get("documentStyle") == "pdf":
                pdf_url = ft.get("url", "")
                break

        doi = item.get("doi", "")
        url = f"https://doi.org/{doi}" if doi else item.get("pmid", "")

        results.append({
            "title": item.get("title", "Untitled"),
            "authors": authors,
            "abstract": abstract,
            "url": url,
            "pdf_url": pdf_url or url,
            "has_pdf": bool(pdf_url),  # only True for a genuine PDF link, not the article landing page
            "year": int(item["pubYear"]) if item.get("pubYear", "").isdigit() else None,
            "source": "europepmc",
            "citation_count": item.get("citedByCount", 0),
        })
    return results


if __name__ == "__main__":
    # quick manual test: python -m tools.europepmc_tool
    for p in search_europepmc("CRISPR gene editing cancer therapy", max_results=3):
        print(p["title"], "-", p["url"])
