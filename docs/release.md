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
- `manifest.json` (`version`) and versioned download links in the README/Mac guide

2. Run local checks:

```bash
uv sync --locked --extra dev
uv run --locked python -m pytest
uv run --locked python -m compileall src
uv build
uv run --locked python scripts/build_mcpb.py
npx --yes @anthropic-ai/mcpb@2.1.2 validate manifest.json
uv run --locked python scripts/smoke_desktop.py dist/desktop/*.mcpb
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
6. Builds and validates the MCPB manifest on macOS and smoke-tests the exact bundle launcher
7. Publishes the Python distributions to PyPI via OIDC Trusted Publishing only after both build jobs succeed
8. Creates GitHub Release with the tested Python distributions, `.mcpb` and SHA-256 checksum

The desktop archive uses an explicit source allowlist in `scripts/build_mcpb.py`.
Add new runtime modules there when necessary. Local credentials, `.env`, token
files, virtual environments and Git metadata are never copied by directory glob.
The MCPB has its own artifact, so it is never uploaded to PyPI as a Python package.

## After release

1. Verify GitHub workflow `Release` succeeded
2. Verify package appears on PyPI
3. Smoke test install:

```bash
uvx --from flin-google-keyword-planner-mcp@latest python -c "from flin_google_ads_mcp import __version__; print(__version__)"
```

4. Smoke test MCP tool listing:

```bash
npx -y @modelcontextprotocol/inspector --cli \
  uvx flin-google-keyword-planner-mcp@latest \
  --method tools/list
```

Expected tools:
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
