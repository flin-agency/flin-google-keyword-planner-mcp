from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .auth import (
    DEFAULT_REDIRECT_URI,
    build_authorization_url,
    exchange_authorization_code,
    get_local_authorization_flow_status,
    start_local_authorization_flow,
)
from .config import ConfigurationError, load_settings
from .google_ads import (
    format_google_ads_error,
    generate_keyword_ideas,
    resolve_customer_id,
)


mcp = FastMCP(
    name="flin-google-keyword-planner-mcp",
    instructions=(
        "Google Ads Keyword Planner MCP. "
        "OAuth setup helpers and five specialized read-only keyword ideas tools are exposed."
    ),
)


def _error_payload(exc: Exception) -> dict[str, Any]:
    return {"ok": False, "error": format_google_ads_error(exc)}


def _run_keyword_ideas_tool(
    *,
    customer_id: str | None,
    login_customer_id: str | None,
    seed_mode: str,
    **kwargs: Any,
) -> dict[str, Any]:
    try:
        settings = load_settings()
        resolved_customer_id = resolve_customer_id(customer_id, settings)

        result = generate_keyword_ideas(
            customer_id=resolved_customer_id,
            seed_mode=seed_mode,
            login_customer_id=login_customer_id,
            **kwargs,
        )

        return {
            "ok": True,
            "customer_id": resolved_customer_id,
            **result,
        }
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def google_ads_authorization_url(
    redirect_uri: str = DEFAULT_REDIRECT_URI,
    state: str | None = None,
) -> dict[str, Any]:
    """Create the Google OAuth consent URL for generating a Google Ads refresh token."""
    try:
        settings = load_settings()
        authorization_url = build_authorization_url(
            client_id=settings.client_id,
            redirect_uri=redirect_uri,
            state=state,
        )
        return {
            "ok": True,
            "authorization_url": authorization_url,
            "redirect_uri": redirect_uri,
            "next_step": (
                "Open authorization_url, approve access, then copy the code query "
                "parameter from the redirected URL into google_ads_exchange_authorization_code."
            ),
        }
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def google_ads_exchange_authorization_code(
    code: str,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
) -> dict[str, Any]:
    """Exchange a Google OAuth authorization code for a session refresh token."""
    try:
        settings = load_settings()
        refresh_token = exchange_authorization_code(
            code=code,
            client_id=settings.client_id,
            client_secret=settings.client_secret,
            redirect_uri=redirect_uri,
        )
        return {
            "ok": True,
            "refresh_token": refresh_token,
            "token_source": "runtime_session",
            "next_step": (
                "The token is active for this MCP server session. For persistence, "
                "store it as GOOGLE_ADS_REFRESH_TOKEN outside Claude config."
            ),
        }
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def google_ads_start_local_oauth_flow(
    redirect_uri: str = DEFAULT_REDIRECT_URI,
) -> dict[str, Any]:
    """Start a local OAuth callback server and return the Google consent URL."""
    try:
        settings = load_settings()
        flow = start_local_authorization_flow(
            settings=settings,
            redirect_uri=redirect_uri,
        )
        return {
            "ok": True,
            **flow,
            "next_step": (
                "Open authorization_url in your browser. After Google redirects back "
                "to the local callback, run google_ads_oauth_status."
            ),
        }
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def google_ads_oauth_status() -> dict[str, Any]:
    """Return local OAuth callback status and whether a runtime token is available."""
    try:
        return {
            "ok": True,
            **get_local_authorization_flow_status(),
        }
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def keyword_ideas_from_keywords(
    keywords: list[str],
    customer_id: str | None = None,
    language_id: str = "1000",
    location_ids: list[str] | None = None,
    network: str = "GOOGLE_SEARCH_AND_PARTNERS",
    include_adult_keywords: bool = False,
    limit: int = 50,
    page_token: str | None = None,
    keyword_annotation: list[str] | None = None,
    aggregate_metric_types: list[str] | None = None,
    login_customer_id: str | None = None,
) -> dict[str, Any]:
    """Generate keyword ideas using KeywordSeed."""
    return _run_keyword_ideas_tool(
        customer_id=customer_id,
        login_customer_id=login_customer_id,
        seed_mode="keywords",
        keywords=keywords,
        language_id=language_id,
        location_ids=location_ids,
        network=network,
        include_adult_keywords=include_adult_keywords,
        limit=limit,
        page_token=page_token,
        keyword_annotation=keyword_annotation,
        aggregate_metric_types=aggregate_metric_types,
    )


