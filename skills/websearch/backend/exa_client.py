"""
Exa AI client via MCP endpoint (mcp.exa.ai/mcp).

Uses JSON-RPC over SSE transport. Free tier works without API key.
If an API key is provided, it's appended as exaApiKey query param.
"""

import json
import requests
from typing import Any, Dict, List, Optional

EXA_MCP_URL = "https://mcp.exa.ai/mcp"
REQUEST_TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (compatible; Evonic/1.0; WebSearch Skill)"


class ExaError(Exception):
    """Exa API error with status code and message."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Exa error {status_code}: {message}")


def _mcp_call(tool_name: str, arguments: Dict[str, Any], api_key: str = "") -> str:
    """Call an Exa MCP tool and return the text content from the response."""
    url = EXA_MCP_URL
    if api_key:
        url += f"?exaApiKey={api_key}"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "User-Agent": USER_AGENT,
    }

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
        if not resp.ok:
            raise ExaError(resp.status_code, f"HTTP {resp.status_code}: {resp.text[:200]}")

        # Parse SSE response — look for "data:" lines
        text_content = ""
        for line in resp.text.split("\n"):
            if line.startswith("data: "):
                data = json.loads(line[6:])
                # Check for JSON-RPC error
                if "error" in data:
                    err = data["error"]
                    raise ExaError(err.get("code", -1), err.get("message", "Unknown MCP error"))
                # Extract result content
                result = data.get("result", {})
                contents = result.get("content", [])
                for c in contents:
                    if c.get("type") == "text":
                        text_content += c.get("text", "")
                break  # Only one data line expected

        return text_content

    except requests.ConnectionError as e:
        raise ExaError(0, f"Connection error: {e}")
    except requests.Timeout:
        raise ExaError(0, f"Request timed out after {REQUEST_TIMEOUT}s")
    except ExaError:
        raise
    except Exception as e:
        raise ExaError(0, f"Unexpected error: {e}")


def _parse_response(text: str) -> Dict[str, Any]:
    """Parse MCP text response into structured results.

    Handles two formats:
    1. Search: "Title: ...\nURL: ...\nPublished: ...\nAuthor: ...\nHighlights:\n..."
    2. Fetch:  "# title\nURL: ...\nPublished: ...\n\ncontent..."
    Blocks are separated by "\n---\n".
    """
    results = []
    blocks = text.split("\n---\n")
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        item: Dict[str, Any] = {}
        lines = block.split("\n")
        content_lines = []
        in_highlights = False
        in_content = False

        for i, line in enumerate(lines):
            if line.startswith("Title: "):
                item["title"] = line[7:].strip()
                in_highlights = False
                in_content = False
            elif line.startswith("# ") and not item.get("title"):
                # Fetch format: "# title"
                item["title"] = line[2:].strip()
                in_content = False
            elif line.startswith("URL: "):
                item["url"] = line[5:].strip()
                in_highlights = False
                in_content = False
            elif line.startswith("Published: "):
                val = line[11:].strip()
                if val and val != "N/A":
                    item["published_date"] = val
                in_highlights = False
                in_content = False
            elif line.startswith("Author: "):
                val = line[8:].strip()
                if val and val != "N/A":
                    item["author"] = val
                in_highlights = False
                in_content = False
            elif line.startswith("Highlights:"):
                in_highlights = True
                in_content = False
            elif in_highlights:
                if line.strip() and line.strip() != "[...]":
                    content_lines.append(line.strip())
            elif not in_highlights and item.get("url") and not line.startswith(("Title:", "URL:", "Published:", "Author:", "Highlights:")):
                # Fetch format: content after metadata
                if line.strip() or in_content:
                    in_content = True
                    content_lines.append(line)

        if content_lines:
            item["text"] = "\n".join(content_lines).strip()
        if item.get("title") or item.get("url"):
            results.append(item)

    return {
        "status": "success",
        "total_results": len(results),
        "results": results,
    }


def search(
    api_key: str = "",
    query: str = "",
    num_results: int = 10,
    **kwargs,
) -> Dict[str, Any]:
    """Search the web using Exa MCP."""
    arguments: Dict[str, Any] = {"query": query}
    if num_results != 10:
        arguments["numResults"] = min(max(num_results, 1), 100)

    text = _mcp_call("web_search_exa", arguments, api_key)
    return _parse_response(text)


def get_contents(
    api_key: str = "",
    urls: Optional[List[str]] = None,
    max_characters: int = 3000,
) -> Dict[str, Any]:
    """Fetch text content of web pages using Exa MCP."""
    if not urls:
        return {"status": "error", "message": "No URLs provided"}

    arguments: Dict[str, Any] = {"urls": urls[:10]}
    if max_characters != 3000:
        arguments["maxCharacters"] = min(max(max_characters, 1), 100000)

    text = _mcp_call("web_fetch_exa", arguments, api_key)
    return _parse_response(text)


def find_similar(
    api_key: str = "",
    url: str = "",
    num_results: int = 10,
    **kwargs,
) -> Dict[str, Any]:
    """Find similar pages — uses web_search_exa with the URL as query (MCP has no find_similar)."""
    # Fallback: search for the URL content since MCP doesn't have find_similar
    arguments: Dict[str, Any] = {"query": f"pages similar to {url}"}
    if num_results != 10:
        arguments["numResults"] = min(max(num_results, 1), 100)

    text = _mcp_call("web_search_exa", arguments, api_key)
    return _parse_response(text)
