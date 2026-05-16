from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

GMAIL_COMPOSE_SCOPE = "https://www.googleapis.com/auth/gmail.compose"
DEFAULT_REDIRECT_HOST = "127.0.0.1"
DEFAULT_REDIRECT_PORT = 8765


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a local OAuth flow and print a Gmail refresh token."
    )
    parser.add_argument("--client-id", default=os.getenv("GOOGLE_CLIENT_ID"))
    parser.add_argument("--client-secret", default=os.getenv("GOOGLE_CLIENT_SECRET"))
    parser.add_argument("--port", type=int, default=DEFAULT_REDIRECT_PORT)
    parser.add_argument(
        "--env-path",
        default=".env",
        help="Optional .env file to read GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET from.",
    )
    args = parser.parse_args()

    env_values = read_env(Path(args.env_path))
    client_id = args.client_id or env_values.get("GOOGLE_CLIENT_ID")
    client_secret = args.client_secret or env_values.get("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        print(
            "Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET. "
            "Set them in .env or pass --client-id and --client-secret.",
            file=sys.stderr,
        )
        return 2

    redirect_uri = f"http://{DEFAULT_REDIRECT_HOST}:{args.port}/oauth2callback"
    state = secrets.token_urlsafe(24)
    auth_url = build_authorization_url(
        client_id=client_id,
        redirect_uri=redirect_uri,
        state=state,
    )

    server = OAuthCallbackServer((DEFAULT_REDIRECT_HOST, args.port), OAuthCallbackHandler)
    server.expected_state = state

    print("Opening browser for Gmail OAuth consent...")
    print(f"If the browser does not open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    server.handle_request()
    if server.error:
        print(f"OAuth error: {server.error}", file=sys.stderr)
        return 1
    if not server.authorization_code:
        print("No authorization code was received.", file=sys.stderr)
        return 1

    token_response = exchange_code_for_tokens(
        code=server.authorization_code,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )

    refresh_token = token_response.get("refresh_token")
    if not refresh_token:
        print(
            "Google did not return a refresh_token. "
            "Revoke the app grant in your Google Account permissions and run again.",
            file=sys.stderr,
        )
        print(json.dumps(token_response, indent=2))
        return 1

    print("\nAdd this to your root .env:\n")
    print(f"GOOGLE_REFRESH_TOKEN={refresh_token}")
    return 0


def read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def build_authorization_url(*, client_id: str, redirect_uri: str, state: str) -> str:
    query = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": GMAIL_COMPOSE_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
        }
    )
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"


def exchange_code_for_tokens(
    *,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict[str, Any]:
    payload = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


class OAuthCallbackServer(HTTPServer):
    expected_state: str
    authorization_code: str | None = None
    error: str | None = None


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    server: OAuthCallbackServer

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        if parsed.path != "/oauth2callback":
            self.send_response(404)
            self.end_headers()
            return

        state = first(query.get("state"))
        if state != self.server.expected_state:
            self.server.error = "Invalid OAuth state."
            self.respond("Invalid OAuth state. You can close this tab.", status=400)
            return

        oauth_error = first(query.get("error"))
        if oauth_error:
            self.server.error = oauth_error
            self.respond(f"OAuth error: {oauth_error}. You can close this tab.", status=400)
            return

        self.server.authorization_code = first(query.get("code"))
        self.respond("Gmail authorization complete. You can close this tab.")

    def log_message(self, format: str, *args: object) -> None:
        return

    def respond(self, message: str, *, status: int = 200) -> None:
        body = f"<html><body><p>{message}</p></body></html>".encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def first(values: list[str] | None) -> str | None:
    if not values:
        return None
    return values[0]


if __name__ == "__main__":
    raise SystemExit(main())
