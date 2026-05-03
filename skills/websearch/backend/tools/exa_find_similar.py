"""
Exa find similar tool — discover web pages similar to a given URL.
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


def _get_default_max_results() -> int:
    try:
        from backend.skills_manager import skills_manager
        config = skills_manager.get_skill_config('websearch')
        return int(config.get('max_results', 10))
    except Exception:
        return 10


def _format_results(raw: dict) -> dict:
    results = []
    for r in raw.get('results', []):
        item = {
            'title': r.get('title', ''),
            'url': r.get('url', ''),
        }
        if r.get('publishedDate'):
            item['published_date'] = r['publishedDate']
        if r.get('author'):
            item['author'] = r['author']
        if r.get('text'):
            item['text'] = r['text']
        if r.get('score') is not None:
            item['relevance_score'] = round(r['score'], 4)
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

    url = (args.get('url') or '').strip()
    if not url:
        return {'status': 'error', 'message': 'url is required.'}

    default_max = _get_default_max_results()
    num_results = args.get('num_results', default_max)
    include_text = args.get('include_text', False)
    include_domains = args.get('include_domains')
    exclude_domains = args.get('exclude_domains')

    try:
        raw = find_similar(
            api_key=api_key,
            url=url,
            num_results=num_results,
            include_text=include_text,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
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
