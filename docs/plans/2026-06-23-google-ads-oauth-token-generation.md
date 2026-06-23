# Google Ads OAuth Token Generation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let users generate a Google Ads OAuth refresh token from Claude via MCP tools instead of placing the token in Claude MCP config.

**Architecture:** Keep developer token, OAuth client ID, and OAuth client secret as required environment settings. Make `GOOGLE_ADS_REFRESH_TOKEN` optional, add an OAuth helper module that builds the Google consent URL and exchanges authorization codes, and cache the generated refresh token in the running MCP process for subsequent keyword tool calls.

**Tech Stack:** Python 3.10+, FastMCP, Google Ads client library, standard-library `urllib` for OAuth token exchange, pytest.

---

### Task 1: Update configuration contract

**Files:**
- Modify: `src/flin_google_ads_mcp/config.py`
- Test: `tests/test_config.py`

**Step 1: Write the failing test**

Assert that `missing_required_env_vars()` requires developer token, client ID, and client secret, but not `GOOGLE_ADS_REFRESH_TOKEN`.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -q`

Expected: FAIL while refresh token is still listed as required.

**Step 3: Write minimal implementation**

Remove `GOOGLE_ADS_REFRESH_TOKEN` from `REQUIRED_ENV_VARS` and load `Settings.refresh_token` as `str | None`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -q`

Expected: PASS.

### Task 2: Add OAuth helper behavior

**Files:**
- Create: `src/flin_google_ads_mcp/auth.py`
- Test: `tests/test_auth.py`

**Step 1: Write the failing tests**

Cover authorization URL generation, authorization-code exchange with an injected fake token request, runtime token precedence, and the missing-token error.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_auth.py -q`

Expected: FAIL because `flin_google_ads_mcp.auth` does not exist.

**Step 3: Write minimal implementation**

Implement `build_authorization_url`, `exchange_authorization_code`, `set_runtime_refresh_token`, `clear_runtime_refresh_token`, and `get_effective_refresh_token`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_auth.py -q`

Expected: PASS.

### Task 2.1: Invalidate cached clients when tokens are regenerated

**Files:**
- Modify: `src/flin_google_ads_mcp/auth.py`
- Modify: `src/flin_google_ads_mcp/google_ads.py`
- Test: `tests/test_auth.py`

**Step 1: Write the failing test**

Call `get_google_ads_client()` after exchanging a first runtime token, exchange a second runtime token, and call `get_google_ads_client()` again. Assert that the Google Ads client factory receives the second refresh token.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_auth.py::test_google_ads_client_uses_regenerated_runtime_refresh_token -q`

Expected: FAIL because the cached client still uses the first token.

**Step 3: Write minimal implementation**

Track a refresh-token cache version in `auth.py`, increment it whenever the runtime token changes, and include that version in the cached Google Ads client helper key.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_auth.py::test_google_ads_client_uses_regenerated_runtime_refresh_token -q`

Expected: PASS.

### Task 3: Wire OAuth into MCP tools and Google Ads client

**Files:**
- Modify: `src/flin_google_ads_mcp/server.py`
- Modify: `src/flin_google_ads_mcp/google_ads.py`
- Test: `tests/test_query_builders.py`

**Step 1: Write the failing test**

Assert the MCP exposes `google_ads_authorization_url` and `google_ads_exchange_authorization_code` before the existing keyword tools.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_query_builders.py::test_server_exposes_expected_keyword_idea_tools -q`

Expected: FAIL because the new tools are not registered.

**Step 3: Write minimal implementation**

Add the two FastMCP tools and update `get_google_ads_client()` to call `get_effective_refresh_token(settings)`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_query_builders.py::test_server_exposes_expected_keyword_idea_tools -q`

Expected: PASS.

### Task 4: Update user documentation

**Files:**
- Modify: `README.md`
- Modify: `.env.example`
- Modify: `docs/testing.md`

**Step 1: Remove refresh token from Claude config examples**

Document the two Claude tool calls needed to generate and exchange a token.

**Step 2: Keep optional persistence documented**

Show `GOOGLE_ADS_REFRESH_TOKEN` only as optional shell or `.env` persistence.

### Task 5: Verify

**Files:**
- All changed files

**Step 1: Run tests**

Run: `pytest -q`

Expected: all tests pass.

**Step 2: Run import/syntax check**

Run: `python3 -m compileall src`

Expected: all files compile.
