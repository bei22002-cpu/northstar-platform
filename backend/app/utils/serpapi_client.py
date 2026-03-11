import httpx
from typing import List, Dict, Any

from app.core.config import SERPAPI_KEY


def search(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """
    Wrapper around the SerpAPI Google Search endpoint.
    Returns raw organic search results.
    Only uses publicly accessible sources.
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
        return response.json().get("organic_results", [])
    except Exception:
        return []
