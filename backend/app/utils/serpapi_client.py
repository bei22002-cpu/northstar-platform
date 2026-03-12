from typing import Optional
import httpx

from app.core.config import SERPAPI_KEY

SERPAPI_URL = "https://serpapi.com/search"


def search_leads(query: str, location: Optional[str] = None, num_results: int = 10) -> list[dict]:
    """Query SerpAPI for public web search results to discover potential leads."""
    if not SERPAPI_KEY:
        return []

    params = {
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": num_results,
        "engine": "google",
    }
    if location:
        params["location"] = location

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(SERPAPI_URL, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("organic_results", [])
    except httpx.HTTPError:
        return []
