"""
OAuth routes for ChatGPT/OpenAI subscription authentication.
"""
import secrets
import logging
from flask import Blueprint, redirect, request, jsonify, session, url_for

from backend.oauth_refresh import (
    generate_pkce_pair,
    build_authorize_url,
    exchange_code_for_tokens,
    extract_email_from_token,
    extract_plan_from_token,
    get_valid_access_token,
    OPENAI_CLIENT_ID,
)
from models.db import db

logger = logging.getLogger(__name__)

oauth_bp = Blueprint("oauth", __name__)


@oauth_bp.route("/auth/openai/login")
def openai_login():
    """Initiate OpenAI OAuth PKCE login flow."""
    import config
    redirect_uri = f"http://localhost:{config.PORT}/auth/openai/callback"

    # Generate PKCE pair and state
    code_verifier, code_challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(16)

    # Store in session for callback verification
    session['oauth_code_verifier'] = code_verifier
    session['oauth_state'] = state

    auth_url = build_authorize_url(redirect_uri, state, code_challenge)
    return redirect(auth_url)


@oauth_bp.route("/auth/openai/callback")
def openai_callback():
    """Handle OAuth callback from OpenAI."""
    import config

    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')

    if error:
        logger.error("OAuth callback error: %s - %s", error, request.args.get('error_description'))
        return jsonify({"error": error, "description": request.args.get('error_description')}), 400

    if not code:
        return jsonify({"error": "No authorization code received"}), 400

    # Verify state
    expected_state = session.pop('oauth_state', None)
    if state != expected_state:
        return jsonify({"error": "Invalid state parameter"}), 400

    # Get stored PKCE verifier
    code_verifier = session.pop('oauth_code_verifier', None)
    if not code_verifier:
        return jsonify({"error": "Missing PKCE verifier - please try login again"}), 400

    redirect_uri = f"http://localhost:{config.PORT}/auth/openai/callback"

    try:
        # Exchange code for tokens
        token_data = exchange_code_for_tokens(code, redirect_uri, code_verifier)

        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')
        expires_in = token_data.get('expires_in', 864000)

        if not access_token or not refresh_token:
            return jsonify({"error": "Incomplete token response from OpenAI"}), 500

        # Extract user info from JWT
        email = extract_email_from_token(access_token) or "unknown@openai.com"
        plan_type = extract_plan_from_token(access_token)

        import time
        expires_at = int(time.time() * 1000) + (expires_in * 1000)

        # Save to DB
        account = db.create_oauth_account(
            email=email,
            refresh_token=refresh_token,
            access_token=access_token,
            expires_at=expires_at,
            plan_type=plan_type,
            provider='chatgpt'
        )

        logger.info("OAuth account created/updated: %s (plan=%s)", email, plan_type)

        # Redirect to OAuth accounts page
        return redirect("/oauth-accounts?success=1")

    except Exception as e:
        logger.error("OAuth token exchange failed: %s", e)
        return jsonify({"error": str(e)}), 500


@oauth_bp.route("/api/oauth/accounts", methods=["GET"])
def api_list_oauth_accounts():
    """List all OAuth accounts."""
    accounts = db.get_oauth_accounts()
    # Strip sensitive tokens from response
    safe_accounts = []
    for a in accounts:
        safe = {k: v for k, v in a.items() if k not in ('refresh_token', 'access_token')}
        safe['has_refresh_token'] = bool(a.get('refresh_token'))
        safe['has_access_token'] = bool(a.get('access_token'))
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
        return jsonify({"status": "refreshed", "email": account.get('email'), "expires_at": account.get('expires_at')})
    return jsonify({"error": "Refresh failed - account may need re-login"}), 500


@oauth_bp.route("/oauth-accounts")
def oauth_accounts_page():
    """Render OAuth accounts management page."""
    from flask import render_template
    return render_template("oauth_accounts.html")
