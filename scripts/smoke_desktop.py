"""Verify the actual bundle launcher and all MCP tools without real credentials."""

import argparse
import asyncio
import json
import tempfile
from pathlib import Path
from zipfile import ZipFile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def smoke(bundle: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="flin desktop ") as directory:
        root = Path(directory)
        with ZipFile(bundle) as archive:
            archive.extractall(root)
        manifest = json.loads((root / "manifest.json").read_text())
        config = manifest["server"]["mcp_config"]
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
    args = parser.parse_args()
    asyncio.run(smoke(args.bundle))
