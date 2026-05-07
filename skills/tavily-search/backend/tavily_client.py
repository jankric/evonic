"""
Tavily client — shared HTTP helper for Tavily API calls.
"""
import os
import requests

TAVILY_BASE_URL = "https://api.tavily.com"
DEFAULT_TIMEOUT = 30


class TavilyError(Exception):
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def get_api_key() -> str:
    """Get Tavily API key from skill config or environment."""
    try:
        from backend.skills_manager import skills_manager
        config = skills_manager.get_skill_config('tavily-search')
        key = config.get('api_key', '').strip()
        if key:
            return key
    except Exception:
        pass
    return os.environ.get('TAVILY_API_KEY', '')


def search(api_key: str, query: str, num_results: int = 5,
           search_depth: str = "basic", topic: str = "general",
           time_range: str = None, include_answer: bool = False) -> dict:
    """Call Tavily search API."""
    if not api_key:
        raise TavilyError("No Tavily API key configured.", 401)

    payload = {
        "query": query,
        "max_results": min(max(1, num_results), 10),
        "search_depth": search_depth,
        "topic": topic,
        "include_answer": include_answer,
        "include_raw_content": False,
    }
    if time_range:
        payload["time_range"] = time_range

    try:
        resp = requests.post(
            f"{TAVILY_BASE_URL}/search",
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=DEFAULT_TIMEOUT
        )
    except requests.Timeout:
        raise TavilyError("Tavily request timed out.", 408)
    except requests.RequestException as e:
        raise TavilyError(f"Network error: {e}", 0)

    if resp.status_code == 429:
        raise TavilyError("Rate limit exceeded. Try again later.", 429)
    if resp.status_code == 401:
        raise TavilyError("Invalid Tavily API key.", 401)
    if not resp.ok:
        raise TavilyError(f"Tavily API error: {resp.text[:200]}", resp.status_code)

    data = resp.json()
    results = data.get("results", [])

    formatted = []
    for r in results:
        formatted.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", "")[:500],
            "published_date": r.get("published_date", ""),
            "score": round(r.get("score", 0), 3)
        })

    output = {
        "status": "ok",
        "query": query,
        "count": len(formatted),
        "results": formatted
    }
    if include_answer and data.get("answer"):
        output["answer"] = data["answer"]

    return output


def extract(api_key: str, urls: list, query: str = None) -> dict:
    """Call Tavily extract API."""
    if not api_key:
        raise TavilyError("No Tavily API key configured.", 401)

    payload = {"urls": urls[:5]}
    if query:
        payload["query"] = query

    try:
        resp = requests.post(
            f"{TAVILY_BASE_URL}/extract",
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=DEFAULT_TIMEOUT
        )
    except requests.Timeout:
        raise TavilyError("Tavily extract timed out.", 408)
    except requests.RequestException as e:
        raise TavilyError(f"Network error: {e}", 0)

    if not resp.ok:
        raise TavilyError(f"Tavily extract error: {resp.text[:200]}", resp.status_code)

    data = resp.json()
    results = data.get("results", [])

    formatted = []
    for r in results:
        content = r.get("raw_content") or r.get("content") or ""
        formatted.append({
            "url": r.get("url", ""),
            "content": content[:3000]
        })

    return {
        "status": "ok",
        "count": len(formatted),
        "results": formatted
    }
