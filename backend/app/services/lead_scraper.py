import httpx
from typing import List, Dict, Any

from app.core.config import SERPAPI_KEY


def search_leads(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search for leads using SerpAPI (Google Search).
    Only uses publicly accessible search results.
    """
    if not SERPAPI_KEY:
        return []

    params = {
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": num_results,
        "engine": "google",
    }

    try:
        response = httpx.get("https://serpapi.com/search", params=params, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        results = []
        for item in data.get("organic_results", []):
            results.append({
                "company_name": item.get("title", ""),
                "website": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": "serpapi",
            })
        return results
    except Exception:
        return []
