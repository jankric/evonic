"""
tavily_search tool — search the web via Tavily API.
"""
import os
import sys

_skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _skill_dir not in sys.path:
    sys.path.insert(0, _skill_dir)

from backend.tavily_client import TavilyError, get_api_key, search


def execute(agent: dict, args: dict) -> dict:
    api_key = get_api_key()

    query = (args.get('query') or '').strip()
    if not query:
        return {'status': 'error', 'message': 'query is required.'}

    num_results = int(args.get('num_results') or 5)
    search_depth = args.get('search_depth') or 'basic'
    topic = args.get('topic') or 'general'
    time_range = args.get('time_range') or None
    include_answer = bool(args.get('include_answer', False))

    try:
        return search(
            api_key=api_key,
            query=query,
            num_results=num_results,
            search_depth=search_depth,
            topic=topic,
            time_range=time_range,
            include_answer=include_answer
        )
    except TavilyError as e:
        if e.status_code == 429:
            return {'status': 'error', 'message': 'Rate limit exceeded. Try again later.'}
        if e.status_code == 401:
            return {'status': 'error', 'message': 'Invalid or missing Tavily API key. Configure it in skill settings.'}
        return {'status': 'error', 'message': f'Tavily error: {e.message}'}
    except Exception as e:
        return {'status': 'error', 'message': f'Unexpected error: {str(e)}'}
