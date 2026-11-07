# MCP Usage Guide

Use this guide when operating `flin-google-keyword-planner-mcp` from Claude or MCP Inspector.

## Available tools

- `connection_status`
- `keyword_ideas_from_keywords`
- `google_ads_start_local_oauth_flow`
- `google_ads_oauth_status`
- `google_ads_authorization_url`
- `google_ads_exchange_authorization_code`
- `keyword_ideas_from_url`
- `keyword_ideas_from_keyword_and_url`
- `keyword_ideas_from_site`
- `keyword_ideas_historical`
- `keyword_historical_metrics`

## Tool selection guide

Use:
- `connection_status` for the running server version and local setup only. It does not start a browser or call Google. A local token yields `auth_status=unknown`; `live_access` remains `not_checked`.
- `google_ads_start_local_oauth_flow` when the refresh token is expired or revoked and you need a browser-based OAuth refresh inside the MCP session.
- `google_ads_oauth_status` after browser approval to verify that `token_available` is `true`; `token_source` shows `runtime`, `file`, or `env`.
- `google_ads_authorization_url` and `google_ads_exchange_authorization_code` as a manual fallback when the local callback flow is not possible.
- `keyword_ideas_from_keywords` when you have keyword seeds only.
- `keyword_ideas_from_url` when you have a landing page URL only.
- `keyword_ideas_from_keyword_and_url` when you have both and want broader ideas.
- `keyword_ideas_from_site` when you want domain-wide site seed expansion.
- `keyword_ideas_historical` when discovering new ideas with year-month constrained metrics.
- `keyword_historical_metrics` when measuring an existing keyword list without generating new ideas.

## Common parameters

Most tools support:
- `customer_id`
- `login_customer_id`
- `language_id`
- `location_ids`
- `network`
- `include_adult_keywords`
- `limit`
- `page_token`
- `keyword_annotation`
- `aggregate_metric_types`

## Historical tool parameters

`keyword_ideas_historical` additionally requires:
- `start_year`
- `start_month`
- `end_year`
- `end_month`

And supports:
- `include_average_cpc`

## MCC and subaccount rules

- For subaccount access, pass both:
- `customer_id` = client account
- `login_customer_id` = manager account
- `USER_PERMISSION_DENIED` usually means wrong manager/client pairing or missing account access.

## Common error handling

`missing_configuration`:
- Required Google Ads env vars are missing.

`invalid_grant`:
- The configured refresh token is expired or revoked. Run `google_ads_start_local_oauth_flow`, open the returned URL, approve access, then run `google_ads_oauth_status`. A generated token is persisted in `~/.config/flin-google-keyword-planner-mcp/oauth-token.json`.

Seed validation errors:
- Required seed field missing or empty (`keywords`, `url`, or `site_url` depending on tool).

Historical range validation errors:
- Missing one of `start_year/start_month/end_year/end_month`, or invalid month/range ordering.

`USER_PERMISSION_DENIED` / `PERMISSION_DENIED`:
- Verify OAuth user access, manager-client link, and `login_customer_id`.

## Output quality checklist

- Always state which tool was used.
- Always state `customer_id` and `login_customer_id` used.
- Always state seed source (`keywords`, `url`, `keyword+url`, `site`).
- Treat keyword ideas as planning input, not guaranteed outcomes.

## Accurate interpretation

Use explicit targeting for non-US research: German Switzerland is language `1001`
and location `2756`. Empty locations (`[]`) means worldwide. Competition is paid
advertising competition, not organic ranking difficulty. Bid/CPC values use the
customer account currency. `null` means unavailable, not zero. Preserve returned
close variants and do not treat unmatched keywords as zero-volume terms.

Continue idea pages with the returned token and identical request parameters.
Exact historical metrics accepts up to 10,000 keywords, has no pagination, and
uses the past 12 months unless all four date fields are supplied.

OAuth exchange returns status only; tokens are stored privately and never returned
in the tool response. Prefer the local PKCE callback flow over manual code copying.
