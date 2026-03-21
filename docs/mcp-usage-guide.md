# MCP Usage Guide

Use this guide when operating `flin-google-keyword-planner-mcp` from Claude or MCP Inspector.

## Available tool

- `keyword_research`

No other tools are exposed.

## Recommended call pattern

1. Decide seed input:
- `keywords` list, and/or
- `url`
2. Provide target scope:
- `customer_id` (or set `GOOGLE_ADS_CUSTOMER_ID`)
- optional `login_customer_id` for MCC flows
3. Optionally tune:
- `language_id` (default `1000`)
- `location_ids` (default `2840` = US)
- `network` (`GOOGLE_SEARCH` or `GOOGLE_SEARCH_AND_PARTNERS`)
- `include_adult_keywords`
- `limit`

## MCC and subaccount rules

- For subaccount access, pass both:
- `customer_id` = client account
- `login_customer_id` = manager account
- `USER_PERMISSION_DENIED` usually means wrong manager/client pairing or missing account access.

## Common error handling

`missing_configuration`:
- Required Google Ads env vars are missing.

`ValueError` for seed:
- `keywords` and `url` were both empty/missing.

`USER_PERMISSION_DENIED` / `PERMISSION_DENIED`:
- Verify OAuth user access, manager-client link, and `login_customer_id`.

## Output quality checklist

- Always state which `customer_id` and `login_customer_id` were used.
- Always state seed type (`keywords`, `url`, or both).
- Treat returned keyword ideas as planning input, not guaranteed performance.
