"""
Internal OpenAI OAuth proxy route.
Handles multi-account rotation with auto-fallback on 429.
Mounted at /proxy/openai — acts as OpenAI-compatible endpoint.
"""
import logging
import time
import requests as _requests
from flask import Blueprint, request, jsonify, Response, stream_with_context

from backend.oauth_refresh import get_token_with_fallback, CODEX_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

openai_proxy_bp = Blueprint("openai_proxy", __name__)

OPENAI_BASE = "https://api.openai.com/v1"
MAX_RETRIES = 3


def _get_upstream_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "codex_cli_rs/0.122.0 (linux)",
        "originator": "codex_cli_rs",
    }


def _inject_codex_system_prompt(payload: dict) -> dict:
    """Inject required Codex system prompt as first message."""
    messages = payload.get("messages", [])
    codex_msg = {"role": "system", "content": CODEX_SYSTEM_PROMPT}
    # Only inject if not already present
    if not messages or messages[0].get("content") != CODEX_SYSTEM_PROMPT:
        payload["messages"] = [codex_msg] + messages
    return payload


@openai_proxy_bp.route("/proxy/openai/v1/models", methods=["GET"])
def proxy_models():
    """Return available ChatGPT Plus models."""
    models = [
        {"id": "gpt-5.5", "object": "model", "owned_by": "openai"},
        {"id": "gpt-5.4", "object": "model", "owned_by": "openai"},
        {"id": "gpt-5.4-mini", "object": "model", "owned_by": "openai"},
        {"id": "gpt-5.3-codex", "object": "model", "owned_by": "openai"},
        {"id": "gpt-5.2", "object": "model", "owned_by": "openai"},
        {"id": "codex-auto-review", "object": "model", "owned_by": "openai"},
    ]
    return jsonify({"object": "list", "data": models})


@openai_proxy_bp.route("/proxy/openai/v1/chat/completions", methods=["POST"])
def proxy_chat_completions():
    """Proxy chat completions with multi-account rotation."""
    payload = request.get_json(force=True) or {}
    payload = _inject_codex_system_prompt(payload)
    is_stream = payload.get("stream", False)

    tried_ids = []

    for attempt in range(MAX_RETRIES):
        result = get_token_with_fallback("chatgpt", exclude_ids=tried_ids)
        if not result:
            return jsonify({"error": {"message": "All OAuth accounts exhausted", "type": "rate_limit_error"}}), 429

        account_id, token = result
        tried_ids.append(account_id)
        headers = _get_upstream_headers(token)

        try:
            if is_stream:
                upstream = _requests.post(
                    f"{OPENAI_BASE}/chat/completions",
                    json=payload,
                    headers=headers,
                    stream=True,
                    timeout=(10, 120),
                )
                if upstream.status_code == 429:
                    logger.info("OAuth proxy 429 on account %s, rotating...", account_id)
                    continue
                if upstream.status_code != 200:
                    return jsonify({"error": {"message": f"Upstream error {upstream.status_code}", "type": "api_error"}}), upstream.status_code

                def generate():
                    for chunk in upstream.iter_content(chunk_size=None):
                        yield chunk

                return Response(
                    stream_with_context(generate()),
                    status=upstream.status_code,
                    content_type=upstream.headers.get("Content-Type", "text/event-stream"),
                )
            else:
                upstream = _requests.post(
                    f"{OPENAI_BASE}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=(10, 120),
                )
                if upstream.status_code == 429:
                    logger.info("OAuth proxy 429 on account %s, rotating...", account_id)
                    continue
                return Response(
                    upstream.content,
                    status=upstream.status_code,
                    content_type=upstream.headers.get("Content-Type", "application/json"),
                )

        except Exception as e:
            logger.error("OAuth proxy request failed (account %s): %s", account_id, e)
            continue

    return jsonify({"error": {"message": "All retry attempts failed", "type": "api_error"}}), 500
