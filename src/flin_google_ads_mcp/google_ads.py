from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Any
import re

from .config import ConfigurationError, Settings, load_settings


KEYWORD_PLAN_NETWORK_ALIASES = {
    "GOOGLE_SEARCH": "GOOGLE_SEARCH",
    "SEARCH": "GOOGLE_SEARCH",
    "GOOGLE_SEARCH_AND_PARTNERS": "GOOGLE_SEARCH_AND_PARTNERS",
    "SEARCH_AND_PARTNERS": "GOOGLE_SEARCH_AND_PARTNERS",
}

DEFAULT_LANGUAGE_ID = "1000"
DEFAULT_LOCATION_IDS = ("2840",)


def normalize_customer_id(raw_customer_id: str) -> str:
    cleaned = re.sub(r"\D", "", raw_customer_id)
    if not cleaned:
        raise ValueError("customer_id must contain at least one digit.")
    if len(cleaned) != 10:
        raise ValueError(
            f"customer_id must be 10 digits after normalization, got {len(cleaned)}."
        )
    return cleaned


def normalize_entity_id(raw_entity_id: str) -> str:
    cleaned = re.sub(r"\D", "", raw_entity_id)
    if not cleaned:
        raise ValueError("ID must contain at least one digit.")
    return cleaned


def resolve_customer_id(customer_id: str | None, settings: Settings) -> str:
    candidate = customer_id or settings.default_customer_id
    if not candidate:
        raise ConfigurationError(
            "No customer_id provided. Set GOOGLE_ADS_CUSTOMER_ID or pass customer_id to the tool."
        )
    return normalize_customer_id(candidate)


def normalize_keyword_seed(
    *, keywords: list[str] | None, url: str | None
) -> tuple[list[str], str | None]:
    cleaned_keywords = [
        str(keyword).strip() for keyword in (keywords or []) if str(keyword).strip()
    ]
    cleaned_url = url.strip() if url is not None else None
    if cleaned_url == "":
        cleaned_url = None

    if not cleaned_keywords and cleaned_url is None:
        raise ValueError("At least one seed is required: keywords or url.")

    return cleaned_keywords, cleaned_url


def normalize_keyword_plan_network(network: str) -> str:
    normalized = network.strip().upper()
    resolved = KEYWORD_PLAN_NETWORK_ALIASES.get(normalized)
    if resolved is None:
        allowed = ", ".join(sorted(set(KEYWORD_PLAN_NETWORK_ALIASES.values())))
        raise ValueError(
            f"Invalid keyword plan network {network!r}. Allowed values: {allowed}."
        )
    return resolved


def build_language_constant_resource_name(language_id: str) -> str:
    return f"languageConstants/{normalize_entity_id(language_id)}"


def build_geo_target_constant_resource_names(
    location_ids: list[str] | None,
) -> list[str]:
    raw_ids = list(location_ids) if location_ids is not None else list(DEFAULT_LOCATION_IDS)
    if not raw_ids:
        raise ValueError("location_ids cannot be empty.")

    return [f"geoTargetConstants/{normalize_entity_id(raw_id)}" for raw_id in raw_ids]


def clamp_limit(limit: int, *, default: int = 50, max_limit: int = 1000) -> int:
    if limit <= 0:
        return default
    return min(limit, max_limit)


@lru_cache(maxsize=16)
def get_google_ads_client(login_customer_id: str | None = None) -> Any:
    settings = load_settings()

    try:
        from google.ads.googleads.client import GoogleAdsClient
    except ImportError as exc:
        raise ConfigurationError(
            "google-ads dependency is not installed. Install project dependencies first."
        ) from exc

    config_dict: dict[str, Any] = {
        "developer_token": settings.developer_token,
        "client_id": settings.client_id,
        "client_secret": settings.client_secret,
        "refresh_token": settings.refresh_token,
        "use_proto_plus": settings.use_proto_plus,
    }

    effective_login_customer_id = login_customer_id or settings.login_customer_id
    if effective_login_customer_id:
        config_dict["login_customer_id"] = normalize_customer_id(
            effective_login_customer_id
        )

    return GoogleAdsClient.load_from_dict(config_dict)


def enum_name(value: Any) -> str:
    if hasattr(value, "name"):
        return str(value.name)
    value_str = str(value)
    if "." in value_str:
        return value_str.rsplit(".", 1)[-1]
    return value_str


