#!/usr/bin/env python3
"""
Headless ChatGPT OAuth login helper.
Prints the auth URL, starts a local server on port 1455,
waits for the callback, exchanges tokens, and saves to evonic DB.

Usage:
  cd ~/evonic
  source .venv/bin/activate
  python3 scripts/chatgpt_oauth_login.py
"""
import sys
import os
import time
import secrets
import threading
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Add evonic root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.oauth_refresh import (
    generate_pkce_pair,
    build_authorize_url,
    exchange_code_for_tokens,
    extract_email_from_token,
    extract_plan_from_token,
    OPENAI_OAUTH_REDIRECT_URI,
    OPENAI_OAUTH_CALLBACK_PORT,
)

# ── result container ──────────────────────────────────────────────────────────
_result = {"code": None, "state": None, "error": None, "done": False}


class ReusableHTTPServer(HTTPServer):
    """HTTPServer with SO_REUSEADDR set before bind."""
    allow_reuse_address = True


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/auth/callback":
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(parsed.query)
        _result["code"]  = params.get("code",  [None])[0]
        _result["state"] = params.get("state", [None])[0]
        _result["error"] = params.get("error", [None])[0]
        _result["done"]  = True

        html = (
            "<!DOCTYPE html><html><body style='font-family:sans-serif;text-align:center;padding:60px'>"
            "<h2>✅ Login berhasil!</h2>"
            "<p>Kamu bisa tutup tab ini dan kembali ke terminal.</p>"
            "<script>setTimeout(()=>window.close(),3000)</script>"
            "</body></html>"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, *args):
        pass  # silent


def main():
    # Generate PKCE + state
    code_verifier, code_challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(16)

    auth_url = build_authorize_url(OPENAI_OAUTH_REDIRECT_URI, state, code_challenge)

    print("\n" + "="*60)
    print("  ChatGPT OAuth Login — Headless Mode")
    print("="*60)
    print("\nBuka URL ini di browser kamu:\n")
    print(auth_url)
    print("\n" + "-"*60)
    print(f"Menunggu callback di http://localhost:{OPENAI_OAUTH_CALLBACK_PORT}/callback ...")
    print("(Timeout: 5 menit)\n")

    # Start callback server
    import socket
    server = ReusableHTTPServer(("", OPENAI_OAUTH_CALLBACK_PORT), CallbackHandler)
    server.timeout = 1

    deadline = time.time() + 300
    while time.time() < deadline and not _result["done"]:
        server.handle_request()

    server.server_close()

    if not _result["done"]:
        print("❌ Timeout — tidak ada callback dalam 5 menit.")
        sys.exit(1)

    if _result["error"]:
        print(f"❌ Error dari OpenAI: {_result['error']}")
        sys.exit(1)

    if _result["state"] != state:
        print("❌ State mismatch — kemungkinan CSRF.")
        sys.exit(1)

    code = _result["code"]
    print("✅ Callback diterima. Menukar code dengan token...")

    try:
        token_data = exchange_code_for_tokens(code, OPENAI_OAUTH_REDIRECT_URI, code_verifier)
    except Exception as e:
        print(f"❌ Token exchange gagal: {e}")
        sys.exit(1)

    access_token  = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in    = token_data.get("expires_in", 864000)

    if not access_token or not refresh_token:
        print(f"❌ Response tidak lengkap: {token_data}")
        sys.exit(1)

    email     = extract_email_from_token(access_token) or "unknown@openai.com"
    plan_type = extract_plan_from_token(access_token)
    expires_at = int(time.time() * 1000) + (expires_in * 1000)

    print(f"✅ Token diterima untuk: {email} (plan: {plan_type})")

    # Save to evonic DB
    try:
        from models.db import db
        account = db.create_oauth_account(
            email=email,
            refresh_token=refresh_token,
            access_token=access_token,
            expires_at=expires_at,
            plan_type=plan_type,
            provider="chatgpt",
        )
        print(f"✅ Akun disimpan ke DB (id: {account['id']})")
    except Exception as e:
        print(f"⚠️  Gagal simpan ke DB: {e}")
        print("\nToken mentah (simpan manual jika perlu):")
        print(json.dumps({
            "email": email,
            "plan_type": plan_type,
            "refresh_token": refresh_token,
            "access_token": access_token[:40] + "...",
            "expires_at": expires_at,
        }, indent=2))
        sys.exit(1)

    print("\n" + "="*60)
    print("  Login selesai! Akun ChatGPT OAuth siap dipakai di evonic.")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
