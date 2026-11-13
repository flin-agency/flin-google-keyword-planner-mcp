from __future__ import annotations

import json
import sys
import time
from types import ModuleType
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

import pytest

from flin_google_ads_mcp import google_ads
from flin_google_ads_mcp.auth import (
    GOOGLE_ADS_SCOPE,
    build_authorization_url,
    clear_runtime_refresh_token,
    exchange_authorization_code,
    get_effective_refresh_token,
    get_local_authorization_flow_status,
    start_local_authorization_flow,
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


@pytest.fixture(autouse=True)
def _isolated_token_file(monkeypatch: pytest.MonkeyPatch, tmp_path):
    from flin_google_ads_mcp import auth

    monkeypatch.setenv("FLIN_GOOGLE_ADS_TOKEN_FILE", str(tmp_path / "oauth-token.json"))
    monkeypatch.setattr(auth, "_local_flow", None)
    clear_runtime_refresh_token()
    yield
    if auth._local_flow:
        if auth._local_flow.timer:
            auth._local_flow.timer.cancel()
        auth._local_flow.server.shutdown()
        auth._local_flow.server.server_close()
    clear_runtime_refresh_token()


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
    assert "include_granted_scopes" not in params
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


def test_exchange_authorization_code_persists_refresh_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    token_file = tmp_path / "oauth-token.json"
    monkeypatch.setenv("FLIN_GOOGLE_ADS_TOKEN_FILE", str(token_file))
    clear_runtime_refresh_token()

    exchange_authorization_code(
        code="auth-code",
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="http://localhost:8080/",
        token_request=lambda _payload: {"refresh_token": "persisted-refresh-token"},
    )
    clear_runtime_refresh_token()

    assert get_effective_refresh_token(_settings()) == "persisted-refresh-token"
    assert json.loads(token_file.read_text(encoding="utf-8")) == {
        "refresh_token": "persisted-refresh-token"
    }


def test_persisted_refresh_token_takes_precedence_over_env_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    token_file = tmp_path / "oauth-token.json"
    monkeypatch.setenv("FLIN_GOOGLE_ADS_TOKEN_FILE", str(token_file))
    token_file.write_text(
        json.dumps({"refresh_token": "persisted-refresh-token"}),
        encoding="utf-8",
    )
    clear_runtime_refresh_token()

    assert get_effective_refresh_token(_settings("expired-env-token")) == (
        "persisted-refresh-token"
    )


def test_local_authorization_status_reports_persisted_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    token_file = tmp_path / "oauth-token.json"
    monkeypatch.setenv("FLIN_GOOGLE_ADS_TOKEN_FILE", str(token_file))
    token_file.write_text(
        json.dumps({"refresh_token": "persisted-refresh-token"}),
        encoding="utf-8",
    )
    clear_runtime_refresh_token()

    status = get_local_authorization_flow_status()

    assert status["status"] == "not_started"
    assert status["token_available"] is True
    assert status["token_source"] == "file"


def test_exchange_authorization_code_accepts_full_redirect_url() -> None:
    clear_runtime_refresh_token()

    def fake_token_request(payload: dict[str, str]) -> dict[str, str]:
        assert payload["code"] == "auth-code"
        return {"refresh_token": "runtime-refresh-token"}

    token = exchange_authorization_code(
        code="http://localhost:8080/?state=csrf-token&code=auth-code&scope=adwords",
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="http://localhost:8080/",
        token_request=fake_token_request,
    )

    assert token == "runtime-refresh-token"


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

    with pytest.raises(
        ConfigurationError, match="No Google Ads refresh token available"
    ):
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


def test_start_local_authorization_flow_exchanges_callback_code() -> None:
    clear_runtime_refresh_token()

    def fake_token_request(payload: dict[str, str]) -> dict[str, str]:
        assert payload["code"] == "callback-code"
        return {"refresh_token": "callback-refresh-token"}

    flow = start_local_authorization_flow(
        settings=_settings(),
        redirect_uri="http://127.0.0.1:0/",
        token_request=fake_token_request,
    )
    parsed_auth_url = urlparse(flow["authorization_url"])
    auth_params = parse_qs(parsed_auth_url.query)

    callback_url = (
        f"{flow['redirect_uri']}?state={auth_params['state'][0]}&code=callback-code"
    )
    with urlopen(callback_url, timeout=5) as response:
        body = response.read().decode("utf-8")

    assert response.status == 200
    assert "Authentication complete" in body

    status = {}
    for _ in range(20):
        status = get_local_authorization_flow_status()
        if status["status"] == "complete":
            break
        time.sleep(0.05)

    assert status["status"] == "complete"
    assert status["token_available"] is True
    assert get_effective_refresh_token(_settings()) == "callback-refresh-token"


def test_token_file_is_private_and_corrupt_shapes_are_ignored(tmp_path, monkeypatch):
    from flin_google_ads_mcp.auth import (
        load_persisted_refresh_token,
        persist_refresh_token,
    )

    token_file = tmp_path / "token.json"
    monkeypatch.setenv("FLIN_GOOGLE_ADS_TOKEN_FILE", str(token_file))
    persist_refresh_token("secret")
    assert token_file.stat().st_mode & 0o777 == 0o600
    assert load_persisted_refresh_token() == "secret"
    for content in ["[]", "null", "1", '"string"', "{broken"]:
        token_file.write_text(content)
        assert load_persisted_refresh_token() is None


def test_failed_persistence_does_not_activate_token(monkeypatch):
    from flin_google_ads_mcp import auth

    def fail(_):
        raise OSError("disk full")

    monkeypatch.setattr(auth, "persist_refresh_token", fail)
    with pytest.raises(OSError):
        auth.set_runtime_refresh_token("not-persisted")
    assert auth._runtime_refresh_token is None


def test_mcp_exchange_never_returns_secret(monkeypatch):
    from flin_google_ads_mcp import server

    monkeypatch.setattr(server, "load_settings", _settings)
    monkeypatch.setattr(
        server, "exchange_authorization_code", lambda **_: "sensitive-token"
    )
    result = server.google_ads_exchange_authorization_code("code")
    assert result["ok"] and result["persisted"] and result["token_available"]
    assert "refresh_token" not in result
    assert "sensitive-token" not in json.dumps(result)


def test_bad_callback_state_does_not_cancel_legitimate_flow():
    from urllib.error import HTTPError

    captured = {}

    def token_request(payload):
        captured.update(payload)
        return {"refresh_token": "test-token"}

    flow = start_local_authorization_flow(
        settings=_settings(),
        redirect_uri="http://127.0.0.1:0/",
        token_request=token_request,
    )
    with pytest.raises(HTTPError) as error:
        urlopen(flow["redirect_uri"] + "?state=wrong&code=bad", timeout=5)
    assert error.value.code == 400
    assert get_local_authorization_flow_status()["status"] == "pending"
    with urlopen(
        flow["redirect_uri"] + "?state=" + flow["state"] + "&code=valid", timeout=5
    ) as response:
        assert response.status == 200
    import base64
    import hashlib

    params = parse_qs(urlparse(flow["authorization_url"]).query)
    expected = (
        base64.urlsafe_b64encode(
            hashlib.sha256(captured["code_verifier"].encode()).digest()
        )
        .rstrip(b"=")
        .decode()
    )
    assert params["code_challenge"] == [expected]
    assert params["code_challenge_method"] == ["S256"]


def test_restart_local_flow_releases_port():
    from flin_google_ads_mcp import auth

    first = start_local_authorization_flow(
        settings=_settings(), redirect_uri="http://127.0.0.1:0/"
    )
    second = start_local_authorization_flow(
        settings=_settings(),
        redirect_uri=first["redirect_uri"],
        token_request=lambda _: {"refresh_token": "test-token"},
    )
    assert first["redirect_uri"] == second["redirect_uri"]
    with urlopen(
        second["redirect_uri"] + "?state=" + second["state"] + "&code=valid", timeout=5
    ) as response:
        assert response.status == 200
    auth._local_flow.server.shutdown()
    auth._local_flow.server.server_close()


def test_local_flow_expires(monkeypatch):
    from flin_google_ads_mcp import auth

    monkeypatch.setattr(auth, "LOCAL_FLOW_TIMEOUT_SECONDS", 0.05)
    start_local_authorization_flow(
        settings=_settings(), redirect_uri="http://127.0.0.1:0/"
    )
    deadline = time.monotonic() + 3
    while (
        get_local_authorization_flow_status()["status"] == "pending"
        and time.monotonic() < deadline
    ):
        time.sleep(0.01)
    assert get_local_authorization_flow_status()["status"] == "expired"


def test_exchange_accepts_additional_granted_scopes():
    assert exchange_authorization_code(
        code="code",
        client_id="id",
        client_secret="secret",
        token_request=lambda _: {
            "refresh_token": "token",
            "scope": GOOGLE_ADS_SCOPE + " https://www.googleapis.com/auth/analytics.readonly",
        },
    ) == "token"


@pytest.mark.parametrize(
    "failure, expected",
    [
        ("invalid_grant", "invalid_grant"),
        ("invalid_client", "invalid_client"),
        ("missing_token", "did not contain a refresh token"),
        ("persistence", "could not be saved"),
        ("network", "could not be reached"),
        ("malformed", "invalid token response"),
        ("unknown", "token exchange failed with HTTP 400"),
        ("unexpected", "Authentication failed"),
    ],
)
def test_callback_reports_safe_failure_reason(monkeypatch, failure, expected):
    from io import BytesIO
    from urllib.error import HTTPError, URLError
    from flin_google_ads_mcp import auth

    def fake_urlopen(*args, **kwargs):
        if failure == "network":
            raise URLError("private-secret")
        if failure == "unexpected":
            raise RuntimeError("private-secret")
        if failure == "unknown":
            raise HTTPError("https://example.com", 400, "private-secret", {}, BytesIO(b"private-secret"))
        if failure in {"invalid_grant", "invalid_client"}:
            body = json.dumps({"error": failure, "error_description": "private-secret"}).encode()
            raise HTTPError("https://example.com", 400, "private-secret", {}, BytesIO(body))
        if failure == "malformed":
            return BytesIO(b"[]")
        if failure == "missing_token":
            return BytesIO(b'{"access_token": "private-secret"}')
        return BytesIO(b'{"refresh_token": "private-secret"}')

    monkeypatch.setattr(auth, "urlopen", fake_urlopen)
    if failure == "persistence":
        def fail_save(_):
            raise PermissionError("private-secret")
        monkeypatch.setattr(auth, "persist_refresh_token", fail_save)

    flow = start_local_authorization_flow(settings=_settings(), redirect_uri="http://127.0.0.1:0/")
    with pytest.raises(HTTPError) as error:
        urlopen(flow["redirect_uri"] + "?state=" + flow["state"] + "&code=code", timeout=5)
    assert error.value.code == 400
    assert "private-secret" not in error.value.read().decode()
    status = get_local_authorization_flow_status()
    assert status["status"] == "error"
    assert expected in status["error"]
    assert "private-secret" not in json.dumps(status)
    assert status["token_available"] is False


@pytest.mark.parametrize('kind, expected', [
    ('certificate', 'TLS_CERTIFICATE_ERROR'), ('tls', 'TLS_ERROR'),
    ('timeout', 'NETWORK_TIMEOUT'), ('dns', 'NETWORK_DNS'),
    ('refused', 'NETWORK_REFUSED'), ('reset', 'NETWORK_RESET'),
])
@pytest.mark.parametrize('wrapped', [False, True])
def test_network_diagnostics_reach_browser_and_status(monkeypatch, kind, expected, wrapped):
    import socket
    import ssl
    from urllib.error import HTTPError, URLError
    from flin_google_ads_mcp import auth

    failures = {
        'certificate': ssl.SSLCertVerificationError(1, 'private-secret'),
        'tls': ssl.SSLError(1, 'private-secret'),
        'timeout': TimeoutError('private-secret'),
        'dns': socket.gaierror(-2, 'private-secret'),
        'refused': ConnectionRefusedError('private-secret'),
        'reset': ConnectionResetError('private-secret'),
    }
    def fail(*args, **kwargs):
        error = failures[kind]
        raise URLError(error) if wrapped else error
    monkeypatch.setattr(auth, 'urlopen', fail)
    flow = start_local_authorization_flow(settings=_settings(), redirect_uri='http://127.0.0.1:0/')
    with pytest.raises(HTTPError) as error:
        urlopen(flow['redirect_uri'] + '?state=' + flow['state'] + '&code=private-code', timeout=5)
    body = error.value.read().decode()
    status = get_local_authorization_flow_status()
    assert status['error_code'] == expected
    assert status['error_stage'] == 'token_exchange'
    assert expected in body
    for secret in ['private-secret', 'private-code', 'client-secret']:
        assert secret not in body + json.dumps(status)


@pytest.mark.parametrize('failure, expected', [
    ('permission', 'TOKEN_STORAGE_PERMISSION'), ('full', 'TOKEN_STORAGE_FULL'),
    ('readonly', 'TOKEN_STORAGE_READ_ONLY'), ('path', 'TOKEN_STORAGE_PATH'),
    ('io', 'TOKEN_STORAGE_IO'),
])
def test_storage_preflight_stops_before_code_exchange(monkeypatch, failure, expected):
    import errno
    from flin_google_ads_mcp import auth, server
    failures = {'permission': errno.EACCES, 'full': errno.ENOSPC,
                'readonly': errno.EROFS, 'path': errno.ENOTDIR, 'io': errno.EIO}
    def fail(*args, **kwargs):
        raise OSError(failures[failure], 'private-secret', '/private-sensitive-path')
    monkeypatch.setattr(auth.tempfile, 'TemporaryDirectory', fail)
    monkeypatch.setattr(server, 'load_settings', _settings)
    def should_not_exchange(*args, **kwargs):
        pytest.fail('Must not consume the authorization code when storage fails')
    monkeypatch.setattr(auth, '_request_google_token', should_not_exchange)
    result = server.google_ads_exchange_authorization_code('private-code')
    assert result['ok'] is False
    assert result['error']['code'] == expected
    assert result['error']['stage'] == 'storage_check'
    assert 'private-' not in json.dumps(result)
    result = server.google_ads_start_local_oauth_flow('http://127.0.0.1:0/')
    assert result['error']['code'] == expected
    assert 'authorization_url' not in result
    assert auth._local_flow is None


def test_preflight_preserves_existing_token_and_cleans_probe(tmp_path, monkeypatch):
    from flin_google_ads_mcp import auth
    token = tmp_path / 'new' / 'directory' / 'token.json'
    monkeypatch.setenv(auth.TOKEN_FILE_ENV_VAR, str(token))
    auth.check_token_storage()
    assert token.parent.stat().st_mode & 0o777 == 0o700
    assert list(token.parent.iterdir()) == []
    auth.persist_refresh_token('existing-token')
    before = token.read_bytes()
    auth.check_token_storage()
    assert token.read_bytes() == before
    assert list(token.parent.iterdir()) == [token]
    token.unlink()
    token.mkdir()
    with pytest.raises(auth.OAuthFlowError) as error:
        auth.check_token_storage()
    assert error.value.code == 'TOKEN_STORAGE_PATH'


def test_save_failure_after_successful_preflight_is_distinct(monkeypatch):
    import errno
    from flin_google_ads_mcp import auth, server
    monkeypatch.setattr(server, 'load_settings', _settings)
    monkeypatch.setattr(auth, '_request_google_token', lambda _: {'refresh_token': 'private-token'})
    def fail(_):
        raise OSError(errno.ENOSPC, 'private-secret')
    monkeypatch.setattr(auth, 'persist_refresh_token', fail)
    result = server.google_ads_exchange_authorization_code('private-code')
    assert result['error']['code'] == 'TOKEN_STORAGE_FULL'
    assert result['error']['stage'] == 'token_save'
    assert 'private-' not in json.dumps(result)
    assert auth._runtime_refresh_token is None


def test_port_collision_is_actionable(monkeypatch):
    import socket
    from flin_google_ads_mcp import server
    monkeypatch.setattr(server, 'load_settings', _settings)
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        result = server.google_ads_start_local_oauth_flow(
            f'http://127.0.0.1:{listener.getsockname()[1]}/')
    assert result['error']['code'] == 'CALLBACK_PORT_IN_USE'
    assert result['error']['stage'] == 'callback_start'
    assert '127.0.0.1:0' in result['error']['message']


def test_unrecognized_google_error_is_not_exposed(monkeypatch):
    from io import BytesIO
    from urllib.error import HTTPError
    from flin_google_ads_mcp import auth, server
    monkeypatch.setattr(server, 'load_settings', _settings)
    def fail(*args, **kwargs):
        raise HTTPError('https://example.com/private-code', 400, 'private-secret', {},
                        BytesIO(b'{"error":"private-secret","error_description":"private-token"}'))
    monkeypatch.setattr(auth, 'urlopen', fail)
    result = server.google_ads_exchange_authorization_code('private-code')
    assert result['error']['code'] == 'GOOGLE_TOKEN_ERROR'
    assert 'HTTP 400' in result['error']['message']
    assert 'private-' not in json.dumps(result)
