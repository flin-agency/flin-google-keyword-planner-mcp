import json
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import HTTPError

import pytest

from flin_google_ads_mcp import auth, google_ads
from flin_google_ads_mcp.config import ConfigurationError, Settings


@pytest.mark.parametrize("error", [RuntimeError, ValueError, OSError])
def test_library_exceptions_do_not_disclose_credentials(error):
    result = google_ads.format_google_ads_error(error("refresh_token=private-secret"))
    assert "private-secret" not in json.dumps(result)


def test_settings_repr_hides_secrets():
    settings = Settings(
        "dev-secret", "client", "client-secret", "refresh-secret", None, None, True
    )
    assert "secret" not in repr(settings)


@pytest.mark.parametrize("proto_plus", [True, False])
def test_google_error_only_exposes_enum_code(proto_plus):
    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException
    from unittest.mock import Mock

    client = GoogleAdsClient(
        credentials=Mock(), developer_token="fake", use_proto_plus=proto_plus
    )
    failure = client.get_type("GoogleAdsFailure")
    error = client.get_type("GoogleAdsError")
    error.message = "private-secret"
    error.error_code.authentication_error = (
        getattr(error.error_code, "_pb", error.error_code)
        .DESCRIPTOR.fields_by_name["authentication_error"]
        .enum_type.values_by_name["OAUTH_TOKEN_INVALID"]
        .number
    )
    failure.errors.append(error)
    result = google_ads.format_google_ads_error(
        GoogleAdsException(Mock(), Mock(), failure, "request-id")
    )
    assert "private-secret" not in json.dumps(result)
    assert "OAUTH_TOKEN_INVALID" in result["errors"][0]["code"]


@pytest.mark.parametrize(
    "redirect",
    [
        "https://example.com/callback",
        "http://localhost.evil/",
        "file:///tmp/x",
        "http://user@localhost:8080/",
    ],
)
def test_manual_oauth_rejects_non_loopback_redirects(redirect):
    with pytest.raises(ConfigurationError):
        auth.build_authorization_url(client_id="client", redirect_uri=redirect)
    with pytest.raises(ConfigurationError):
        auth.exchange_authorization_code(
            code="code",
            client_id="client",
            client_secret="secret",
            redirect_uri=redirect,
        )


def test_oauth_error_description_is_not_reflected():
    with pytest.raises(ConfigurationError) as error:
        auth.exchange_authorization_code(
            code="code",
            client_id="client",
            client_secret="secret",
            token_request=lambda _: {
                "error": "invalid_grant",
                "error_description": "private-secret",
            },
        )
    assert "private-secret" not in str(error.value)


def test_callback_does_not_reflect_untrusted_errors(monkeypatch, tmp_path):
    monkeypatch.setenv(auth.TOKEN_FILE_ENV_VAR, str(tmp_path / "token.json"))
    monkeypatch.setattr(auth, "_local_flow", None)
    flow = auth.start_local_authorization_flow(
        settings=Settings("dev", "id", "secret", None, None, None, True),
        redirect_uri="http://127.0.0.1:0/",
    )
    try:
        query = urlencode(
            {
                "state": flow["state"],
                "error": "denied",
                "error_description": "private-secret",
            }
        )
        with pytest.raises(HTTPError) as error:
            urlopen(flow["redirect_uri"] + "?" + query, timeout=5)
        assert error.value.headers["Cache-Control"] == "no-store"
        assert "private-secret" not in json.dumps(
            auth.get_local_authorization_flow_status()
        )
    finally:
        auth._local_flow.timer.cancel()
        auth._local_flow.server.shutdown()
        auth._local_flow.server.server_close()