def to_int(value: Any) -> int:
    if value is None:
        return 0
    return int(value)


def to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def micros_to_currency(value: Any) -> float:
    return to_float(value) / 1_000_000


def format_google_ads_error(exc: Exception) -> dict[str, Any]:
    # GoogleAdsException import is intentionally dynamic to keep module import cheap for tests.
    if exc.__class__.__name__ != "GoogleAdsException":
        return {"type": exc.__class__.__name__, "message": str(exc)}

    request_id = getattr(exc, "request_id", None)
    failure = getattr(exc, "failure", None)
    errors: list[dict[str, Any]] = []

    if failure is not None and getattr(failure, "errors", None):
        for failure_error in failure.errors:
            error_code = getattr(failure_error, "error_code", None)
            errors.append(
                {
                    "message": getattr(failure_error, "message", "Unknown API error"),
                    "code": str(error_code) if error_code is not None else "UNKNOWN",
                }
            )

    return {
        "type": exc.__class__.__name__,
        "request_id": request_id,
        "errors": errors,
        "message": str(exc),
    }


def _monthly_search_volume_to_dict(volume: Any) -> dict[str, Any]:
    return {
        "year": to_int(getattr(volume, "year", None)),
        "month": enum_name(getattr(volume, "month", "UNKNOWN")),
        "monthly_searches": to_int(getattr(volume, "monthly_searches", None)),
    }


def _keyword_idea_metrics_to_dict(metrics: Any) -> dict[str, Any]:
    return {
        "average_monthly_searches": to_int(getattr(metrics, "avg_monthly_searches", None)),
        "competition": enum_name(getattr(metrics, "competition", "UNKNOWN")),
        "competition_index": to_int(getattr(metrics, "competition_index", None)),
        "low_top_of_page_bid": micros_to_currency(
            getattr(metrics, "low_top_of_page_bid_micros", None)
        ),
        "high_top_of_page_bid": micros_to_currency(
            getattr(metrics, "high_top_of_page_bid_micros", None)
        ),
        "average_cpc": micros_to_currency(getattr(metrics, "average_cpc_micros", None)),
        "monthly_search_volumes": [
            _monthly_search_volume_to_dict(volume)
            for volume in getattr(metrics, "monthly_search_volumes", [])
        ],
    }


def generate_keyword_ideas(
    *,
    customer_id: str,
    keywords: list[str] | None,
    url: str | None,
    language_id: str = DEFAULT_LANGUAGE_ID,
    location_ids: list[str] | None = None,
    network: str = "GOOGLE_SEARCH_AND_PARTNERS",
    include_adult_keywords: bool = False,
    limit: int = 50,
    login_customer_id: str | None = None,
) -> list[dict[str, Any]]:
    normalized_keywords, normalized_url = normalize_keyword_seed(
        keywords=keywords,
        url=url,
    )
    normalized_network = normalize_keyword_plan_network(network)
    normalized_limit = clamp_limit(limit)

    client = get_google_ads_client(login_customer_id)
    service = client.get_service("KeywordPlanIdeaService")

    request = client.get_type("GenerateKeywordIdeasRequest")
    request.customer_id = normalize_customer_id(customer_id)
    request.language = build_language_constant_resource_name(language_id)
    request.geo_target_constants.extend(
        build_geo_target_constant_resource_names(location_ids)
    )
    request.include_adult_keywords = bool(include_adult_keywords)
    request.page_size = normalized_limit

    try:
        request.keyword_plan_network = getattr(
            client.enums.KeywordPlanNetworkEnum,
            normalized_network,
        )
    except AttributeError as exc:
        raise ValueError(
            f"Unsupported keyword plan network {normalized_network!r} for this Google Ads client version."
        ) from exc

    if normalized_keywords and normalized_url:
        request.keyword_and_url_seed.url = normalized_url
        request.keyword_and_url_seed.keywords.extend(normalized_keywords)
    elif normalized_keywords:
        request.keyword_seed.keywords.extend(normalized_keywords)
    else:
        request.url_seed.url = normalized_url

    response = service.generate_keyword_ideas(request=request)

    items: list[dict[str, Any]] = []
    for idea in response:
        items.append(
            {
                "keyword": str(idea.text),
                "metrics": _keyword_idea_metrics_to_dict(idea.keyword_idea_metrics),
            }
        )
        if len(items) >= normalized_limit:
            break

    return items
