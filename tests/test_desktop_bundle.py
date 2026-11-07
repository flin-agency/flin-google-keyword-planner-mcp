import hashlib
import importlib.util
import json
from pathlib import Path
from zipfile import ZipFile

from flin_google_ads_mcp import __version__

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "build_mcpb", ROOT / "scripts/build_mcpb.py"
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_bundle_is_reproducible_and_excludes_unlisted_secrets(tmp_path):
    import shutil

    root = tmp_path / "source"
    for name in builder.FILES:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    (root / ".env").write_text("DO_NOT_SHIP=private-secret")
    (root / "src/flin_google_ads_mcp/oauth-token.json").write_text("private-secret")
    bundle = builder.build_bundle(root, tmp_path / "first")
    second = builder.build_bundle(root, tmp_path / "second")
    assert bundle.read_bytes() == second.read_bytes()
    alias = bundle.parent / "flin-google-keyword-planner-mcp.mcpb"
    assert alias.read_bytes() == bundle.read_bytes()
    assert (
        alias.with_suffix(".mcpb.sha256").read_text().split()[0]
        == hashlib.sha256(alias.read_bytes()).hexdigest()
    )
    assert (
        bundle.with_suffix(".mcpb.sha256").read_text().split()[0]
        == hashlib.sha256(bundle.read_bytes()).hexdigest()
    )
    with ZipFile(bundle) as archive:
        assert set(archive.namelist()) == set(builder.FILES)
        assert all(
            b"private-secret" not in archive.read(name) for name in archive.namelist()
        )


def test_manifest_runs_independent_launcher_and_protects_secret_fields():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    assert manifest["version"] == __version__
    args = manifest["server"]["mcp_config"]["args"]
    assert "--no-project" in args and "--no-config" in args
    assert "--locked" not in args
    for field in ("developer_token", "client_secret", "refresh_token"):
        assert manifest["user_config"][field]["sensitive"] is True
        assert field not in " ".join(args)


def test_03_extension_settings_identity_and_token_location_remain_compatible():
    from flin_google_ads_mcp.auth import DEFAULT_TOKEN_FILE

    manifest = json.loads((ROOT / "manifest.json").read_text())
    assert manifest["name"] == "flin-google-keyword-planner-mcp"
    required = {"developer_token", "client_id", "client_secret", "customer_id"}
    optional = {"login_customer_id", "refresh_token"}
    assert set(manifest["user_config"]) == required | optional
    for field in required | optional:
        assert manifest["user_config"][field]["required"] == (field in required)
        assert (
            manifest["server"]["mcp_config"]["env"][f"GOOGLE_ADS_{field.upper()}"]
            == "${user_config." + field + "}"
        )
    assert (
        DEFAULT_TOKEN_FILE
        == Path.home() / ".config/flin-google-keyword-planner-mcp/oauth-token.json"
    )


def test_bundle_rejects_symlinked_sources(tmp_path):
    import pytest

    (tmp_path / "manifest.json").symlink_to(ROOT / "manifest.json")
    with pytest.raises(ValueError, match="regular bundle source"):
        builder.build_bundle(tmp_path, tmp_path / "out")
