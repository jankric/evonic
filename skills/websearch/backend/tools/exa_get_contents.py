"""
Exa get contents tool — fetch and extract text from web pages by URL.
"""

import os
import sys

_skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _skill_dir not in sys.path:
    sys.path.insert(0, _skill_dir)

from exa_client import ExaError, get_contents


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


def _format_results(raw: dict) -> dict:
    results = []
    for r in raw.get('results', []):
        item = {
            'title': r.get('title', ''),
            'url': r.get('url', ''),
        }
        if r.get('text'):
            item['text'] = r['text']
        if r.get('publishedDate'):
            item['published_date'] = r['publishedDate']
        if r.get('author'):
            item['author'] = r['author']
        results.append(item)
    return {
        'status': 'success',
        'total_results': len(results),
        'results': results,
    }


def execute(agent: dict, args: dict) -> dict:
    api_key = _get_api_key()
    if not api_key:
        return {
            'status': 'error',
            'message': 'Exa API key not configured. Ask the admin to set it in Web Search skill settings.',
        }

    urls = args.get('urls')
    if not urls or not isinstance(urls, list) or len(urls) == 0:
        return {'status': 'error', 'message': 'urls is required (list of 1-10 URLs).'}
    if len(urls) > 10:
        return {'status': 'error', 'message': 'Maximum 10 URLs per request.'}

    max_characters = args.get('max_characters', 3000)

    try:
        raw = get_contents(
            api_key=api_key,
            urls=urls,
            max_characters=max_characters,
        )
        return _format_results(raw)
    except ExaError as e:
        if e.status_code == 401:
            return {'status': 'error', 'message': 'Invalid Exa API key. Check the key in skill settings.'}
        if e.status_code == 429:
            return {'status': 'error', 'message': 'Exa API rate limit exceeded. Try again in a moment.'}
        return {'status': 'error', 'message': f'Exa API error ({e.status_code}): {e.message}'}
    except Exception as e:
        return {'status': 'error', 'message': f'Unexpected error: {str(e)}'}
