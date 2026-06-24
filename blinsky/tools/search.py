"""
Tavily web search wrapper.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

_client: TavilyClient | None = None


def _get_client() -> TavilyClient:
    global _client
    if _client is None:
        api_key = os.getenv("TAVILY_API_KEY") or ""
        _client = TavilyClient(api_key=api_key or None)
    return _client


def web_search(query: str, max_results: int = 1) -> str:
    try:
        client = _get_client()
        res = client.search(query=query, max_results=max_results, include_answer=False)
        items = res.get("results", [])[:max_results]
        if not items:
            return "No search results found."
        lines = []
        for i, item in enumerate(items, 1):
            title = item.get("title", "No title")
            url = item.get("url", "")
            snippet = (item.get("content") or "")[:250]
            lines.append(f"{i}. {title}\n   {url}\n   {snippet}")
        return "\n\n".join(lines)
    except Exception as exc:
        return f"Search error: {exc}"
