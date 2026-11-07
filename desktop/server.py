"""Launch the latest stable release within the tested 0.3 desktop contract."""

from __future__ import annotations

import os
import shutil
import sys

PACKAGE = "flin-google-keyword-planner-mcp"
# 0.3 keeps the console entry point, credential fields, token path, and ten
# original tool input schemas. A new minor line requires explicit review.
REQUIREMENT = f"{PACKAGE}>=0.3.2,<0.4.0"


def tool_args() -> list[str]:
    return [
        "tool",
        "run",
        "--no-config",
        "--isolated",
        "--default-index",
        "https://pypi.org/simple",
        "--prerelease",
        "disallow",
        "--refresh",
        "--python",
        "3.13",
        "--from",
        REQUIREMENT,
        PACKAGE,
    ]


def runtime_env() -> dict[str, str]:
    # User/global package-manager settings must not pin an old version, switch
    # indexes, enable offline mode or inject additional packages into this launcher.
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("UV_", "PIP_"))
        and key not in {"VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME"}
    }


def main() -> None:
    # `uv run` supplies its own executable via UV, including Claude's managed uv.
    uv = os.environ.get("UV") or shutil.which("uv")
    if not uv:
        print(
            "Claude's UV runtime is unavailable. Update Claude Desktop and restart.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    print(
        "Checking PyPI for the latest stable Google Keyword Planner 0.3.x server. "
        "No automatic offline fallback; see SUPPORT.md if PyPI is unavailable.",
        file=sys.stderr,
    )
    os.execve(uv, [uv, *tool_args()], runtime_env())


if __name__ == "__main__":
    main()
