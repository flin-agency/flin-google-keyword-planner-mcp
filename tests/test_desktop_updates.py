"""Exercise cache refresh against a real local package index, without PyPI writes."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "desktop_launcher", ROOT / "desktop/server.py"
)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def test_launcher_uses_managed_uv_and_preserves_credentials(monkeypatch, capsys):
    monkeypatch.setenv("UV", "/managed/runtime/uv")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "test-secret")
    for key in (
        "UV_OFFLINE",
        "UV_INDEX",
        "UV_EXCLUDE_NEWER",
        "PIP_INDEX_URL",
        "PYTHONPATH",
        "VIRTUAL_ENV",
    ):
        monkeypatch.setenv(key, "unwanted-setting")
    captured = {}
    monkeypatch.setattr(
        os,
        "execve",
        lambda path, args, env: captured.update(path=path, args=args, env=env),
    )
    launcher.main()
    assert captured["path"] == "/managed/runtime/uv"
    assert captured["args"][-1] == launcher.PACKAGE
    assert (
        captured["args"][captured["args"].index("--from") + 1] == launcher.REQUIREMENT
    )
    assert captured["env"]["GOOGLE_ADS_CLIENT_SECRET"] == "test-secret"
    assert "unwanted-setting" not in json.dumps(captured)
    assert capsys.readouterr().out == ""


def _wheel(directory, version):
    name = "flin_google_keyword_planner_mcp"
    metadata = f"{name}-{version}.dist-info"
    files = {
        "update_probe.py": (
            "import os, json\nfrom pathlib import Path\n"
            f"def main():\n    print({version!r})\n"
            "    assert os.environ['GOOGLE_ADS_CLIENT_SECRET'] == 'preserved-secret'\n"
            "    assert json.loads(Path(os.environ['FLIN_GOOGLE_ADS_TOKEN_FILE']).read_text())['refresh_token'] == 'preserved-token'\n"
        ),
        f"{metadata}/METADATA": f"Metadata-Version: 2.1\nName: {launcher.PACKAGE}\nVersion: {version}\n",
        f"{metadata}/WHEEL": "Wheel-Version: 1.0\nGenerator: update-test\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        f"{metadata}/entry_points.txt": f"[console_scripts]\n{launcher.PACKAGE} = update_probe:main\n",
    }
    files[f"{metadata}/RECORD"] = "".join(
        f"{path},,\n" for path in [*files, f"{metadata}/RECORD"]
    )
    filename = f"{name}-{version}-py3-none-any.whl"
    with ZipFile(directory / filename, "w") as wheel:
        for path, content in files.items():
            wheel.writestr(path, content)
    return filename


def test_new_release_is_used_with_same_cache_and_prereleases_are_skipped(tmp_path):
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv required for the real update integration test")
    index = tmp_path / "simple" / launcher.PACKAGE
    index.mkdir(parents=True)

    class Handler(SimpleHTTPRequestHandler):
        unavailable = False

        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.unavailable:
                self.send_error(503)
            else:
                super().do_GET()

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(Handler, directory=str(tmp_path))
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    args = launcher.tool_args()
    args[args.index("--default-index") + 1] = (
        f"http://127.0.0.1:{server.server_port}/simple"
    )
    args[args.index("--python") + 1] = sys.executable
    args[2:2] = ["--cache-dir", str(tmp_path / "cache")]
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("UV_", "PIP_"))
    }
    token_file = tmp_path / "oauth-token.json"
    token_file.write_text(json.dumps({"refresh_token": "preserved-token"}))
    token_file.chmod(0o600)
    original_token = token_file.read_bytes()
    env.update(
        GOOGLE_ADS_CLIENT_SECRET="preserved-secret",
        FLIN_GOOGLE_ADS_TOKEN_FILE=str(token_file),
    )
    env.update(UV_HTTP_TIMEOUT="1", UV_HTTP_RETRIES="0", UV_PYTHON_DOWNLOADS="never")

    def run():
        return subprocess.run(
            [uv, *args], env=env, capture_output=True, text=True, timeout=30
        )

    def publish(*versions):
        names = [_wheel(index, version) for version in versions]
        (index / "index.html").write_text(
            "\n".join(f'<a href="{name}">{name}</a>' for name in names)
        )

    try:
        publish("0.3.6", "0.4.0")
        first = run()
        assert first.returncode == 0, first.stderr
        assert first.stdout.strip() == "0.4.0"
        publish("0.3.6", "0.4.0", "0.4.1", "0.4.2rc1", "0.5.0", "1.0.0")
        second = run()
        assert second.returncode == 0, second.stderr
        assert second.stdout.strip() == "0.4.1"
        assert token_file.read_bytes() == original_token
        assert token_file.stat().st_mode & 0o777 == 0o600
        Handler.unavailable = True
        unavailable = run()
        assert unavailable.returncode != 0, (
            "Must not silently run an old cached release"
        )
        # Explicit, visible operator fallback only; never part of normal startup.
        fallback = [arg for arg in args if arg != "--refresh"]
        fallback[fallback.index("--from") + 1] = f"{launcher.PACKAGE}==0.4.1"
        fallback[2:2] = ["--offline"]
        pinned = subprocess.run(
            [uv, *fallback], env=env, capture_output=True, text=True, timeout=30
        )
        assert pinned.returncode == 0, pinned.stderr
        assert pinned.stdout.strip() == "0.4.1"
        assert token_file.read_bytes() == original_token
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
