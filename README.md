# flin-google-keyword-planner-mcp

MCP server for Google Ads Keyword Planner ideas.

This server exposes focused read-only tools so an LLM can clearly choose the right seed strategy.

## Exposed MCP tools

- `keyword_ideas_from_keywords`
- `keyword_ideas_from_url`
- `keyword_ideas_from_keyword_and_url`
- `keyword_ideas_from_site`
- `keyword_ideas_historical`
- `keyword_historical_metrics`

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

## Common optional parameters (keyword idea tools)

- `customer_id`
- `language_id` (default `1000`)
- `location_ids` (default `2840` = US; `[]` = all locations; max 10 unique IDs)
- `network` (`GOOGLE_SEARCH` or `GOOGLE_SEARCH_AND_PARTNERS`; default includes partners)
- `include_adult_keywords` (default `false`)
- `limit` (page size: default `50`, max `1000`; Google may return fewer rows)
- `include_average_cpc` (default `false`; also available on all four seed tools)
- `page_token`
- `keyword_annotation` (currently: `KEYWORD_CONCEPT`)
- `aggregate_metric_types` (currently: `DEVICE`)
- `login_customer_id`

### 6) `keyword_historical_metrics`

Fetch historical search volumes and bids for an existing list of up to 10,000
keywords using Google's `GenerateKeywordHistoricalMetrics` endpoint. It does not
expand the list into new ideas. `keyword_ideas_historical` keeps its original
behavior: discovering ideas with a historical date range.

Required: `keywords`. Optional: customer, language, locations, network, adult
keywords, manager ID, and `include_average_cpc`. Omit dates for Google's default
past 12 months, or supply all four year/month fields. Google controls historical
data availability and may omit unavailable months.

Results include close variants and `unmatched_keywords`. Google can combine similar
keywords, so the result count need not match the input count; an unmatched term is
not evidence of zero search volume. Pagination and idea annotations do not apply.

## Data interpretation and targeting

- Defaults remain **English / US / Search and Partners** for compatibility. For
  German Switzerland, explicitly pass `language_id="1001"`, `location_ids=["2756"]`.
  Use `network="GOOGLE_SEARCH"` for Google Search alone.
- Responses echo their targeting. Bid amounts and CPC use the Google Ads customer
  account's currency; do not assume USD or CHF from the target location.
- Missing optional metrics are `null`; genuine reported zeroes remain `0`.
- Competition and competition index measure **advertiser competition**, not SEO difficulty.
- Search volumes are approximate and may group close variants.
- Idea seeds accept at most 20 unique keywords. URL seeds require absolute HTTP(S) URLs.
- Each ideas call returns one API page. Continue with `next_page_token` and identical
  request parameters. A short or empty page does not imply the end if a token exists.
- Requests use a 30-second RPC timeout and a 45-second retry window for transient
  transport errors. The last in-flight RPC may extend beyond that window. Quota and
  authentication errors are not automatically retried.

## Requirements

1. Python 3.10+
2. Google Ads API credentials:
- `GOOGLE_ADS_DEVELOPER_TOKEN`
- `GOOGLE_ADS_CLIENT_ID`
- `GOOGLE_ADS_CLIENT_SECRET`

Optional:

- `GOOGLE_ADS_REFRESH_TOKEN` (only needed if you want a persistent token instead of generating one in Claude)
- `GOOGLE_ADS_LOGIN_CUSTOMER_ID`
- `GOOGLE_ADS_CUSTOMER_ID` (default customer if no `customer_id` argument is passed)
- `GOOGLE_ADS_USE_PROTO_PLUS` (`true` by default)

## Quickstart (local)

```bash
uv sync --locked --extra dev
cp .env.example .env
# Fill .env with real credentials
uv run --env-file .env flin-google-keyword-planner-mcp
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
        "GOOGLE_ADS_CUSTOMER_ID": "1234567890",
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID": "1234567890",
        "GOOGLE_ADS_USE_PROTO_PLUS": "true"
      }
    }
  }
}
```

Restart Claude Desktop after config changes.

### Generate the refresh token in Claude

After Claude has loaded the MCP, ask it to run:

1. `google_ads_start_local_oauth_flow`
2. Open the returned `authorization_url` in your browser and approve Google Ads access.
3. After the browser shows the local completion page, run `google_ads_oauth_status`.
4. Run the keyword tools once `token_available` is `true`.

The default redirect URI is `http://localhost:8080/`. If your Google OAuth client uses a different loopback redirect URI, pass it to `google_ads_start_local_oauth_flow`.

If you cannot use the local callback flow, use the manual fallback:

1. Run `google_ads_authorization_url`.
2. Open the returned URL and approve access.
3. Copy either the full redirected URL or the `code` query parameter.
4. Run `google_ads_exchange_authorization_code` with that value.

The exchanged refresh token is stored outside Claude config in `~/.config/flin-google-keyword-planner-mcp/oauth-token.json` and reused after MCP restarts. Override the storage path with `FLIN_GOOGLE_ADS_TOKEN_FILE` if needed.

## Security

- Never commit real credentials to git.
- `.env` and `.env.*` are gitignored; only `.env.example` is tracked.
- Keep secrets in environment variables or secret managers.
- Rotate credentials immediately if accidentally exposed.
- CI and release workflows run secret scanning with OSS `gitleaks` (no `GITLEAKS_LICENSE` secret required).

## Testing

```bash
uv sync --locked --extra dev
uv run --locked python -m pytest
uv run --locked python -m compileall src
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
uv run --locked python -m pytest
uv run --locked python -m compileall src
uv build

# 3) release
git add -A
git commit -m "release: vX.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

## Version 0.3.0 upgrade notes

Validated with Google Ads Python SDK 35.0.0 (API v26) and MCP SDK 1.30.0.
The MCP SDK remains on the compatible 1.x line; this is not a migration to MCP 2.x.
`uv.lock` is now tracked so local installs and CI use the same dependency versions.

OAuth exchange returns success and persistence status, **never the refresh token**.
Local OAuth uses PKCE, state validation, a ten-minute expiry, and releases its
callback port after completion. Token files are written atomically with private
permissions. The manual code-copy fallback remains available.

Clients upgrading from 0.2.x must accept nullable metrics, the additional response
metadata, and the removal of `refresh_token` from the OAuth exchange response.
Existing five idea tool names and targeting defaults are retained.

Reference: [Google historical metrics](https://developers.google.com/google-ads/api/docs/keyword-planning/generate-historical-metrics),
[Google keyword ideas](https://developers.google.com/google-ads/api/docs/keyword-planning/generate-keyword-ideas),
[API releases](https://developers.google.com/google-ads/api/docs/release-notes).
