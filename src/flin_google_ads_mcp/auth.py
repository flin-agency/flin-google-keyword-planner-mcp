from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen
import json
import secrets
import threading

from .config import ConfigurationError, Settings


GOOGLE_ADS_SCOPE = "https://www.googleapis.com/auth/adwords"
GOOGLE_OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_REDIRECT_URI = "http://localhost:8080/"

_runtime_refresh_token: str | None = None
_runtime_refresh_token_version = 0
_local_flow: LocalAuthorizationFlow | None = None

TokenRequest = Callable[[dict[str, str]], Mapping[str, Any]]


@dataclass
class LocalAuthorizationFlow:
    server: ThreadingHTTPServer
    authorization_url: str
    redirect_uri: str
    state: str
    status: str = "pending"
    error: str | None = None
    token_available: bool = False


def build_authorization_url(
    *,
    client_id: str,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
    state: str | None = None,
) -> str:
    params = {
        "client_id": client_id.strip(),
        "redirect_uri": redirect_uri.strip(),
        "response_type": "code",
        "scope": GOOGLE_ADS_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    if state:
        params["state"] = state.strip()

    return f"{GOOGLE_OAUTH_AUTH_URL}?{urlencode(params)}"


def clear_runtime_refresh_token() -> None:
    global _runtime_refresh_token, _runtime_refresh_token_version
    _runtime_refresh_token = None
    _runtime_refresh_token_version += 1


def set_runtime_refresh_token(refresh_token: str) -> str:
    token = refresh_token.strip()
    if not token:
        raise ConfigurationError("Google OAuth response did not contain a refresh token.")

    global _runtime_refresh_token, _runtime_refresh_token_version
    _runtime_refresh_token = token
    _runtime_refresh_token_version += 1
    return token


def extract_authorization_code(code_or_url: str) -> str:
    cleaned = code_or_url.strip()
    if not cleaned:
        raise ConfigurationError("Authorization code cannot be blank.")

    parsed = urlparse(cleaned)
    if parsed.scheme and parsed.netloc:
        params = parse_qs(parsed.query)
        if params.get("error"):
            description = params.get("error_description", params["error"])[0]
            raise ConfigurationError(f"Google OAuth authorization failed: {description}")
        code_values = params.get("code")
        if not code_values or not code_values[0].strip():
            raise ConfigurationError(
                "Redirect URL did not contain a code query parameter."
            )
        return code_values[0].strip()

    return cleaned


def get_refresh_token_cache_version() -> int:
    return _runtime_refresh_token_version


def get_effective_refresh_token(settings: Settings) -> str:
    if _runtime_refresh_token:
        return _runtime_refresh_token
    if settings.refresh_token:
        return settings.refresh_token
    raise ConfigurationError(
        "No Google Ads refresh token available. Generate one with "
        "google_ads_authorization_url and google_ads_exchange_authorization_code, "
        "or set GOOGLE_ADS_REFRESH_TOKEN."
    )


def _request_google_token(payload: dict[str, str]) -> Mapping[str, Any]:
    request = Request(
        GOOGLE_OAUTH_TOKEN_URL,
        data=urlencode(payload).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise ConfigurationError(
            f"Google OAuth token exchange failed with HTTP {exc.code}: {details}"
        ) from exc
    except URLError as exc:
        raise ConfigurationError(f"Google OAuth token exchange failed: {exc}") from exc


def exchange_authorization_code(
    *,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
    token_request: TokenRequest | None = None,
) -> str:
    cleaned_code = extract_authorization_code(code)

    payload = {
        "code": cleaned_code,
        "client_id": client_id.strip(),
        "client_secret": client_secret.strip(),
        "redirect_uri": redirect_uri.strip(),
        "grant_type": "authorization_code",
    }
    response = (token_request or _request_google_token)(payload)

    if "error" in response:
        description = response.get("error_description") or response["error"]
        raise ConfigurationError(f"Google OAuth token exchange failed: {description}")

    refresh_token = response.get("refresh_token")
    if not isinstance(refresh_token, str):
        raise ConfigurationError(
            "Google OAuth response did not contain a refresh token. "
            "Generate a fresh authorization URL and approve offline access again."
        )

    return set_runtime_refresh_token(refresh_token)


def _normalize_loopback_redirect_uri(redirect_uri: str) -> tuple[str, str, int, str]:
    parsed = urlparse(redirect_uri.strip())
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise ConfigurationError(
            "Local OAuth flow requires an http://localhost or http://127.0.0.1 redirect_uri."
        )
    if parsed.query or parsed.fragment:
        raise ConfigurationError("Local OAuth redirect_uri cannot include query or fragment.")

    host = parsed.hostname
    port = parsed.port if parsed.port is not None else 80
    path = parsed.path or "/"
    return parsed.geturl(), host, port, path


def _redirect_uri_with_bound_port(redirect_uri: str, bound_port: int) -> str:
    parsed = urlparse(redirect_uri)
    netloc = parsed.hostname or "127.0.0.1"
    if bound_port != 80:
        netloc = f"{netloc}:{bound_port}"
    return urlunparse((parsed.scheme, netloc, parsed.path or "/", "", "", ""))


def _stop_local_flow_server(server: ThreadingHTTPServer) -> None:
    threading.Thread(target=server.shutdown, daemon=True).start()


def start_local_authorization_flow(
    *,
    settings: Settings,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
    token_request: TokenRequest | None = None,
) -> dict[str, str]:
    global _local_flow

    normalized_redirect_uri, host, port, path = _normalize_loopback_redirect_uri(
        redirect_uri
    )

    if _local_flow and _local_flow.status == "pending":
        _stop_local_flow_server(_local_flow.server)

    state = secrets.token_urlsafe(24)
    flow_holder: dict[str, LocalAuthorizationFlow] = {}

    class OAuthCallbackHandler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def do_GET(self) -> None:
            flow = flow_holder["flow"]
            parsed = urlparse(self.path)
            if parsed.path != path:
                self.send_error(404)
                return

            params = parse_qs(parsed.query)
            try:
                returned_state = params.get("state", [""])[0]
                if returned_state != flow.state:
                    raise ConfigurationError("OAuth state did not match.")
                if params.get("error"):
                    description = params.get("error_description", params["error"])[0]
                    raise ConfigurationError(
                        f"Google OAuth authorization failed: {description}"
                    )
                code = params.get("code", [""])[0]
                exchange_authorization_code(
                    code=code,
                    client_id=settings.client_id,
                    client_secret=settings.client_secret,
                    redirect_uri=flow.redirect_uri,
                    token_request=token_request,
                )
                flow.status = "complete"
                flow.token_available = True
                body = "Authentication complete. You may close this browser tab."
                self.send_response(200)
            except Exception as exc:
                flow.status = "error"
                flow.error = str(exc)
                body = f"Authentication failed: {exc}"
                self.send_response(400)

            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            _stop_local_flow_server(flow.server)

    server = ThreadingHTTPServer((host, port), OAuthCallbackHandler)
    actual_redirect_uri = _redirect_uri_with_bound_port(
        normalized_redirect_uri,
        server.server_address[1],
    )
    authorization_url = build_authorization_url(
        client_id=settings.client_id,
        redirect_uri=actual_redirect_uri,
        state=state,
    )
    flow = LocalAuthorizationFlow(
        server=server,
        authorization_url=authorization_url,
        redirect_uri=actual_redirect_uri,
        state=state,
    )
    flow_holder["flow"] = flow
    _local_flow = flow
    threading.Thread(target=server.serve_forever, daemon=True).start()

    return {
        "authorization_url": authorization_url,
        "redirect_uri": actual_redirect_uri,
        "state": state,
    }


def get_local_authorization_flow_status() -> dict[str, Any]:
    if _local_flow is None:
        return {
            "status": "not_started",
            "token_available": bool(_runtime_refresh_token),
            "error": None,
        }

    return {
        "status": _local_flow.status,
        "token_available": _local_flow.token_available or bool(_runtime_refresh_token),
        "error": _local_flow.error,
        "redirect_uri": _local_flow.redirect_uri,
    }
