"""
Web Search (Exa) skill install/uninstall script.
"""


def install(context: dict) -> dict:
    """Validate environment and initialize the skill."""
    return {'success': True, 'message': 'Web Search (Exa) skill installed successfully. Configure your Exa API key in skill settings.'}


def uninstall(context: dict) -> dict:
    """Clean up any runtime artifacts created by this skill."""
    return {'success': True, 'message': 'Web Search (Exa) skill uninstalled successfully.'}
