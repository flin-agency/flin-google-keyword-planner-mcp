from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import tempfile
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

from .config import ConfigurationError, Settings

GOOGLE_ADS_SCOPE = "https://www.googleapis.com/auth/adwords"
GOOGLE_OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_REDIRECT_URI = "http://localhost:8080/"
LOCAL_FLOW_TIMEOUT_SECONDS = 600
TOKEN_FILE_ENV_VAR = "FLIN_GOOGLE_ADS_TOKEN_FILE"
DEFAULT_TOKEN_FILE = (
    Path.home() / ".config" / "flin-google-keyword-planner-mcp" / "oauth-token.json"
)

_runtime_refresh_token: str | None = None
_runtime_refresh_token_version = 0
_local_flow: LocalAuthorizationFlow | None = None

TokenRequest = Callable[[dict[str, str]], Mapping[str, Any]]


class OAuthFlowError(ConfigurationError):
    """An OAuth failure with an application-owned, secret-free message."""


def _token_error_message(response: Mapping[str, Any]) -> str:
    # Never reflect Google's error_description or arbitrary error values.
    messages = {
        "invalid_grant": "Google OAuth rejected the code (invalid_grant). Start a new OAuth flow; the code may be expired, already used, or not match the redirect URI or PKCE verifier.",
        "invalid_client": "Google OAuth rejected the client (invalid_client). Check the client ID and client secret belong to the same OAuth client.",
        "unauthorized_client": "Google OAuth rejected this client for code exchange (unauthorized_client). Check the OAuth client configuration.",
        "redirect_uri_mismatch": "Google OAuth rejected the redirect URI (redirect_uri_mismatch). Check the OAuth client's redirect URI.",
        "invalid_scope": "Google OAuth rejected the requested scope (invalid_scope). Check Google Ads OAuth access.",
    }
    error = response.get("error")
    if isinstance(error, str) and error in messages:
        return messages[error]
    return "Google OAuth token exchange failed. Check the OAuth client and use a fresh code."


@dataclass
class LocalAuthorizationFlow:
    server: ThreadingHTTPServer
    authorization_url: str
    redirect_uri: str
    state: str
    code_verifier: str = field(repr=False)
    lock: Any = field(default_factory=threading.Lock, repr=False)
    timer: threading.Timer | None = field(default=None, repr=False)
    status: str = "pending"
    error: str | None = None
    token_available: bool = False


def build_authorization_url(
    *,
    client_id: str,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
    state: str | None = None,
    code_verifier: str | None = None,
) -> str:
    # Desktop flows must not send authorization codes to a remote callback.
    redirect_uri, _, _, _ = _normalize_loopback_redirect_uri(redirect_uri)
    params = {
        "client_id": client_id.strip(),
        "redirect_uri": redirect_uri.strip(),
        "response_type": "code",
        "scope": GOOGLE_ADS_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    if state:
        params["state"] = state.strip()
    if code_verifier:
        params["code_challenge"] = (
            base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode("ascii")).digest()
            )
            .rstrip(b"=")
            .decode("ascii")
        )
        params["code_challenge_method"] = "S256"

    return f"{GOOGLE_OAUTH_AUTH_URL}?{urlencode(params)}"


def clear_runtime_refresh_token() -> None:
    global _runtime_refresh_token, _runtime_refresh_token_version
    _runtime_refresh_token = None
    _runtime_refresh_token_version += 1


def set_runtime_refresh_token(refresh_token: str) -> str:
    token = refresh_token.strip()
    if not token:
        raise ConfigurationError(
            "Google OAuth response did not contain a refresh token."
        )

    global _runtime_refresh_token, _runtime_refresh_token_version
    persist_refresh_token(token)
    _runtime_refresh_token = token
    _runtime_refresh_token_version += 1
    return token


def get_token_file_path() -> Path:
    configured_path = os.getenv(TOKEN_FILE_ENV_VAR)
    if configured_path:
        return Path(configured_path).expanduser()
    return DEFAULT_TOKEN_FILE


def load_persisted_refresh_token() -> str | None:
    token_file = get_token_file_path()
    if not token_file.exists():
        return None

    try:
        payload = json.loads(token_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None
    refresh_token = payload.get("refresh_token")
    if isinstance(refresh_token, str) and refresh_token.strip():
        return refresh_token.strip()
    return None


def persist_refresh_token(refresh_token: str) -> None:
    token_file = get_token_file_path()
    token_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # mkstemp starts with mode 0600. Atomic replace prevents partial reads and
    # avoids following an existing token-file symlink while writing secrets.
    fd, temporary_path = tempfile.mkstemp(prefix=".oauth-", dir=token_file.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"refresh_token": refresh_token}, stream)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, token_file)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def extract_authorization_code(code_or_url: str) -> str:
    cleaned = code_or_url.strip()
    if not cleaned:
        raise ConfigurationError("Authorization code cannot be blank.")

    parsed = urlparse(cleaned)
    if parsed.scheme and parsed.netloc:
        params = parse_qs(parsed.query)
        if params.get("error"):
            raise ConfigurationError(
                "Google OAuth authorization failed. Start a new authorization flow."
            )
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
    persisted_refresh_token = load_persisted_refresh_token()
    if persisted_refresh_token:
        return persisted_refresh_token
    if settings.refresh_token:
        return settings.refresh_token
    raise ConfigurationError(
        "No Google Ads refresh token available. Generate one with "
        "google_ads_authorization_url and google_ads_exchange_authorization_code, "
        "or set GOOGLE_ADS_REFRESH_TOKEN."
    )


