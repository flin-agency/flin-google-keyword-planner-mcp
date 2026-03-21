from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import ConfigurationError, load_settings
from .google_ads import (
    format_google_ads_error,
    generate_keyword_ideas,
    normalize_keyword_seed,
    resolve_customer_id,
)


mcp = FastMCP(
    name="flin-google-keyword-planner-mcp",
    instructions=(
        "Google Ads Keyword Planner MCP. "
        "Only keyword research is exposed via a single read-only tool."
    ),
)


def _error_payload(exc: Exception) -> dict[str, Any]:
    return {"ok": False, "error": format_google_ads_error(exc)}


@mcp.tool()
def keyword_research(
    customer_id: str | None = None,
    keywords: list[str] | None = None,
    url: str | None = None,
    language_id: str = "1000",
    location_ids: list[str] | None = None,
    network: str = "GOOGLE_SEARCH_AND_PARTNERS",
    include_adult_keywords: bool = False,
    limit: int = 50,
    login_customer_id: str | None = None,
) -> dict[str, Any]:
    """Run keyword research using Google Ads Keyword Planner ideas."""
    try:
        settings = load_settings()
        resolved_customer_id = resolve_customer_id(customer_id, settings)
        normalized_keywords, normalized_url = normalize_keyword_seed(
            keywords=keywords,
            url=url,
        )

        items = generate_keyword_ideas(
            customer_id=resolved_customer_id,
            keywords=normalized_keywords,
            url=normalized_url,
            language_id=language_id,
            location_ids=location_ids,
            network=network,
            include_adult_keywords=include_adult_keywords,
            limit=limit,
            login_customer_id=login_customer_id,
        )

        return {
            "ok": True,
            "customer_id": resolved_customer_id,
            "count": len(items),
            "seed": {
                "keywords": normalized_keywords,
                "url": normalized_url,
            },
            "items": items,
        }
    except Exception as exc:
        return _error_payload(exc)


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
