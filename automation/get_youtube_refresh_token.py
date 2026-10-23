"""One-time local helper to obtain a YouTube refresh token for GitHub Actions.

Run locally only. Register http://localhost:8765/callback as an additional
Authorized redirect URI in the same Google OAuth Web application client first.
Never commit the resulting refresh token or share it in screenshots/logs.
"""
from __future__ import annotations

import os
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REDIRECT_URI = "http://localhost:8765/callback"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        state = query.get("state", [""])[0]
        code = query.get("code", [""])[0]
        error = query.get("error", [""])[0]
        expected = self.server.oauth_state
        if parsed.path != "/callback" or not secrets.compare_digest(state, expected):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid OAuth callback state. You can close this tab.")
            return
        if error:
            self.server.oauth_error = error
        elif code:
            self.server.auth_code = code
        self.send_response(200 if code and not error else 400)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"YouTube authorization received. You can close this tab and return to the terminal.")

    def log_message(self, *_args):
        return


def main() -> int:
    client_id = os.getenv("YOUTUBE_CLIENT_ID", "").strip()
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        print("Set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET as local environment variables first.")
        return 2

    oauth_state = secrets.token_urlsafe(24)
    server = HTTPServer(("127.0.0.1", 8765), CallbackHandler)
    server.timeout = 5
    server.oauth_state = oauth_state
    server.auth_code = None
    server.oauth_error = None
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": oauth_state,
    }
    url = f"{AUTH_URL}?{urlencode(params)}"
    print("Opening Google consent in your browser. If it does not open, copy this URL into your browser:")
    print(url)
    webbrowser.open(url)
    print("Waiting up to 5 minutes for the local OAuth callback...")
    deadline = time.time() + 300
    try:
        while time.time() < deadline and not server.auth_code and not server.oauth_error:
            server.handle_request()
    finally:
        server.server_close()

    if server.oauth_error:
        print(f"Google authorization was not completed ({server.oauth_error}).")
        return 1
    if not server.auth_code:
        print("Timed out waiting for OAuth callback. Try again.")
        return 1

    try:
        response = requests.post(TOKEN_URL, data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": server.auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        }, timeout=25)
    except requests.RequestException as exc:
        print(f"Could not contact Google ({exc.__class__.__name__}).")
        return 1
    if response.status_code != 200:
        print(f"Google token exchange failed (HTTP {response.status_code}). Verify the client and redirect URI.")
        return 1
    token_data = response.json()
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        print("Google did not return a refresh token. Revoke the prior grant and run again with prompt=consent.")
        return 1
    print("\nCopy this value directly into GitHub Actions Secret YOUTUBE_REFRESH_TOKEN.")
    print("Do not commit it or share it. It grants upload access to the authorized YouTube channel.\n")
    print(refresh_token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
