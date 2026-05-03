"""
OCM Session Start — start an interactive opencode-mix session.
"""
import os
import sys
import time

_backend_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

try:
    from ocm_backend import start_session, send_to_session, DEFAULT_MODEL, DEFAULT_WORKDIR, DEFAULT_TIMEOUT
except ImportError:
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "ocm_backend", os.path.join(_backend_dir, "ocm_backend.py")
    )
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    start_session = _mod.start_session
    send_to_session = _mod.send_to_session
    DEFAULT_MODEL = _mod.DEFAULT_MODEL
    DEFAULT_WORKDIR = _mod.DEFAULT_WORKDIR
    DEFAULT_TIMEOUT = _mod.DEFAULT_TIMEOUT


def execute(agent: dict, args: dict) -> dict:
    """Start an interactive opencode-mix session."""
    workdir = args.get('workdir') or DEFAULT_WORKDIR
    model = args.get('model') or DEFAULT_MODEL
    initial_message = args.get('initial_message')

    session_id = start_session(workdir, model)

    result = {
        'success': True,
        'session_id': session_id,
        'workdir': workdir,
        'model': model,
        'message': f"Session started. Use ocm_session_send with session_id='{session_id}' to send tasks."
    }

    if initial_message:
        time.sleep(2)
        send_result = send_to_session(session_id, initial_message, DEFAULT_TIMEOUT)
        result['initial_output'] = send_result.get('output', '')

    return result
