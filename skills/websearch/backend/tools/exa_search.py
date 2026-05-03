"""
Exa web search tool — search the internet via Exa MCP endpoint.
"""

import os
import sys

_skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _skill_dir not in sys.path:
    sys.path.insert(0, _skill_dir)

from exa_client import ExaError, search


def _get_api_key() -> str:
    """Retrieve optional Exa API key from skill config or env."""
    try:
        from backend.skills_manager import skills_manager
        config = skills_manager.get_skill_config('websearch')
        key = config.get('exa_api_key', '').strip()
        if key:
            return key
    except Exception:
        pass
    return os.environ.get('EXA_API_KEY', '')


def execute(agent: dict, args: dict) -> dict:
    api_key = _get_api_key()

    query = (args.get('query') or '').strip()
    if not query:
        return {'status': 'error', 'message': 'query is required.'}

    num_results = args.get('num_results', 10)

    try:
        return search(api_key=api_key, query=query, num_results=num_results)
    except ExaError as e:
        if e.status_code == 429:
            return {'status': 'error', 'message': 'Exa rate limit exceeded. Try again in a moment.'}
        return {'status': 'error', 'message': f'Exa error ({e.status_code}): {e.message}'}
    except Exception as e:
        return {'status': 'error', 'message': f'Unexpected error: {str(e)}'}
