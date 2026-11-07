# Release Checklist

## One-time setup

1. Create PyPI project: `flin-google-keyword-planner-mcp`
2. Configure Trusted Publishing in PyPI:
- GitHub owner: `flin-agency`
- Repository: `flin-google-keyword-planner-mcp`
- Workflow: `release.yml`
- Environment: `pypi`
3. Ensure GitHub Actions is enabled for the repository
4. Ensure repository secret hygiene:
- no real credentials in tracked files
- use `.env` locally only

## Before each release

1. Update versions:
- `pyproject.toml` (`project.version`)
- `src/flin_google_ads_mcp/__init__.py` (`__version__`)
- `manifest.json` (`version`); keep README on the existing stable download alias

2. Run local checks:

```bash
uv sync --locked --extra dev
uv run --locked python -m pytest
uv run --locked python -m compileall src
uv build
uv run --locked python scripts/build_mcpb.py
npx --yes @anthropic-ai/mcpb@2.1.2 validate manifest.json
uv run --locked python scripts/smoke_desktop.py dist/desktop/flin-google-keyword-planner-mcp.mcpb
```

3. Validate git state:

```bash
git status
```

4. Commit and tag:

```bash
git add -A
git commit -m "release: vX.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

## What `release.yml` does on tag `v*`

1. Runs secret scan (checksum-pinned `gitleaks` OSS binary; no license secret needed)
2. Verifies tag version matches `pyproject.toml`
3. Audits locked dependencies and runs tests + compile + build
4. Runs `twine check dist/*`
5. Uploads the tested distributions as a workflow artifact
6. Builds and validates the MCPB manifest on a runner asserted to be Apple Silicon (`arm64`) and smoke-tests the exact bundle launcher
7. Publishes the Python distributions to PyPI via OIDC Trusted Publishing only after both build jobs succeed
8. Verifies that the unchanged Mac starter resolves the newly published version from PyPI and starts it successfully
9. Creates GitHub Release with the tested Python distributions, versioned `.mcpb`,
   identical `flin-google-keyword-planner-mcp.mcpb` alias and both SHA-256 files

The desktop archive uses an explicit source allowlist in `scripts/build_mcpb.py`.
Add new runtime modules there when necessary. Local credentials, `.env`, token
files, virtual environments and Git metadata are never copied by directory glob.
The MCPB has its own artifact, so it is never uploaded to PyPI as a Python package.

## After release

1. Verify GitHub workflow `Release` succeeded
2. Verify package appears on PyPI
3. Smoke test install:

```bash
uvx --refresh --prerelease disallow --from 'flin-google-keyword-planner-mcp>=0.3.2,<0.4.0' python -c "from flin_google_ads_mcp import __version__; print(__version__)"
```

4. Smoke test MCP tool listing:

```bash
npx -y @modelcontextprotocol/inspector --cli \
  uvx --refresh --prerelease disallow --from 'flin-google-keyword-planner-mcp>=0.3.2,<0.4.0' flin-google-keyword-planner-mcp \
  --method tools/list
```

Expected tools:
- `connection_status`
- `google_ads_authorization_url`
- `google_ads_exchange_authorization_code`
- `google_ads_start_local_oauth_flow`
- `google_ads_oauth_status`
- `keyword_ideas_from_keywords`
- `keyword_ideas_from_url`
- `keyword_ideas_from_keyword_and_url`
- `keyword_ideas_from_site`
- `keyword_ideas_historical`
- `keyword_historical_metrics`

## Automatic server updates (starter 0.3.3+)

The desktop entry point is a standard-library launcher. It runs `uv tool run`
with `--from flin-google-keyword-planner-mcp>=0.3.2,<0.4.0`, `--refresh`, isolated tools, no discovered configuration and stable releases only. It ignores bundled server code and the development lockfile.
Package-manager environment overrides are removed; Google Ads credentials remain.

The update integration test serves real test wheels on loopback, publishes a newer
stable wheel alongside a prerelease and incompatible 0.4/1.0 versions and verifies a second invocation with the same
cache chooses the newer stable release inside the 0.3 boundary. Credentials and
the private token file must survive unchanged. It also checks that an unavailable index
fails instead of silently executing stale code. CI must have uv installed.

Existing starters before 0.3.3 need a one-time starter upgrade. Future server code
updates need only a restart. A changed launcher, configuration schema or required
Python runtime may still require a new MCPB. The startup check requires network
access and intentionally trusts future stable releases of this PyPI project.

The unchanged ten input schemas from 0.3.2 are frozen in
`tests/fixtures/mcp-0.3-inputs.json`; keep these and existing response tests passing
for 0.3 updates. Breaking entry-point, credentials, token path, tool schema or
response semantics require a new compatibility line and starter review. The new
local status tool is additive. Publish every server release to both PyPI and GitHub
with a freshly tested desktop package. A new package does not imply existing users
must import it for a compatible server update.

The post-publication smoke checks `connection_status.server_version` from the
running server, then restarts the same extracted extension with fake credentials
and a token file. Linux CI, Apple-Silicon execution and real provider-account tests
are distinct: the last is not performed by CI. Installation through Claude's UI
and UI-setting retention must not be claimed from a process-level test.
