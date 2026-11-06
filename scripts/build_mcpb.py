"""Build a reproducible MCPB ZIP from an explicit file allowlist, never the cwd."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "manifest.json",
    "pyproject.toml",
    "uv.lock",
    "README.md",
    "LICENSE",
    "docs/claude-desktop-mac.md",
    "desktop/server.py",
    "src/flin_google_ads_mcp/__init__.py",
    "src/flin_google_ads_mcp/auth.py",
    "src/flin_google_ads_mcp/config.py",
    "src/flin_google_ads_mcp/google_ads.py",
    "src/flin_google_ads_mcp/server.py",
)


def build_bundle(root: Path, output: Path) -> Path:
    manifest = json.loads((root / "manifest.json").read_text())
    output.mkdir(parents=True, exist_ok=True)
    bundle = output / f"{manifest['name']}-{manifest['version']}-mac.mcpb"
    with ZipFile(bundle, "w", compression=ZIP_DEFLATED) as archive:
        for name in sorted(FILES):
            source = root / name
            if source.is_symlink() or not source.is_file():
                raise ValueError(f"Expected a regular bundle source file: {name}")
            if not source.resolve().is_relative_to(root.resolve()):
                raise ValueError(f"Bundle source escapes project: {name}")
            info = ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())
    digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
    bundle.with_suffix(".mcpb.sha256").write_text(f"{digest}  {bundle.name}\n")
    return bundle


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "desktop")
    args = parser.parse_args()
    print(build_bundle(ROOT, args.output))
