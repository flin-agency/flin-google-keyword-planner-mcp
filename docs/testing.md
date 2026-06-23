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

- MCP tool registration contract
- input normalization and validation logic
- Python syntax/import safety
- package can be built into wheel and sdist

## 2) Local MCP runtime test with Inspector

### 2.1 Export credentials in your shell

```bash
export GOOGLE_ADS_DEVELOPER_TOKEN="..."
export GOOGLE_ADS_CLIENT_ID="..."
export GOOGLE_ADS_CLIENT_SECRET="..."
# Optional: export this for persistent auth, or generate it with the MCP OAuth tools.
# export GOOGLE_ADS_REFRESH_TOKEN="..."
export GOOGLE_ADS_CUSTOMER_ID="1234567890"
export GOOGLE_ADS_LOGIN_CUSTOMER_ID="1234567890"
```

### 2.2 List tools

```bash
npx -y @modelcontextprotocol/inspector --cli \
  uv run flin-google-keyword-planner-mcp \
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

### 2.3 Smoke tests per tool

Keyword seed:

```bash
npx -y @modelcontextprotocol/inspector --cli \
  uv run flin-google-keyword-planner-mcp \
  --method tools/call \
  --tool-name keyword_ideas_from_keywords \
  --tool-arg customer_id=1234567890 \
  --tool-arg login_customer_id=1234567890 \
  --tool-arg 'keywords=["running shoes","trail shoes"]' \
  --tool-arg limit=20
```

URL seed:

```bash
npx -y @modelcontextprotocol/inspector --cli \
  uv run flin-google-keyword-planner-mcp \
  --method tools/call \
  --tool-name keyword_ideas_from_url \
  --tool-arg customer_id=1234567890 \
  --tool-arg login_customer_id=1234567890 \
  --tool-arg url=https://example.com \
  --tool-arg limit=20
```

Keyword + URL seed:

```bash
npx -y @modelcontextprotocol/inspector --cli \
  uv run flin-google-keyword-planner-mcp \
  --method tools/call \
  --tool-name keyword_ideas_from_keyword_and_url \
  --tool-arg customer_id=1234567890 \
  --tool-arg login_customer_id=1234567890 \
  --tool-arg 'keywords=["running shoes"]' \
  --tool-arg url=https://example.com \
  --tool-arg limit=20
```

Site seed:

```bash
npx -y @modelcontextprotocol/inspector --cli \
  uv run flin-google-keyword-planner-mcp \
  --method tools/call \
  --tool-name keyword_ideas_from_site \
  --tool-arg customer_id=1234567890 \
  --tool-arg login_customer_id=1234567890 \
  --tool-arg site_url=https://example.com \
  --tool-arg limit=20
```

Historical keyword ideas:

```bash
npx -y @modelcontextprotocol/inspector --cli \
  uv run flin-google-keyword-planner-mcp \
  --method tools/call \
  --tool-name keyword_ideas_historical \
  --tool-arg customer_id=1234567890 \
  --tool-arg login_customer_id=1234567890 \
  --tool-arg 'keywords=["running shoes"]' \
  --tool-arg start_year=2025 \
  --tool-arg start_month=JANUARY \
  --tool-arg end_year=2025 \
  --tool-arg end_month=DECEMBER \
  --tool-arg include_average_cpc=true \
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
        "GOOGLE_ADS_CUSTOMER_ID": "1234567890",
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID": "1234567890"
      }
    }
  }
}
```

Then ask Claude:

1. `Run google_ads_authorization_url`
2. Open the returned URL, approve access, and copy the `code` query parameter from the redirected URL.
3. `Run google_ads_exchange_authorization_code with code "..."`
4. `Run keyword_ideas_from_keywords with ["running shoes"] limit 10`
5. `Run keyword_ideas_from_site with site_url https://example.com`
6. `Run keyword_ideas_historical for ["running shoes"] from JANUARY 2025 to DECEMBER 2025`

If your OAuth client does not use `http://localhost:8080/`, pass the same `redirect_uri` value to `google_ads_authorization_url` and `google_ads_exchange_authorization_code`.

## 4) Common failures and fixes

`missing_configuration`:

- One or more required env vars are missing.
- Fix: compare with `.env.example`.

`PERMISSION_DENIED` / `USER_PERMISSION_DENIED`:

- OAuth user/token is valid but lacks account access or API permissions.
- Fix: confirm account permissions and `login_customer_id` pairing.

Seed validation errors:

- Required seed argument missing or blank.
- Fix: pass non-empty required seed fields.

Historical range errors:

- Incomplete range fields or invalid month/order.
- Fix: pass all 4 range fields and valid month names/values.

## Recommended release gate

Before each release:

1. `python3 -m pytest`
2. `python3 -m compileall src`
3. `uv build`
4. Inspector smoke tests: `tools/list` + all 5 tool calls
