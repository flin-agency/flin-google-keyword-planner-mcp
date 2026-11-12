# flin Google Keyword Planner MCP

Keyword-Ideen und historische Suchvolumen aus Google Ads für Claude Desktop.
Die Keyword-Tools lesen Daten und verändern keine Kampagnen.

## Start auf einem Mac mit Apple Silicon (M1 oder neuer)

1. **[Desktop-Paket herunterladen](https://github.com/flin-agency/flin-google-keyword-planner-mcp/releases/latest/download/flin-google-keyword-planner-mcp.mcpb)**.
   [Versionierte Downloads und Prüfsummen](https://github.com/flin-agency/flin-google-keyword-planner-mcp/releases) bleiben verfügbar.
2. In aktuellem Claude Desktop: **Settings → Desktop app → Extensions → Manage →
   Advanced settings → Install Extension…** und die `.mcpb` auswählen.
3. Die Pflichtfelder aus dem Passwortmanager eintragen. Die Werte erhältst du vom
   zuständigen Administrator; keine Zugangsdaten in den Chat kopieren.
4. Ohne vorhandenen Refresh Token Claude bitten: **«Starte `google_ads_start_local_oauth_flow`.»**
   Den Google-Link öffnen, das berechtigte Konto wählen und den Zugriff genehmigen.
5. **«Rufe `connection_status` auf.»** Das prüft die lokale Einrichtung ohne
   Google-Abfrage. Für einen echten Zugriffstest anschliessend ausdrücklich:
   **«Prüfe mit `keyword_historical_metrics` das Keyword Wandern, Sprache Deutsch
   (`1001`), Schweiz (`2756`), Netzwerk `GOOGLE_SEARCH`.»** Dieser Test verwendet
   Google-Ads-API-Kontingent; Fehler erscheinen als Tool-Ergebnis.

| Feld in Claude | Erforderlich? | Bedeutung |
| --- | --- | --- |
| Google Ads developer token | Ja | API-Token des berechtigten Managerkontos |
| OAuth client ID | Ja | Google-Cloud-OAuth-Client, empfohlen: Desktop app |
| OAuth client secret | Ja | Zum OAuth-Client gehörendes Secret |
| Google Ads customer ID | Ja im Desktop-Paket | Zielkonto, zehn Ziffern; Bindestriche sind erlaubt |
| Manager account ID / `login_customer_id` | Nur bei Zugriff über ein MCC | ID des zugriffsberechtigten Managerkontos, nicht automatisch die Zielkonto-ID |
| Refresh token | Nein | Kann durch den Browser-Login erzeugt werden |

`connection_status` zeigt die **tatsächlich laufende `server_version`**.
`configuration_status=configured` bedeutet nur, dass die lokalen Angaben vorliegen.
Ein vorhandenes Token ergibt `auth_status=unknown`, nicht eine bestätigte Anmeldung;
`live_access=not_checked` bleibt beim lokalen Statusaufruf unverändert.

## Updates und Hilfe

Die **Erweiterungsversion** bezeichnet den importierten Starter. Ab Starter 0.3.3
lädt jeder Serverneustart automatisch die neueste stabile PyPI-Version im geprüften
Bereich **`>=0.3.2,<0.4.0`** für Python 3.13. Die **Serverversion** kann daher neuer
sein. Laufende Sitzungen bleiben bestehen, Einstellungen und Token werden nicht
umgeschrieben. Vorabversionen und die nächste Minor-Version sind ausgeschlossen.

Für die neue Kompatibilitätsgrenze den Starter **einmal neu importieren**; normale
Serverupdates benötigen danach keinen neuen Import. Starter-/UI-Änderungen können
einen weiteren Import erfordern. Internet ist beim Start erforderlich. Es gibt
keinen automatischen Rückfall auf einen alten Cache; der bewusst manuelle Ausweg
bei einer PyPI-Störung steht in [SUPPORT.md](SUPPORT.md).

Ab Server 0.3.4 sind die Standardwerte **Deutsch, Schweiz, Google Search mit Partnern**.
Für andere Märkte Sprache und Region ausdrücklich angeben. Advertising Competition ist
**Anzeigenwettbewerb, keine organische SEO-Schwierigkeit**. Fehlende Kennzahlen sind
`null`, nicht 0. Volumen sind Näherungswerte; Google fasst ähnliche Varianten zusammen.

[Ausführliche Mac-Anleitung](docs/claude-desktop-mac.md) ·
[Datenschutz](PRIVACY.md) · [Sicherheit](SECURITY.md) · [Hilfe](SUPPORT.md)

Das Python-Paket unterstützt weiterhin Python 3.10+ auf anderen geeigneten Systemen;
Intel-Macs werden durch das plattformneutrale Paket nicht ausgeschlossen. Die
Apple-Silicon-Prüfung ist unten von Linux-Tests und echten Kontotests getrennt.
Entwicklerinstallation und manuelle JSON-Konfiguration folgen weiter unten.

## Exposed MCP tools

- `connection_status` — local setup and running version; no browser or API request
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
- `language_id` (default `1001` = German)
- `location_ids` (default `2756` = Switzerland; `[]` = all locations; max 10 unique IDs)
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

- Since server 0.3.4, defaults are **German / Switzerland / Search and Partners**.
  This intentionally changes requests with omitted targeting from English/US.
  To keep English/US targeting, pass `language_id="1000"`, `location_ids=["2840"]`.
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

1. Python 3.10+ for manual/developer installation; Claude Desktop manages Python 3.13
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
      "args": ["--refresh", "--prerelease", "disallow", "--from", "flin-google-keyword-planner-mcp>=0.3.2,<0.4.0", "flin-google-keyword-planner-mcp"],
      "env": {
        "GOOGLE_ADS_DEVELOPER_TOKEN": "REPLACE_ME",
        "GOOGLE_ADS_CLIENT_ID": "REPLACE_ME",
        "GOOGLE_ADS_CLIENT_SECRET": "REPLACE_ME",
        "GOOGLE_ADS_CUSTOMER_ID": "1234567890",
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID": "",
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
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID": "",
        "GOOGLE_ADS_USE_PROTO_PLUS": "true"
      }
    }
  }
}
```

Leave `GOOGLE_ADS_LOGIN_CUSTOMER_ID` blank unless access goes through an MCC; then use the manager account ID. The manual server also accepts `customer_id` per query if no default is set.

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

If the browser reports `Authentication failed`, run `google_ads_oauth_status` for
the failure reason. It distinguishes rejected codes/clients, connectivity problems,
missing refresh tokens and token-file write failures without returning secrets or
Google's raw error descriptions. Start a new flow after correcting the cause;
authorization codes cannot be reused. `token_available=true` alone can refer to an
older saved token and does not confirm the latest login succeeded.

Authorization requests only the Google Ads scope and does not opt into combining
previously granted scopes. Code exchange uses Python's HTTP client directly, not
oauthlib's scope validation, so `OAUTHLIB_RELAX_TOKEN_SCOPE` does not affect this flow.

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
Existing five idea tool names are retained. Since 0.3.4, omitted targeting defaults
to German/Switzerland; explicit targeting continues to override these defaults.

Reference: [Google historical metrics](https://developers.google.com/google-ads/api/docs/keyword-planning/generate-historical-metrics),
[Google keyword ideas](https://developers.google.com/google-ads/api/docs/keyword-planning/generate-keyword-ideas),
[API releases](https://developers.google.com/google-ads/api/docs/release-notes).
