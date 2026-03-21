# flin-google-keyword-planner-mcp

MCP server for Google Ads Keyword Planner ideas.

This server exposes focused read-only tools so an LLM can clearly choose the right seed strategy.

## Exposed MCP tools

- `keyword_ideas_from_keywords`
- `keyword_ideas_from_url`
- `keyword_ideas_from_keyword_and_url`
- `keyword_ideas_from_site`
- `keyword_ideas_historical`

## Tool overview

### 1) `keyword_ideas_from_keywords`

Generate ideas from a keyword list (`KeywordSeed`).

Required:
- `keywords`

### 2) `keyword_ideas_from_url`

Generate ideas from a page URL (`UrlSeed`).

Required:
- `url`

### 3) `keyword_ideas_from_keyword_and_url`

Generate ideas from keyword list + URL (`KeywordAndUrlSeed`).

Required:
- `keywords`
- `url`

### 4) `keyword_ideas_from_site`

Generate ideas from a full site/domain (`SiteSeed`).

Required:
- `site_url`

### 5) `keyword_ideas_historical`

Generate ideas from keywords and constrain historical metrics to a year-month range.

Required:
- `keywords`
- `start_year`
- `start_month`
- `end_year`
- `end_month`

Historical option:
- `include_average_cpc` (default `false`)

## Common optional parameters (all tools)

- `customer_id`
- `language_id` (default `1000`)
- `location_ids` (default `2840` = US)
- `network` (`GOOGLE_SEARCH` or `GOOGLE_SEARCH_AND_PARTNERS`)
- `include_adult_keywords` (default `false`)
- `limit` (default `50`, max `1000`)
- `page_token`
- `keyword_annotation` (currently: `KEYWORD_CONCEPT`)
- `aggregate_metric_types` (currently: `DEVICE`)
- `login_customer_id`

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
