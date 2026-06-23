from __future__ import annotations

from types import ModuleType
from urllib.parse import parse_qs, urlparse
import sys

import pytest

from flin_google_ads_mcp import google_ads
from flin_google_ads_mcp.auth import (
    GOOGLE_ADS_SCOPE,
    build_authorization_url,
    clear_runtime_refresh_token,
    exchange_authorization_code,
    get_effective_refresh_token,
)
from flin_google_ads_mcp.config import ConfigurationError, Settings


def _settings(refresh_token: str | None = None) -> Settings:
    return Settings(
        developer_token="developer-token",
        client_id="client-id",
        client_secret="client-secret",
        refresh_token=refresh_token,
        login_customer_id=None,
        default_customer_id=None,
        use_proto_plus=True,
    )


def test_build_authorization_url_requests_offline_google_ads_access() -> None:
    auth_url = build_authorization_url(
        client_id="client-id",
        redirect_uri="http://localhost:8080/",
        state="csrf-token",
    )

    parsed = urlparse(auth_url)
    params = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "accounts.google.com"
    assert parsed.path == "/o/oauth2/v2/auth"
    assert params["client_id"] == ["client-id"]
    assert params["redirect_uri"] == ["http://localhost:8080/"]
    assert params["response_type"] == ["code"]
    assert params["scope"] == [GOOGLE_ADS_SCOPE]
    assert params["access_type"] == ["offline"]
    assert params["prompt"] == ["consent"]
    assert params["state"] == ["csrf-token"]


def test_exchange_authorization_code_stores_runtime_refresh_token() -> None:
    clear_runtime_refresh_token()

    def fake_token_request(payload: dict[str, str]) -> dict[str, str]:
        assert payload["code"] == "auth-code"
        assert payload["client_id"] == "client-id"
        assert payload["client_secret"] == "client-secret"
        assert payload["redirect_uri"] == "http://localhost:8080/"
        assert payload["grant_type"] == "authorization_code"
        return {"refresh_token": "runtime-refresh-token"}

    token = exchange_authorization_code(
        code="auth-code",
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="http://localhost:8080/",
        token_request=fake_token_request,
    )

    assert token == "runtime-refresh-token"
    assert get_effective_refresh_token(_settings()) == "runtime-refresh-token"


def test_get_effective_refresh_token_prefers_runtime_token() -> None:
    clear_runtime_refresh_token()

    exchange_authorization_code(
        code="auth-code",
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="http://localhost:8080/",
        token_request=lambda _payload: {"refresh_token": "runtime-refresh-token"},
    )

    assert get_effective_refresh_token(_settings("env-refresh-token")) == (
        "runtime-refresh-token"
    )


def test_get_effective_refresh_token_requires_generated_or_env_token() -> None:
    clear_runtime_refresh_token()

    with pytest.raises(ConfigurationError, match="No Google Ads refresh token available"):
        get_effective_refresh_token(_settings())


def test_google_ads_client_uses_regenerated_runtime_refresh_token(monkeypatch) -> None:
    clear_runtime_refresh_token()
    google_ads.load_settings.cache_clear()
    google_ads.clear_google_ads_client_cache()

    monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "developer-token")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "client-secret")

    configs: list[dict[str, object]] = []

    class FakeGoogleAdsClient:
        @staticmethod
        def load_from_dict(config: dict[str, object]) -> object:
            configs.append(config)
            return object()

    fake_client_module = ModuleType("google.ads.googleads.client")
    fake_client_module.GoogleAdsClient = FakeGoogleAdsClient
    monkeypatch.setitem(sys.modules, "google.ads.googleads.client", fake_client_module)

    exchange_authorization_code(
        code="first-code",
        client_id="client-id",
        client_secret="client-secret",
        token_request=lambda _payload: {"refresh_token": "first-token"},
    )
    google_ads.get_google_ads_client()

    exchange_authorization_code(
        code="second-code",
        client_id="client-id",
        client_secret="client-secret",
        token_request=lambda _payload: {"refresh_token": "second-token"},
    )
    google_ads.get_google_ads_client()

    assert [config["refresh_token"] for config in configs] == [
        "first-token",
        "second-token",
    ]
