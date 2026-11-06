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
            package = args.pop()
            args.extend(
                [
                    "--from",
                    package,
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
            env={key: "" for key in config["env"]},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = (await session.list_tools()).tools
                assert len(tools) == 10, tools
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
                    "Bundle smoke passed: initialization, 10 tools, read-only annotations, safe missing-config error."
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--expected-version")
    args = parser.parse_args()
    asyncio.run(smoke(args.bundle, args.expected_version))
