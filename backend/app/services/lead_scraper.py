from typing import Optional

from app.utils.serpapi_client import search_leads


def scrape_leads(query: str, location: Optional[str] = None, industry: Optional[str] = None, num_results: int = 10) -> list[dict]:
    """
    Search publicly available web sources via SerpAPI and normalise
    the results into a list of raw lead dictionaries.

    Only public web data is used — no restricted or private data sources.
    """
    raw_results = search_leads(query=query, location=location, num_results=num_results)

    leads = []
    for result in raw_results:
        lead = {
            "company_name": result.get("title", "Unknown"),
            "website": result.get("link"),
            "notes": result.get("snippet"),
            "source": "serpapi",
            "industry": industry,
            "contact_name": None,
            "email": None,
        }
        leads.append(lead)

    return leads
