"""
OCM Run — one-shot coding task via opencode-mix.
"""
import os
import sys

# Robust import: add skill backend dir to path only if needed
_backend_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

try:
    from ocm_backend import run_ocm_oneshot, DEFAULT_MODEL, DEFAULT_WORKDIR, DEFAULT_TIMEOUT
except ImportError:
    # Fallback: direct import from file
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "ocm_backend", os.path.join(_backend_dir, "ocm_backend.py")
    )
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    run_ocm_oneshot = _mod.run_ocm_oneshot
    DEFAULT_MODEL = _mod.DEFAULT_MODEL
    DEFAULT_WORKDIR = _mod.DEFAULT_WORKDIR
    DEFAULT_TIMEOUT = _mod.DEFAULT_TIMEOUT


def execute(agent: dict, args: dict) -> dict:
    """Run a one-shot coding task via opencode-mix."""
    task = args.get('task', '')
    workdir = args.get('workdir')
    model = args.get('model')
    variant = args.get('variant')

    if not task:
        return {'success': False, 'output': 'task parameter is required'}

    _model = model or DEFAULT_MODEL
    _workdir = workdir or DEFAULT_WORKDIR
    _timeout = DEFAULT_TIMEOUT

    result = run_ocm_oneshot(task, _workdir, _model, variant, _timeout)

    status = 'SUCCESS' if result['success'] else 'FAILED'
    output_preview = result.get('output', '')[:500]

    result['_trace'] = {
        'tool': 'ocm_run',
        'task': task,
        'workdir': _workdir,
        'model': _model,
        'status': status,
        'output_preview': output_preview,
        'exit_code': result.get('exit_code', -1)
    }

    return result
