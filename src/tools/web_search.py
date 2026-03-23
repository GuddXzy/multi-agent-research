"""Web search tool using DuckDuckGo (no API key required)."""

import os
import time
from langchain_core.tools import tool
from src.config import SEARCH_DELAY


@tool
def web_search(query: str) -> str:
    """Search the internet for current information about the given query.

    Use this for recent news, trends, statistics, and up-to-date facts.
    Returns formatted results with title, summary, and URL.
    """
    try:
        from ddgs import DDGS

        time.sleep(SEARCH_DELAY)  # rate-limit: avoid being blocked

        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
        results = []
        with DDGS(timeout=10, proxy=proxy) as ddgs:
            for r in ddgs.text(query, max_results=3):
                results.append(r)

        if not results:
            return f"No results found for: {query}"

        lines = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            body = r.get("body", r.get("snippet", "No snippet"))
            href = r.get("href", r.get("url", ""))
            lines.append(f"[{i}] {title}\n    {body}\n    URL: {href}")

        return "\n\n".join(lines)

    except Exception as exc:
        return f"Web search failed for '{query}': {exc}"