def get_refresh_token_source() -> str | None:
    if _runtime_refresh_token:
        return "runtime"
    if load_persisted_refresh_token():
        return "file"
    if (os.getenv("GOOGLE_ADS_REFRESH_TOKEN") or "").strip():
        return "env"
    return None


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
        try:
            error_response = json.loads(exc.read().decode("utf-8"))
        except (OSError, UnicodeError, ValueError):
            error_response = None
        if isinstance(error_response, dict) and "error" in error_response:
            raise OAuthFlowError(_token_error_message(error_response)) from exc
        raise OAuthFlowError(
            f"Google OAuth token exchange failed with HTTP {exc.code}. "
            "Check the OAuth client and generate a fresh authorization code."
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise OAuthFlowError(
            "Google OAuth token endpoint could not be reached."
        ) from exc
    except (UnicodeError, ValueError) as exc:
        raise OAuthFlowError("Google OAuth returned an invalid token response.") from exc


def exchange_authorization_code(
    *,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
    token_request: TokenRequest | None = None,
    code_verifier: str | None = None,
) -> str:
    redirect_uri, _, _, _ = _normalize_loopback_redirect_uri(redirect_uri)
    cleaned_code = extract_authorization_code(code)

    payload = {
        "code": cleaned_code,
        "client_id": client_id.strip(),
        "client_secret": client_secret.strip(),
        "redirect_uri": redirect_uri.strip(),
        "grant_type": "authorization_code",
    }
    if code_verifier:
        payload["code_verifier"] = code_verifier
    response = (token_request or _request_google_token)(payload)

    if not isinstance(response, Mapping):
        raise OAuthFlowError("Google OAuth returned an invalid token response.")
    if "error" in response:
        raise OAuthFlowError(_token_error_message(response))

    refresh_token = response.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token.strip():
        raise OAuthFlowError(
            "Google OAuth response did not contain a refresh token. "
            "Generate a fresh authorization URL and approve offline access again."
        )

    try:
        return set_runtime_refresh_token(refresh_token)
    except OSError as exc:
        raise OAuthFlowError(
            "Google OAuth succeeded, but the refresh token could not be saved. "
            "Check permissions and free space for FLIN_GOOGLE_ADS_TOKEN_FILE, then start a new OAuth flow."
        ) from exc


def _normalize_loopback_redirect_uri(redirect_uri: str) -> tuple[str, str, int, str]:
    parsed = urlparse(redirect_uri.strip())
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise ConfigurationError(
            "Local OAuth flow requires an http://localhost or http://127.0.0.1 redirect_uri."
        )
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise ConfigurationError(
            "Local OAuth redirect_uri cannot include credentials, query or fragment."
        )

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
    def stop() -> None:
        server.shutdown()
        server.server_close()

    threading.Thread(target=stop, daemon=True).start()


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
        _local_flow.status = "cancelled"
    if _local_flow:
        if _local_flow.timer:
            _local_flow.timer.cancel()
        _local_flow.server.shutdown()
        _local_flow.server.server_close()

    state = secrets.token_urlsafe(24)
    code_verifier = secrets.token_urlsafe(64)
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
            returned_state = params.get("state", [""])[0]
            if not secrets.compare_digest(returned_state.encode(), flow.state.encode()):
                self.send_error(400, "OAuth state did not match.")
                return
            with flow.lock:
                if flow.status != "pending":
                    self.send_error(409, "OAuth flow is no longer pending.")
                    return
                flow.status = "exchanging"
            if flow.timer:
                flow.timer.cancel()
            try:
                if params.get("error"):
                    raise OAuthFlowError(
                        "Google OAuth authorization failed. Start a new authorization flow."
                    )
                code = params.get("code", [""])[0]
                if not code.strip():
                    raise OAuthFlowError("Google OAuth callback did not contain a code. Start a new OAuth flow.")
                exchange_authorization_code(
                    code=code,
                    client_id=settings.client_id,
                    client_secret=settings.client_secret,
                    redirect_uri=flow.redirect_uri,
                    token_request=token_request,
                    code_verifier=flow.code_verifier,
                )
                flow.status = "complete"
                flow.token_available = True
                body = "Authentication complete. You may close this browser tab."
                self.send_response(200)
            except Exception as exc:
                flow.status = "error"
                flow.error = (
                    str(exc) if isinstance(exc, OAuthFlowError)
                    else "Authentication failed. Check credentials and start a new OAuth flow."
                )
                body = "Authentication failed. Check OAuth status in your MCP client."
                self.send_response(400)

            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            try:
                self.wfile.write(body.encode("utf-8"))
            finally:
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
        code_verifier=code_verifier,
    )
    flow = LocalAuthorizationFlow(
        server=server,
        authorization_url=authorization_url,
        redirect_uri=actual_redirect_uri,
        state=state,
        code_verifier=code_verifier,
    )
    flow_holder["flow"] = flow
    _local_flow = flow
    threading.Thread(target=server.serve_forever, daemon=True).start()

    def expire() -> None:
        with flow.lock:
            if flow.status != "pending":
                return
            flow.status = "expired"
            flow.error = "OAuth flow expired. Start a new authorization flow."
        _stop_local_flow_server(server)

    flow.timer = threading.Timer(LOCAL_FLOW_TIMEOUT_SECONDS, expire)
    flow.timer.daemon = True
    flow.timer.start()

    return {
        "authorization_url": authorization_url,
        "redirect_uri": actual_redirect_uri,
        "state": state,
    }


def get_local_authorization_flow_status() -> dict[str, Any]:
    token_source = get_refresh_token_source()
    if _local_flow is None:
        return {
            "status": "not_started",
            "token_available": token_source is not None,
            "token_source": token_source,
            "error": None,
        }

    return {
        "status": _local_flow.status,
        "token_available": _local_flow.token_available or token_source is not None,
        "token_source": token_source,
        "error": _local_flow.error,
        "redirect_uri": _local_flow.redirect_uri,
    }
