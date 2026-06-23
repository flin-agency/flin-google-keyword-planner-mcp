from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json

from .config import ConfigurationError, Settings


GOOGLE_ADS_SCOPE = "https://www.googleapis.com/auth/adwords"
GOOGLE_OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_REDIRECT_URI = "http://localhost:8080/"

_runtime_refresh_token: str | None = None
_runtime_refresh_token_version = 0

TokenRequest = Callable[[dict[str, str]], Mapping[str, Any]]


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
    cleaned_code = code.strip()
    if not cleaned_code:
        raise ConfigurationError("Authorization code cannot be blank.")

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
