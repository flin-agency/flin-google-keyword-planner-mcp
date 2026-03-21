# flin-google-keyword-planner-mcp

MCP server for Google Ads Keyword Planner.

This server intentionally exposes exactly one read-only tool: `keyword_research`.

## Exposed MCP tool

- `keyword_research`

## `keyword_research` parameters

- `customer_id` (optional)
- `keywords` (optional list)
- `url` (optional)
- `language_id` (optional, default `1000`)
- `location_ids` (optional list, default `2840` = US)
- `network` (optional, `GOOGLE_SEARCH` or `GOOGLE_SEARCH_AND_PARTNERS`)
- `include_adult_keywords` (optional, default `false`)
- `limit` (optional, default `50`, max `1000`)
- `login_customer_id` (optional)

At least one seed is required: `keywords` and/or `url`.

## Requirements

1. Python 3.10+
2. Google Ads API credentials:
- `GOOGLE_ADS_DEVELOPER_TOKEN`
- `GOOGLE_ADS_CLIENT_ID`
- `GOOGLE_ADS_CLIENT_SECRET`
- `GOOGLE_ADS_REFRESH_TOKEN`

Optional:

- `GOOGLE_ADS_LOGIN_CUSTOMER_ID`
- `GOOGLE_ADS_CUSTOMER_ID` (default customer if no `customer_id` argument is passed)
- `GOOGLE_ADS_USE_PROTO_PLUS` (`true` by default)

## Quickstart (local)

```bash
uv sync --extra dev
cp .env.example .env
# Fill .env with real credentials
uv run flin-google-keyword-planner-mcp
```

## Claude integration

### Option A: Published package (`uvx`)

```json
{
  "mcpServers": {
    "flin-google-keyword-planner-mcp": {
      "command": "uvx",
      "args": ["flin-google-keyword-planner-mcp@latest"],
      "env": {
        "GOOGLE_ADS_DEVELOPER_TOKEN": "REPLACE_ME",
        "GOOGLE_ADS_CLIENT_ID": "REPLACE_ME",
        "GOOGLE_ADS_CLIENT_SECRET": "REPLACE_ME",
        "GOOGLE_ADS_REFRESH_TOKEN": "REPLACE_ME",
        "GOOGLE_ADS_CUSTOMER_ID": "1234567890",
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID": "1234567890",
        "GOOGLE_ADS_USE_PROTO_PLUS": "true"
      }
    }
  }
}
```

### Option B: Local development checkout

```json
{
  "mcpServers": {
    "flin-google-keyword-planner-mcp-local": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/ABSOLUTE/PATH/TO/flin-google-keyword-planner-mcp",
        "flin-google-keyword-planner-mcp"
      ],
      "env": {
        "GOOGLE_ADS_DEVELOPER_TOKEN": "REPLACE_ME",
        "GOOGLE_ADS_CLIENT_ID": "REPLACE_ME",
        "GOOGLE_ADS_CLIENT_SECRET": "REPLACE_ME",
        "GOOGLE_ADS_REFRESH_TOKEN": "REPLACE_ME",
        "GOOGLE_ADS_CUSTOMER_ID": "1234567890",
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID": "1234567890",
        "GOOGLE_ADS_USE_PROTO_PLUS": "true"
      }
    }
  }
}
```

Restart Claude Desktop after config changes.

## Security

- Never commit real credentials to git.
- `.env` and `.env.*` are gitignored; only `.env.example` is tracked.
- Keep secrets in environment variables or secret managers.
- Rotate credentials immediately if accidentally exposed.
- CI and release workflows run secret scanning (`gitleaks`).

## Testing

```bash
uv sync --extra dev
python3 -m pytest
python3 -m compileall src
uv build
```

## Release automation (GitHub + PyPI)

- CI workflow: `.github/workflows/ci.yml`
- Release workflow: `.github/workflows/release.yml`
- Tag push (`v*`) triggers:
1. tests + compile + build + `twine check`
2. publish to PyPI via Trusted Publishing (OIDC)
3. GitHub Release creation with built artifacts

## PyPI Trusted Publishing (one-time)

In the PyPI project `flin-google-keyword-planner-mcp`, add a Trusted Publisher:

- Owner: `flin-agency`
- Repository: `flin-google-keyword-planner-mcp`
- Workflow: `release.yml`
- Environment: `pypi`

## Release steps

```bash
# 1) bump version in pyproject.toml + src/flin_google_ads_mcp/__init__.py
# 2) run checks
python3 -m pytest
python3 -m compileall src
uv build

# 3) release
git add -A
git commit -m "release: vX.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```
