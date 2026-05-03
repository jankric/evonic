"""
Exa AI REST API client.

Thin wrapper around the Exa API (https://docs.exa.ai/reference).
Uses stdlib urllib to avoid external dependencies.
"""

import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

EXA_BASE_URL = "https://api.exa.ai"
REQUEST_TIMEOUT = 30


class ExaError(Exception):
    """Exa API error with status code and message."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Exa API error {status_code}: {message}")


def _request(api_key: str, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Make a POST request to the Exa API."""
    url = f"{EXA_BASE_URL}/{endpoint.lstrip('/')}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
            err_data = json.loads(body)
            body = err_data.get("error", err_data.get("message", body))
        except Exception:
            pass
        raise ExaError(e.code, body or str(e))
    except urllib.error.URLError as e:
        raise ExaError(0, f"Connection error: {e.reason}")


def search(
    api_key: str,
    query: str,
    num_results: int = 10,
    search_type: str = "auto",
    include_text: bool = False,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    start_published_date: Optional[str] = None,
    category: Optional[str] = None,
    max_characters: int = 3000,
) -> Dict[str, Any]:
    """Search the web using Exa."""
    payload: Dict[str, Any] = {
        "query": query,
        "numResults": min(max(num_results, 1), 50),
    }
    if search_type != "auto":
        payload["type"] = search_type
    if include_text:
        payload["contents"] = {"text": {"maxCharacters": max_characters}}
    if include_domains:
        payload["includeDomains"] = include_domains
    if exclude_domains:
        payload["excludeDomains"] = exclude_domains
    if start_published_date:
        payload["startPublishedDate"] = start_published_date
    if category:
        payload["category"] = category

    return _request(api_key, "/search", payload)


def get_contents(
    api_key: str,
    urls: List[str],
    max_characters: int = 3000,
) -> Dict[str, Any]:
    """Fetch text content of web pages by URL."""
    # Exa uses IDs from search results, but also accepts URLs directly
    payload: Dict[str, Any] = {
        "urls": urls[:10],
        "text": {"maxCharacters": min(max(max_characters, 100), 10000)},
    }
    return _request(api_key, "/contents", payload)


def find_similar(
    api_key: str,
    url: str,
    num_results: int = 10,
    include_text: bool = False,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    max_characters: int = 3000,
) -> Dict[str, Any]:
    """Find pages similar to a given URL."""
    payload: Dict[str, Any] = {
        "url": url,
        "numResults": min(max(num_results, 1), 50),
    }
    if include_text:
        payload["contents"] = {"text": {"maxCharacters": max_characters}}
    if include_domains:
        payload["includeDomains"] = include_domains
    if exclude_domains:
        payload["excludeDomains"] = exclude_domains

    return _request(api_key, "/findSimilar", payload)
