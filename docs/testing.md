# Testing Guide

This guide covers how to test `flin-google-keyword-planner-mcp`.

## Test levels

1. Local static and unit tests (no Google Ads credentials needed)
2. Local MCP runtime test with Inspector (credentials required)
3. End-to-end test in Claude using `uvx`
4. CI test (GitHub Actions) on each push/PR

## 1) Local static and unit tests

Run these first on every change:

```bash
uv sync --extra dev
python3 -m pytest
python3 -m compileall src
uv build
```

What this validates:

- tool registration and input normalization logic
- Python syntax/import safety
- package can be built into wheel and sdist

## 2) Local MCP runtime test with Inspector

### 2.1 Export credentials in your shell

```bash
export GOOGLE_ADS_DEVELOPER_TOKEN="..."
export GOOGLE_ADS_CLIENT_ID="..."
export GOOGLE_ADS_CLIENT_SECRET="..."
export GOOGLE_ADS_REFRESH_TOKEN="..."
export GOOGLE_ADS_CUSTOMER_ID="1234567890"
export GOOGLE_ADS_LOGIN_CUSTOMER_ID="1234567890"
```

### 2.2 List tools

```bash
npx -y @modelcontextprotocol/inspector --cli \
  uv run flin-google-keyword-planner-mcp \
  --method tools/list
```

Expected:

- `keyword_research`

### 2.3 Smoke test `keyword_research`

Keyword seed example:

```bash
npx -y @modelcontextprotocol/inspector --cli \
  uv run flin-google-keyword-planner-mcp \
  --method tools/call \
  --tool-name keyword_research \
  --tool-arg customer_id=1234567890 \
  --tool-arg login_customer_id=1234567890 \
  --tool-arg 'keywords=["running shoes","trail shoes"]' \
  --tool-arg language_id=1000 \
  --tool-arg 'location_ids=["2840"]' \
  --tool-arg network=GOOGLE_SEARCH_AND_PARTNERS \
  --tool-arg limit=20
```

URL seed example:

```bash
npx -y @modelcontextprotocol/inspector --cli \
  uv run flin-google-keyword-planner-mcp \
  --method tools/call \
  --tool-name keyword_research \
  --tool-arg customer_id=1234567890 \
  --tool-arg login_customer_id=1234567890 \
  --tool-arg url=https://example.com \
  --tool-arg limit=20
```

## 3) End-to-end test in Claude (uvx)

Use this config:

```json
{
  "mcpServers": {
    "flin-google-keyword-planner-mcp": {
      "command": "uvx",
      "args": ["flin-google-keyword-planner-mcp@latest"],
      "env": {
        "GOOGLE_ADS_DEVELOPER_TOKEN": "xxx",
        "GOOGLE_ADS_CLIENT_ID": "xxx",
        "GOOGLE_ADS_CLIENT_SECRET": "xxx",
        "GOOGLE_ADS_REFRESH_TOKEN": "xxx",
        "GOOGLE_ADS_CUSTOMER_ID": "1234567890",
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID": "1234567890"
      }
    }
  }
}
```

Then ask Claude:

1. `Run keyword research for ["running shoes"] with limit 10`
2. `Run keyword research from url https://example.com`

## 4) Common failures and fixes

`missing_configuration`:

- One or more required env vars are missing.
- Fix: compare with `.env.example`.

`PERMISSION_DENIED` / `USER_PERMISSION_DENIED`:

- OAuth user/token is valid but lacks account access or API permissions.
- Fix: confirm account permissions and `login_customer_id` pairing.

Seed validation error:

- Both `keywords` and `url` are empty/missing.
- Fix: pass at least one seed source.

## Recommended release gate

Before each release:

1. `python3 -m pytest`
2. `python3 -m compileall src`
3. `uv build`
4. Inspector smoke tests: `tools/list` and `keyword_research`
