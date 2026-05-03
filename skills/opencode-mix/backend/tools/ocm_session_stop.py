"""
OCM Session Stop — stop and clean up an active opencode-mix session.
"""
import os
import sys

_backend_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

try:
    from ocm_backend import stop_session
except ImportError:
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "ocm_backend", os.path.join(_backend_dir, "ocm_backend.py")
    )
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    stop_session = _mod.stop_session


def execute(agent: dict, args: dict) -> dict:
    """Stop and clean up an active opencode-mix session."""
    session_id = args.get('session_id', '')
    if not session_id:
        return {'success': False, 'output': 'session_id is required'}
    return stop_session(session_id)
