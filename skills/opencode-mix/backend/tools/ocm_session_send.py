"""
OCM Session Send — send a prompt to an active opencode-mix session.
"""
import os
import sys

_backend_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

try:
    from ocm_backend import send_to_session, DEFAULT_TIMEOUT
except ImportError:
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "ocm_backend", os.path.join(_backend_dir, "ocm_backend.py")
    )
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    send_to_session = _mod.send_to_session
    DEFAULT_TIMEOUT = _mod.DEFAULT_TIMEOUT


def execute(agent: dict, args: dict) -> dict:
    """Send a prompt to an active opencode-mix session."""
    session_id = args.get('session_id', '')
    prompt = args.get('prompt', '')
    timeout = args.get('timeout') or DEFAULT_TIMEOUT

    if not session_id or not prompt:
        return {'success': False, 'output': 'session_id and prompt are required'}

    result = send_to_session(session_id, prompt, int(timeout))

    status = 'SUCCESS' if result['success'] else 'FAILED'
    result['_trace'] = {
        'tool': 'ocm_session_send',
        'session_id': session_id,
        'prompt': prompt,
        'status': status,
        'output_preview': result.get('output', '')[:500]
    }

    return result
