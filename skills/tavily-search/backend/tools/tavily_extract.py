"""
tavily_extract tool — extract content from URLs via Tavily API.
"""
import os
import sys

_skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _skill_dir not in sys.path:
    sys.path.insert(0, _skill_dir)

from backend.tavily_client import TavilyError, get_api_key, extract


def execute(agent: dict, args: dict) -> dict:
    api_key = get_api_key()

    urls = args.get('urls') or []
    if not urls:
        return {'status': 'error', 'message': 'urls is required.'}
    if isinstance(urls, str):
        urls = [urls]

    query = args.get('query') or None

    try:
        return extract(api_key=api_key, urls=urls, query=query)
    except TavilyError as e:
        if e.status_code == 429:
            return {'status': 'error', 'message': 'Rate limit exceeded. Try again later.'}
        return {'status': 'error', 'message': f'Tavily extract error: {e.message}'}
    except Exception as e:
        return {'status': 'error', 'message': f'Unexpected error: {str(e)}'}
