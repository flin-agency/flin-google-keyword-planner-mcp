"""Verify the actual bundle launcher and all MCP tools without real credentials."""

import argparse
import asyncio
import json
import importlib.util
import subprocess
import tempfile
import time
from pathlib import Path
from zipfile import ZipFile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def smoke(bundle: Path, expected_version: str | None = None) -> None:
    with tempfile.TemporaryDirectory(prefix="flin desktop ") as directory:
        root = Path(directory)
        with ZipFile(bundle) as archive:
            archive.extractall(root)
        manifest = json.loads((root / "manifest.json").read_text())
        config = manifest["server"]["mcp_config"]
        if expected_version:
            spec = importlib.util.spec_from_file_location(
                "launcher", root / "desktop/server.py"
            )
            launcher = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(launcher)
            args = launcher.tool_args()
            args.pop()  # Replace the console command, keeping the constrained --from.
            args.extend(
                [
                    "python",
                    "-c",
                    "from flin_google_ads_mcp import __version__; print(__version__)",
                ]
            )
            for attempt in range(6):
                result = subprocess.run(
                    [config["command"], *args],
                    env=launcher.runtime_env(),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode == 0 and result.stdout.strip() == expected_version:
                    print(f"Latest PyPI version verified: {expected_version}")
                    break
                if attempt == 5:
                    raise RuntimeError(
                        f"Expected latest PyPI version {expected_version}; got {result.stdout!r}: {result.stderr}"
                    )
                time.sleep(5)
        params = StdioServerParameters(
            command=config["command"],
            args=[arg.replace("${__dirname}", directory) for arg in config["args"]],
            env={
                **{key: "" for key in config["env"]},
                "FLIN_GOOGLE_ADS_TOKEN_FILE": str(root / "test-token.json"),
            },
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = (await session.list_tools()).tools
                assert len(tools) in {10, 11}, tools
                has_status = any(tool.name == "connection_status" for tool in tools)
                if expected_version:
                    assert has_status, "Published server must provide connection_status"
                if has_status:
                    status = json.loads(
                        (await session.call_tool("connection_status", {}))
                        .content[0]
                        .text
                    )
                    assert status["configuration_status"] == "incomplete"
                    assert status["auth_status"] == "unauthenticated"
                    assert status["live_access"] == "not_checked"
                    if expected_version:
                        assert status["server_version"] == expected_version
                keyword_tools = [
                    tool for tool in tools if tool.name.startswith("keyword_")
                ]
                assert len(keyword_tools) == 6
                assert all(tool.annotations.readOnlyHint for tool in keyword_tools)
                response = await session.call_tool(
                    "keyword_ideas_from_keywords", {"keywords": ["hiking"]}
                )
                payload = json.loads(response.content[0].text)
                assert payload["ok"] is False
                assert (
                    "Missing required environment variables"
                    in payload["error"]["message"]
                )
                print(
                    f"Bundle smoke passed: initialization, {len(tools)} tools, read-only annotations, safe missing-config error."
                )
        if has_status:
            # Restart the same extracted extension with fake saved credentials.
            # No Google calls: only local connection_status is exercised.
            token_file = root / "test-token.json"
            token_file.write_text('{"refresh_token":"smoke-private-token"}\n')
            token_file.chmod(0o600)
            original = token_file.read_bytes()
            params.env.update(
                {
                    "GOOGLE_ADS_DEVELOPER_TOKEN": "smoke-private-developer",
                    "GOOGLE_ADS_CLIENT_ID": "smoke-private-client",
                    "GOOGLE_ADS_CLIENT_SECRET": "smoke-private-secret",
                    "GOOGLE_ADS_CUSTOMER_ID": "1234567890",
                }
            )
            for _ in range(2):
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        status = json.loads(
                            (await session.call_tool("connection_status", {}))
                            .content[0]
                            .text
                        )
                        assert status["configuration_status"] == "configured"
                        assert status["auth_status"] == "unknown"
                        assert status["live_access"] == "not_checked"
                        assert "smoke-private" not in json.dumps(status)
                        if expected_version:
                            assert status["server_version"] == expected_version
                assert token_file.read_bytes() == original
                assert token_file.stat().st_mode & 0o777 == 0o600
            print(
                "Repeated starter checks preserve configured credentials and private token file."
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--expected-version")
    args = parser.parse_args()
    asyncio.run(smoke(args.bundle, args.expected_version))
