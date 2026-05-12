"""
OAuth token refresh and PKCE utilities for ChatGPT/OpenAI subscription auth.
"""
import hashlib
import base64
import secrets
import time
import logging
import requests
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# OpenAI OAuth constants
OPENAI_AUTH_URL = "https://auth.openai.com/oauth/authorize"
OPENAI_TOKEN_URL = "https://auth.openai.com/oauth/token"
OPENAI_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
OPENAI_API_BASE = "https://api.openai.com/v1"

# Codex system prompt required by OpenAI for OAuth-based API access
CODEX_SYSTEM_PROMPT = (
    "You are Codex, based on GPT-5. You are running as a coding agent "
    "in the Codex CLI on a user's machine."
)

# Refresh buffer: refresh token if it expires within this many seconds
REFRESH_BUFFER_SECONDS = 300  # 5 minutes


def generate_pkce_pair() -> Tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge (S256)."""
    code_verifier = secrets.token_urlsafe(43)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b'=').decode()
    return code_verifier, code_challenge


def build_authorize_url(redirect_uri: str, state: str, code_challenge: str) -> str:
    """Build the OpenAI OAuth authorization URL with PKCE."""
    params = {
        "client_id": OPENAI_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid profile email offline_access",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    query = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    return f"{OPENAI_AUTH_URL}?{query}"


def exchange_code_for_tokens(code: str, redirect_uri: str, code_verifier: str) -> Dict[str, Any]:
    """Exchange authorization code for access + refresh tokens."""
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": OPENAI_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }
    response = requests.post(OPENAI_TOKEN_URL, data=data, timeout=30)
    if response.status_code != 200:
        logger.error("Token exchange failed: %s %s", response.status_code, response.text)
        raise Exception(f"Token exchange failed: {response.status_code} - {response.text}")
    return response.json()


def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """Refresh an access token using the refresh token."""
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": OPENAI_CLIENT_ID,
    }
    response = requests.post(OPENAI_TOKEN_URL, data=data, timeout=30)
    if response.status_code != 200:
        logger.error("Token refresh failed: %s %s", response.status_code, response.text)
        raise Exception(f"Token refresh failed: {response.status_code} - {response.text}")
    return response.json()


def decode_jwt_claims(token: str) -> Dict[str, Any]:
    """Decode JWT payload without verification (for extracting email/plan)."""
    import json
    parts = token.split('.')
    if len(parts) != 3:
        return {}
    # Add padding
    payload = parts[1]
    payload += '=' * (4 - len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception:
        return {}


def extract_email_from_token(access_token: str) -> Optional[str]:
    """Extract email from JWT access token."""
    claims = decode_jwt_claims(access_token)
    profile = claims.get("https://api.openai.com/profile", {})
    return profile.get("email")


def extract_plan_from_token(access_token: str) -> str:
    """Extract plan type from JWT access token."""
    claims = decode_jwt_claims(access_token)
    auth_info = claims.get("https://api.openai.com/auth", {})
    return auth_info.get("chatgpt_plan_type", "plus")


def is_token_expired(expires_at: int) -> bool:
    """Check if token is expired or will expire within buffer."""
    if not expires_at:
        return True
    now_ms = int(time.time() * 1000)
    buffer_ms = REFRESH_BUFFER_SECONDS * 1000
    return now_ms >= (expires_at - buffer_ms)


def get_valid_access_token(account_id: str) -> Optional[str]:
    """Get a valid access token for an OAuth account, refreshing if needed.
    
    Returns the access token string or None if refresh fails.
    """
    from models.db import db

    account = db.get_oauth_account(account_id)
    if not account:
        logger.warning("OAuth account not found: %s", account_id)
        return None

    if account['status'] != 'active':
        logger.warning("OAuth account %s is not active (status=%s)", account_id, account['status'])
        return None

    # Check if token needs refresh
    if not is_token_expired(account.get('expires_at')):
        return account.get('access_token')

    # Refresh the token
    logger.info("Refreshing OAuth token for account %s (%s)", account_id, account.get('email'))
    try:
        result = refresh_access_token(account['refresh_token'])
        new_access = result.get('access_token')
        new_refresh = result.get('refresh_token', account['refresh_token'])
        expires_in = result.get('expires_in', 864000)
        new_expires_at = int(time.time() * 1000) + (expires_in * 1000)

        # Update DB with new tokens
        db.update_oauth_tokens(
            account_id,
            refresh_token=new_refresh,
            access_token=new_access,
            expires_at=new_expires_at
        )
        logger.info("OAuth token refreshed successfully for %s", account.get('email'))
        return new_access

    except Exception as e:
        logger.error("Failed to refresh OAuth token for %s: %s", account.get('email'), e)
        db.update_oauth_status(account_id, 'expired')
        return None


def refresh_all_expiring_accounts():
    """Background job: refresh all accounts that are about to expire."""
    from models.db import db

    accounts = db.get_active_oauth_accounts('chatgpt')
    refreshed = 0
    for account in accounts:
        if is_token_expired(account.get('expires_at')):
            token = get_valid_access_token(account['id'])
            if token:
                refreshed += 1
    if refreshed:
        logger.info("OAuth refresh job: refreshed %d accounts", refreshed)
