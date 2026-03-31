"""Web search tool — basic web search via DuckDuckGo HTML."""

from __future__ import annotations

import json
from typing import Any, Dict
from urllib.error import URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from agent_v5.tools.base import BaseTool
from agent_v5.registry import ToolRegistry


@ToolRegistry.register("web_search")
class WebSearchTool(BaseTool):
    tool_id = "web_search"
    description = "Search the web for information."

    def execute(self, query: str = "", **kwargs: Any) -> str:
        if not query:
            return "Error: query is required"

        try:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            # Extract result snippets from DDG HTML
            results: list[str] = []
            parts = html.split('class="result__snippet"')
            for part in parts[1:6]:  # First 5 results
                end = part.find("</a>")
                if end == -1:
                    end = part.find("</td>")
                if end == -1:
                    end = 300
                snippet = part[1:end]
                # Strip HTML tags
                clean = ""
                in_tag = False
                for ch in snippet:
                    if ch == "<":
                        in_tag = True
                    elif ch == ">":
                        in_tag = False
                    elif not in_tag:
                        clean += ch
                clean = clean.strip()
                if clean:
                    results.append(clean)

            if results:
                return "\n\n".join(f"{i+1}. {r}" for i, r in enumerate(results))
            return f"No results found for '{query}'"

        except (URLError, OSError) as e:
            return f"Search error: {e}"

    def to_definition(self) -> Dict[str, Any]:
        return {
            "name": "web_search",
            "description": "Search the web for current information.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    }
                },
                "required": ["query"],
            },
        }
