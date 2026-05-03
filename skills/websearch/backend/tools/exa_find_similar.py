"""
Exa find similar tool — discover web pages similar to a given URL.
Uses semantic search via Exa MCP (MCP has no native find_similar).
"""

import os
import sys

_skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _skill_dir not in sys.path:
    sys.path.insert(0, _skill_dir)

from exa_client import ExaError, find_similar


def _get_api_key() -> str:
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

    url = (args.get('url') or '').strip()
    if not url:
        return {'status': 'error', 'message': 'url is required.'}

    num_results = args.get('num_results', 10)

    try:
        return find_similar(api_key=api_key, url=url, num_results=num_results)
    except ExaError as e:
        if e.status_code == 429:
            return {'status': 'error', 'message': 'Exa rate limit exceeded. Try again in a moment.'}
        return {'status': 'error', 'message': f'Exa error ({e.status_code}): {e.message}'}
    except Exception as e:
        return {'status': 'error', 'message': f'Unexpected error: {str(e)}'}
