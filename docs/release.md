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

2. Run local checks:

```bash
uv sync --extra dev
python3 -m pytest
python3 -m compileall src
uv build
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

1. Runs secret scan (`gitleaks` OSS container; no `GITLEAKS_LICENSE` secret needed)
2. Verifies tag version matches `pyproject.toml`
3. Runs tests + compile + build
4. Runs `twine check dist/*`
5. Publishes to PyPI via OIDC Trusted Publishing
6. Creates GitHub Release with `dist/*` artifacts

## After release

1. Verify GitHub workflow `Release` succeeded
2. Verify package appears on PyPI
3. Smoke test install:

```bash
uvx flin-google-keyword-planner-mcp@latest --help
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
- `keyword_ideas_from_keywords`
- `keyword_ideas_from_url`
- `keyword_ideas_from_keyword_and_url`
- `keyword_ideas_from_site`
- `keyword_ideas_historical`
