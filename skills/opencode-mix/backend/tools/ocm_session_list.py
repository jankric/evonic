"""
OCM Session List — list all active opencode-mix sessions.
"""
import os
import sys

_backend_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

try:
    from ocm_backend import list_sessions
except ImportError:
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "ocm_backend", os.path.join(_backend_dir, "ocm_backend.py")
    )
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    list_sessions = _mod.list_sessions


def execute(agent: dict, args: dict) -> dict:
    """List all active opencode-mix sessions."""
    sessions = list_sessions()
    return {
        'success': True,
        'count': len(sessions),
        'sessions': sessions
    }
