# Keyword Ideas Multi-Tool Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expose five specialized MCP tools for Google Keyword Planner ideas (`keywords`, `url`, `keyword+url`, `site`, `historical`) while preserving secure read-only behavior.

**Architecture:** Keep one shared internal request builder/executor for `GenerateKeywordIdeas` in `google_ads.py`, and expose five thin tool wrappers in `server.py` with clear, LLM-friendly names and fixed seed modes. Extend normalization for advanced parameters (`historical_metrics_options`, `keyword_annotation`, aggregate metrics) and return a consistent response schema.

**Tech Stack:** Python 3.12, `mcp` FastMCP, Google Ads API client (`google-ads>=29.2.0`), pytest.

---

### Task 1: Replace single-tool contract with five-tool contract tests

**Files:**
- Modify: `tests/test_query_builders.py`

**Step 1: Write the failing test**

Add tests asserting:
- MCP tool names are exactly:
  - `keyword_ideas_from_keywords`
  - `keyword_ideas_from_url`
  - `keyword_ideas_from_keyword_and_url`
  - `keyword_ideas_from_site`
  - `keyword_ideas_historical`
- seed normalization and new option validators work.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_query_builders.py -q`
Expected: FAIL because server currently exposes only `keyword_research` and missing new normalizers.

**Step 3: Write minimal implementation target notes**

No code implementation in this task; only lock desired behavior.

**Step 4: Run test to verify still fails for the right reason**

Run: `pytest tests/test_query_builders.py::test_server_exposes_expected_keyword_idea_tools -q`
Expected: FAIL with mismatched tool names.

**Step 5: Commit**

```bash
git add tests/test_query_builders.py
git commit -m "test: define five-tool keyword ideas contract"
```

### Task 2: Implement shared keyword-ideas engine with seed modes and advanced options

**Files:**
- Modify: `src/flin_google_ads_mcp/google_ads.py`
- Test: `tests/test_query_builders.py`

**Step 1: Write the failing test**

Add tests for:
- site seed normalization and validation
- month parsing (`JANUARY`..`DECEMBER`)
- keyword annotation/aggregate metric normalization

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_query_builders.py -q`
Expected: FAIL for missing helpers.

**Step 3: Write minimal implementation**

Implement:
- `normalize_site_seed`, `normalize_month`, `normalize_keyword_annotations`, `normalize_aggregate_metric_types`
- shared request builder with seed mode selector
- optional `historical_metrics_options.year_month_range`
- optional `keyword_annotation` and `aggregate_metrics`
- response enrichments (`close_variants`, `annotations`, `aggregate_metrics`, paging metadata)

**Step 4: Run tests to verify passing**

Run: `pytest tests/test_query_builders.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/flin_google_ads_mcp/google_ads.py tests/test_query_builders.py
git commit -m "feat: add shared keyword ideas engine with advanced options"
```

### Task 3: Expose five MCP tools in server layer

**Files:**
- Modify: `src/flin_google_ads_mcp/server.py`
- Test: `tests/test_query_builders.py`

**Step 1: Write the failing test**

Ensure tool list test expects exactly the 5 tools and no `keyword_research`.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_query_builders.py::test_server_exposes_expected_keyword_idea_tools -q`
Expected: FAIL.

**Step 3: Write minimal implementation**

Create 5 wrappers:
- `keyword_ideas_from_keywords`
- `keyword_ideas_from_url`
- `keyword_ideas_from_keyword_and_url`
- `keyword_ideas_from_site`
- `keyword_ideas_historical`

Each wrapper resolves customer, calls shared engine with fixed seed mode and tool-specific params.

**Step 4: Run tests to verify passing**

Run: `pytest tests/test_query_builders.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/flin_google_ads_mcp/server.py tests/test_query_builders.py
git commit -m "feat: expose five specialized keyword ideas MCP tools"
```

### Task 4: Update user docs for new tool surface

**Files:**
- Modify: `README.md`
- Modify: `docs/testing.md`
- Modify: `docs/mcp-usage-guide.md`

**Step 1: Write the failing test**

N/A (docs-only task).

**Step 2: Run verification command**

Run: `rg -n "keyword_research" README.md docs/testing.md docs/mcp-usage-guide.md`
Expected: no obsolete single-tool contract statements.

**Step 3: Write minimal documentation update**

Document all 5 tools, example arguments, and safe integration snippets.

**Step 4: Run docs sanity check**

Run: `rg -n "keyword_ideas_from_" README.md docs/testing.md docs/mcp-usage-guide.md`
Expected: all new tools referenced.

**Step 5: Commit**

```bash
git add README.md docs/testing.md docs/mcp-usage-guide.md
git commit -m "docs: describe five keyword ideas tools and usage"
```

### Task 5: End-to-end verification

**Files:**
- Verify only

**Step 1: Run full test suite**

Run: `pytest -q`
Expected: PASS.

**Step 2: Compile check**

Run: `python3 -m compileall src`
Expected: PASS.

**Step 3: Package build**

Run: `uv build`
Expected: PASS.

**Step 4: Tool listing sanity check**

Run:
`PYTHONPATH=src python3 - <<'PY'`
`import asyncio`
`from flin_google_ads_mcp.server import mcp`
`print([t.name for t in asyncio.run(mcp.list_tools())])`
`PY`

Expected: exactly 5 new tool names.

**Step 5: Commit verification metadata**

```bash
git add -A
git commit -m "chore: verify multi-tool keyword ideas implementation"
```
