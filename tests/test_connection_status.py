import asyncio
import json
from pathlib import Path

import pytest

from flin_google_ads_mcp import __version__, auth, server
from flin_google_ads_mcp.config import load_settings


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    for key in (
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "GOOGLE_ADS_CLIENT_ID",
        "GOOGLE_ADS_CLIENT_SECRET",
        "GOOGLE_ADS_REFRESH_TOKEN",
        "GOOGLE_ADS_CUSTOMER_ID",
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID",
        "GOOGLE_ADS_USE_PROTO_PLUS",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv(auth.TOKEN_FILE_ENV_VAR, str(tmp_path / "token.json"))
    monkeypatch.setattr(auth, "_runtime_refresh_token", None)
    load_settings.cache_clear()

    def forbidden(*args, **kwargs):
        pytest.fail(
            "connection_status must not access Google, write tokens or start OAuth"
        )

    monkeypatch.setattr(auth, "urlopen", forbidden)
    monkeypatch.setattr(auth, "persist_refresh_token", forbidden)
    monkeypatch.setattr(server, "start_local_authorization_flow", forbidden)
    monkeypatch.setattr(server, "generate_keyword_ideas", forbidden)
    monkeypatch.setattr(server, "generate_keyword_historical_metrics", forbidden)
    yield
    load_settings.cache_clear()


def configure(monkeypatch):
    monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "private-developer")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "private-client")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "private-secret")


def test_missing_configuration_is_safe_and_does_not_create_files(tmp_path):
    result = server.connection_status()
    assert result == {
        "server_version": __version__,
        "configuration_status": "incomplete",
        "auth_status": "unauthenticated",
        "live_access": "not_checked",
        "next_step": "Enter the required Google Ads credentials in the extension settings.",
    }
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("source", ["env", "file", "runtime"])
def test_local_token_is_not_authenticated_or_live_checked(
    monkeypatch, tmp_path, source
):
    configure(monkeypatch)
    monkeypatch.setenv("GOOGLE_ADS_CUSTOMER_ID", "1234567890")
    monkeypatch.setenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "9876543210")
    if source == "file":
        (tmp_path / "token.json").write_text(
            json.dumps({"refresh_token": "private-token"})
        )
    elif source == "runtime":
        monkeypatch.setattr(auth, "_runtime_refresh_token", "private-token")
    else:
        monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "private-token")
    result = server.connection_status()
    assert result["configuration_status"] == "configured"
    assert result["auth_status"] == "unknown"
    assert result["live_access"] == "not_checked"
    for secret in ("private", "1234567890", "9876543210", str(tmp_path)):
        assert secret not in json.dumps(result)


def test_missing_token_prompts_for_login(monkeypatch):
    configure(monkeypatch)
    monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "   ")
    result = server.connection_status()
    assert result["configuration_status"] == "configured"
    assert result["auth_status"] == "unauthenticated"
    assert "google_ads_start_local_oauth_flow" in result["next_step"]


@pytest.mark.parametrize(
    "field",
    [
        "GOOGLE_ADS_CUSTOMER_ID",
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID",
        "GOOGLE_ADS_USE_PROTO_PLUS",
    ],
)
def test_invalid_settings_are_incomplete_without_echoing_values(monkeypatch, field):
    configure(monkeypatch)
    monkeypatch.setenv(field, "private-invalid-value")
    result = server.connection_status()
    assert result["configuration_status"] == "incomplete"
    assert "private" not in json.dumps(result)


def test_customer_id_can_still_be_supplied_per_query(monkeypatch):
    configure(monkeypatch)
    monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "private-token")
    result = server.connection_status()
    assert result["configuration_status"] == "configured"
    assert "pass customer_id" in result["next_step"]


def test_existing_03_tool_interfaces_and_local_status_annotations():
    def clean(value):
        if isinstance(value, dict):
            return {
                key: clean(item)
                for key, item in value.items()
                if key not in ("title", "description")
            }
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}
    baseline = json.loads(
        (Path(__file__).parent / "fixtures/mcp-0.3-inputs.json").read_text()
    )
    for name, schema in baseline.items():
        assert clean(tools[name].inputSchema) == schema, name
    annotations = tools["connection_status"].annotations
    assert annotations.readOnlyHint and annotations.idempotentHint
    assert not annotations.openWorldHint and not annotations.destructiveHint
    assert tools["connection_status"].inputSchema.get("required", []) == []
