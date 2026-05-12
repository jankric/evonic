"""
OAuth routes for ChatGPT/OpenAI subscription authentication.
Uses a temporary local server on port 1455 to receive the OAuth callback
(matching the fixed redirect_uri registered by Codex CLI).
"""
import secrets
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from flask import Blueprint, redirect, request, jsonify, session

from backend.oauth_refresh import (
    generate_pkce_pair,
    build_authorize_url,
    exchange_code_for_tokens,
    extract_email_from_token,
    extract_plan_from_token,
    get_valid_access_token,
    OPENAI_OAUTH_REDIRECT_URI,
    OPENAI_OAUTH_CALLBACK_PORT,
)
from models.db import db

logger = logging.getLogger(__name__)

oauth_bp = Blueprint("oauth", __name__)

# In-memory store for pending PKCE state (keyed by state param)
_pending_auth: dict = {}


class _CallbackHandler(BaseHTTPRequestHandler):
    """Temporary HTTP handler to receive OAuth callback on port 1455."""

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        state = params.get("state", [None])[0]
        error = params.get("error", [None])[0]

        if error:
            logger.error("OAuth callback error: %s", error)
            self._respond_html(f"<h2>Authentication Error</h2><p>{error}</p>")
            _pending_auth[state] = {"error": error}
            return

        if not code or state not in _pending_auth:
            self._respond_html("<h2>Invalid callback</h2>")
            return

        _pending_auth[state]["code"] = code
        self._respond_html(
            "<h2>Authentication successful!</h2>"
            "<p>You can close this tab and return to Evonic.</p>"
            "<script>setTimeout(()=>window.close(),2000)</script>"
        )

    def _respond_html(self, body: str):
        html = f"<!DOCTYPE html><html><body>{body}</body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        pass  # Suppress default access logs


def _start_callback_server(state: str, code_verifier: str):
    """Start a temporary HTTP server on port 1455, wait for callback, then exchange tokens."""
    _pending_auth[state] = {"code": None}

    server = HTTPServer(("127.0.0.1", OPENAI_OAUTH_CALLBACK_PORT), _CallbackHandler)
    server.timeout = 300  # 5 minute timeout

    def run():
        import time
        deadline = time.time() + 300
        while time.time() < deadline:
            server.handle_request()
            entry = _pending_auth.get(state, {})
            if entry.get("code") or entry.get("error"):
                break
        server.server_close()

        entry = _pending_auth.pop(state, {})
        code = entry.get("code")
        if not code:
            logger.warning("OAuth callback timed out or errored for state=%s", state)
            return

        try:
            import time as _time
            token_data = exchange_code_for_tokens(code, OPENAI_OAUTH_REDIRECT_URI, code_verifier)
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 864000)

            if not access_token or not refresh_token:
                logger.error("Incomplete token response: %s", token_data)
                return

            email = extract_email_from_token(access_token) or "unknown@openai.com"
            plan_type = extract_plan_from_token(access_token)
            expires_at = int(_time.time() * 1000) + (expires_in * 1000)

            db.create_oauth_account(
                email=email,
                refresh_token=refresh_token,
                access_token=access_token,
                expires_at=expires_at,
                plan_type=plan_type,
                provider="chatgpt",
            )
            logger.info("OAuth account saved: %s (plan=%s)", email, plan_type)

        except Exception as e:
            logger.error("Token exchange failed: %s", e)

    t = threading.Thread(target=run, daemon=True)
    t.start()


@oauth_bp.route("/auth/openai/login")
def openai_login():
    """Initiate OpenAI OAuth PKCE login flow."""
    code_verifier, code_challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(16)

    # Start callback server before redirecting
    _start_callback_server(state, code_verifier)

    auth_url = build_authorize_url(OPENAI_OAUTH_REDIRECT_URI, state, code_challenge)
    return redirect(auth_url)


@oauth_bp.route("/api/oauth/proxy-status", methods=["GET"])
def api_oauth_proxy_status():
    """Return which account is currently active in the proxy."""
    import json, os
    auth_file = "/home/mimin/.config/openai-oauth/auth.json"
    # Find active account by matching access_token in auth.json vs DB
    try:
        with open(auth_file) as f:
            auth = json.load(f)
        proxy_token = auth.get('tokens', {}).get('access_token', '')
        accounts = db.get_oauth_accounts()
        for acc in accounts:
            if acc.get('access_token') == proxy_token:
                return jsonify({"active_email": acc['email'], "account_id": acc['id']})
    except Exception:
        pass
    # Fallback: return highest-priority enabled account
    active = db.get_active_oauth_accounts('chatgpt')
    if active:
        return jsonify({"active_email": active[0]['email'], "account_id": active[0]['id']})
    return jsonify({"active_email": None})


@oauth_bp.route("/api/oauth/accounts", methods=["GET"])
def api_list_oauth_accounts():
    """List all OAuth accounts (tokens stripped)."""
    accounts = db.get_oauth_accounts()
    safe_accounts = []
    for a in accounts:
        safe = {k: v for k, v in a.items() if k not in ("refresh_token", "access_token")}
        safe["has_refresh_token"] = bool(a.get("refresh_token"))
        safe["has_access_token"] = bool(a.get("access_token"))
        safe_accounts.append(safe)
    return jsonify(safe_accounts)


@oauth_bp.route("/api/oauth/accounts/<account_id>", methods=["DELETE"])
def api_delete_oauth_account(account_id):
    """Delete an OAuth account."""
    deleted = db.delete_oauth_account(account_id)
    if deleted:
        return jsonify({"status": "deleted"})
    return jsonify({"error": "Account not found"}), 404


@oauth_bp.route("/api/oauth/accounts/<account_id>/refresh", methods=["POST"])
def api_refresh_oauth_account(account_id):
    """Manually trigger token refresh for an account."""
    token = get_valid_access_token(account_id)
    if token:
        account = db.get_oauth_account(account_id)
        return jsonify({
            "status": "refreshed",
            "email": account.get("email"),
            "expires_at": account.get("expires_at"),
        })
    return jsonify({"error": "Refresh failed — account may need re-login"}), 500


@oauth_bp.route("/api/oauth/accounts/<account_id>/toggle", methods=["POST"])
def api_toggle_oauth_account(account_id):
    """Toggle enabled/disabled for an account, then sync proxy to active account."""
    account = db.get_oauth_account(account_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404
    new_state = not bool(account.get('enabled', 1))
    db.set_oauth_enabled(account_id, new_state)

    # Sync proxy to highest-priority enabled account
    from backend.oauth_refresh import sync_proxy_account
    active_email = sync_proxy_account()

    return jsonify({"status": "ok", "enabled": new_state, "proxy_account": active_email})


@oauth_bp.route("/api/oauth/accounts/<account_id>/priority", methods=["POST"])
def api_set_oauth_priority(account_id):
    """Set priority for an account, then sync proxy."""
    data = request.get_json() or {}
    priority = data.get('priority', 0)
    db.set_oauth_priority(account_id, int(priority))

    from backend.oauth_refresh import sync_proxy_account
    active_email = sync_proxy_account()

    return jsonify({"status": "ok", "priority": priority, "proxy_account": active_email})


@oauth_bp.route("/oauth-accounts")
def oauth_accounts_page():
    """Render OAuth accounts management page."""
    from flask import render_template
    return render_template("oauth_accounts.html")