@mcp.tool()
def keyword_ideas_from_url(
    url: str,
    customer_id: str | None = None,
    language_id: str = "1000",
    location_ids: list[str] | None = None,
    network: str = "GOOGLE_SEARCH_AND_PARTNERS",
    include_adult_keywords: bool = False,
    limit: int = 50,
    page_token: str | None = None,
    keyword_annotation: list[str] | None = None,
    aggregate_metric_types: list[str] | None = None,
    login_customer_id: str | None = None,
) -> dict[str, Any]:
    """Generate keyword ideas using UrlSeed."""
    return _run_keyword_ideas_tool(
        customer_id=customer_id,
        login_customer_id=login_customer_id,
        seed_mode="url",
        url=url,
        language_id=language_id,
        location_ids=location_ids,
        network=network,
        include_adult_keywords=include_adult_keywords,
        limit=limit,
        page_token=page_token,
        keyword_annotation=keyword_annotation,
        aggregate_metric_types=aggregate_metric_types,
    )


@mcp.tool()
def keyword_ideas_from_keyword_and_url(
    keywords: list[str],
    url: str,
    customer_id: str | None = None,
    language_id: str = "1000",
    location_ids: list[str] | None = None,
    network: str = "GOOGLE_SEARCH_AND_PARTNERS",
    include_adult_keywords: bool = False,
    limit: int = 50,
    page_token: str | None = None,
    keyword_annotation: list[str] | None = None,
    aggregate_metric_types: list[str] | None = None,
    login_customer_id: str | None = None,
) -> dict[str, Any]:
    """Generate keyword ideas using KeywordAndUrlSeed."""
    return _run_keyword_ideas_tool(
        customer_id=customer_id,
        login_customer_id=login_customer_id,
        seed_mode="keyword_and_url",
        keywords=keywords,
        url=url,
        language_id=language_id,
        location_ids=location_ids,
        network=network,
        include_adult_keywords=include_adult_keywords,
        limit=limit,
        page_token=page_token,
        keyword_annotation=keyword_annotation,
        aggregate_metric_types=aggregate_metric_types,
    )


@mcp.tool()
def keyword_ideas_from_site(
    site_url: str,
    customer_id: str | None = None,
    language_id: str = "1000",
    location_ids: list[str] | None = None,
    network: str = "GOOGLE_SEARCH_AND_PARTNERS",
    include_adult_keywords: bool = False,
    limit: int = 50,
    page_token: str | None = None,
    keyword_annotation: list[str] | None = None,
    aggregate_metric_types: list[str] | None = None,
    login_customer_id: str | None = None,
) -> dict[str, Any]:
    """Generate keyword ideas using SiteSeed."""
    return _run_keyword_ideas_tool(
        customer_id=customer_id,
        login_customer_id=login_customer_id,
        seed_mode="site",
        site_url=site_url,
        language_id=language_id,
        location_ids=location_ids,
        network=network,
        include_adult_keywords=include_adult_keywords,
        limit=limit,
        page_token=page_token,
        keyword_annotation=keyword_annotation,
        aggregate_metric_types=aggregate_metric_types,
    )


@mcp.tool()
def keyword_ideas_historical(
    keywords: list[str],
    start_year: int,
    start_month: str | int,
    end_year: int,
    end_month: str | int,
    include_average_cpc: bool = False,
    customer_id: str | None = None,
    language_id: str = "1000",
    location_ids: list[str] | None = None,
    network: str = "GOOGLE_SEARCH_AND_PARTNERS",
    include_adult_keywords: bool = False,
    limit: int = 50,
    page_token: str | None = None,
    keyword_annotation: list[str] | None = None,
    aggregate_metric_types: list[str] | None = None,
    login_customer_id: str | None = None,
) -> dict[str, Any]:
    """Generate keyword ideas with historical metrics options (year-month range)."""
    return _run_keyword_ideas_tool(
        customer_id=customer_id,
        login_customer_id=login_customer_id,
        seed_mode="keywords",
        keywords=keywords,
        start_year=start_year,
        start_month=start_month,
        end_year=end_year,
        end_month=end_month,
        include_average_cpc=include_average_cpc,
        language_id=language_id,
        location_ids=location_ids,
        network=network,
        include_adult_keywords=include_adult_keywords,
        limit=limit,
        page_token=page_token,
        keyword_annotation=keyword_annotation,
        aggregate_metric_types=aggregate_metric_types,
    )


def main() -> None:
    try:
        # Validate early if env vars are missing.
        load_settings()
    except ConfigurationError:
        # Keep startup non-fatal so tool calls can report missing vars via MCP.
        pass

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
