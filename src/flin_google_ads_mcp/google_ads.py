from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Any
import re

from .auth import get_effective_refresh_token, get_refresh_token_cache_version
from .config import ConfigurationError, Settings, load_settings


KEYWORD_PLAN_NETWORK_ALIASES = {
    "GOOGLE_SEARCH": "GOOGLE_SEARCH",
    "SEARCH": "GOOGLE_SEARCH",
    "GOOGLE_SEARCH_AND_PARTNERS": "GOOGLE_SEARCH_AND_PARTNERS",
    "SEARCH_AND_PARTNERS": "GOOGLE_SEARCH_AND_PARTNERS",
}

ALLOWED_SEED_MODES = {
    "keywords",
    "url",
    "keyword_and_url",
    "site",
}

ALLOWED_KEYWORD_ANNOTATIONS = {
    "KEYWORD_CONCEPT",
}

ALLOWED_AGGREGATE_METRIC_TYPES = {
    "DEVICE",
}

MONTH_NUMBER_TO_NAME = {
    1: "JANUARY",
    2: "FEBRUARY",
    3: "MARCH",
    4: "APRIL",
    5: "MAY",
    6: "JUNE",
    7: "JULY",
    8: "AUGUST",
    9: "SEPTEMBER",
    10: "OCTOBER",
    11: "NOVEMBER",
    12: "DECEMBER",
}

MONTH_NAME_TO_NUMBER = {name: number for number, name in MONTH_NUMBER_TO_NAME.items()}

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


def normalize_keyword_list(raw_keywords: list[str] | None) -> list[str]:
    cleaned_keywords = [
        str(keyword).strip() for keyword in (raw_keywords or []) if str(keyword).strip()
    ]
    if not cleaned_keywords:
        raise ValueError("keywords must contain at least one non-empty keyword.")
    return cleaned_keywords


def normalize_url_seed(url: str | None, *, field_name: str = "url") -> str:
    if url is None:
        raise ValueError(f"{field_name} is required.")
    cleaned_url = str(url).strip()
    if not cleaned_url:
        raise ValueError(f"{field_name} cannot be blank.")
    return cleaned_url


def normalize_site_seed(site_url: str | None) -> str:
    return normalize_url_seed(site_url, field_name="site_url")


def normalize_keyword_plan_network(network: str) -> str:
    normalized = network.strip().upper()
    resolved = KEYWORD_PLAN_NETWORK_ALIASES.get(normalized)
    if resolved is None:
        allowed = ", ".join(sorted(set(KEYWORD_PLAN_NETWORK_ALIASES.values())))
        raise ValueError(
            f"Invalid keyword plan network {network!r}. Allowed values: {allowed}."
        )
    return resolved


def normalize_keyword_annotations(values: list[str] | None) -> list[str]:
    if not values:
        return []

    normalized_values = [str(value).strip().upper() for value in values if str(value).strip()]
    if not normalized_values:
        return []

    invalid = [value for value in normalized_values if value not in ALLOWED_KEYWORD_ANNOTATIONS]
    if invalid:
        allowed = ", ".join(sorted(ALLOWED_KEYWORD_ANNOTATIONS))
        raise ValueError(
            f"Invalid keyword_annotation values {invalid!r}. Allowed values: {allowed}."
        )

    return normalized_values


def normalize_aggregate_metric_types(values: list[str] | None) -> list[str]:
    if not values:
        return []

    normalized_values = [str(value).strip().upper() for value in values if str(value).strip()]
    if not normalized_values:
        return []

    invalid = [
        value for value in normalized_values if value not in ALLOWED_AGGREGATE_METRIC_TYPES
    ]
    if invalid:
        allowed = ", ".join(sorted(ALLOWED_AGGREGATE_METRIC_TYPES))
        raise ValueError(
            f"Invalid aggregate_metric_types values {invalid!r}. Allowed values: {allowed}."
        )

    return normalized_values


def normalize_month(raw_month: str | int) -> str:
    if isinstance(raw_month, int):
        month_name = MONTH_NUMBER_TO_NAME.get(raw_month)
        if month_name is None:
            raise ValueError("Month integer must be between 1 and 12.")
        return month_name

    cleaned = str(raw_month).strip().upper()
    if not cleaned:
        raise ValueError("Month value cannot be empty.")

    if cleaned.isdigit():
        month_number = int(cleaned)
        month_name = MONTH_NUMBER_TO_NAME.get(month_number)
        if month_name is None:
            raise ValueError("Month integer must be between 1 and 12.")
        return month_name

    if cleaned not in MONTH_NAME_TO_NUMBER:
        allowed = ", ".join(MONTH_NAME_TO_NUMBER.keys())
        raise ValueError(
            f"Invalid month {raw_month!r}. Allowed month names: {allowed}; or integers 1-12."
        )
    return cleaned


def build_language_constant_resource_name(language_id: str) -> str:
    return f"languageConstants/{normalize_entity_id(language_id)}"


def build_geo_target_constant_resource_names(
    location_ids: list[str] | None,
) -> list[str]:
    raw_ids = (
        list(location_ids)
        if location_ids is not None
        else list(DEFAULT_LOCATION_IDS)
    )
    if not raw_ids:
        raise ValueError("location_ids cannot be empty.")

    return [f"geoTargetConstants/{normalize_entity_id(raw_id)}" for raw_id in raw_ids]


def clamp_limit(limit: int, *, default: int = 50, max_limit: int = 1000) -> int:
    if limit <= 0:
        return default
    return min(limit, max_limit)


def get_google_ads_client(login_customer_id: str | None = None) -> Any:
    return _get_google_ads_client(login_customer_id, get_refresh_token_cache_version())


@lru_cache(maxsize=16)
def _get_google_ads_client(
    login_customer_id: str | None = None,
    _refresh_token_version: int = 0,
) -> Any:
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
        "refresh_token": get_effective_refresh_token(settings),
        "use_proto_plus": settings.use_proto_plus,
    }

    effective_login_customer_id = login_customer_id or settings.login_customer_id
    if effective_login_customer_id:
        config_dict["login_customer_id"] = normalize_customer_id(
            effective_login_customer_id
        )

    return GoogleAdsClient.load_from_dict(config_dict)


def clear_google_ads_client_cache() -> None:
    _get_google_ads_client.cache_clear()


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


def _keyword_annotations_to_dict(keyword_annotations: Any) -> dict[str, Any] | None:
    concepts_payload: list[dict[str, Any]] = []
    for concept in getattr(keyword_annotations, "concepts", []):
        concept_group = getattr(concept, "concept_group", None)
        concepts_payload.append(
            {
                "name": str(getattr(concept, "name", "")),
                "group_name": str(getattr(concept_group, "name", "")),
                "group_type": enum_name(getattr(concept_group, "type_", "UNKNOWN")),
            }
        )

    if not concepts_payload:
        return None

    return {
        "concepts": concepts_payload,
    }


def _aggregate_metric_results_to_dict(results: Any) -> dict[str, Any] | None:
    device_searches_payload = [
        {
            "device": enum_name(getattr(device_result, "device", "UNKNOWN")),
            "search_count": to_int(getattr(device_result, "search_count", None)),
        }
        for device_result in getattr(results, "device_searches", [])
    ]

    if not device_searches_payload:
        return None

    return {
        "device_searches": device_searches_payload,
    }


def _validate_seed_mode(seed_mode: str) -> str:
    normalized = seed_mode.strip().lower()
    if normalized not in ALLOWED_SEED_MODES:
        allowed = ", ".join(sorted(ALLOWED_SEED_MODES))
        raise ValueError(f"Invalid seed_mode {seed_mode!r}. Allowed values: {allowed}.")
    return normalized


def _apply_historical_metrics_options(
    request: Any,
    *,
    start_year: int | None,
    start_month: str | int | None,
    end_year: int | None,
    end_month: str | int | None,
    include_average_cpc: bool,
    client: Any,
) -> None:
    has_explicit_range = any(
        value is not None for value in (start_year, start_month, end_year, end_month)
    )

    if has_explicit_range:
        if None in (start_year, start_month, end_year, end_month):
            raise ValueError(
                "Historical range requires start_year, start_month, end_year, and end_month."
            )

        normalized_start_month = normalize_month(start_month)  # type: ignore[arg-type]
        normalized_end_month = normalize_month(end_month)  # type: ignore[arg-type]

        start_year_value = int(start_year)  # type: ignore[arg-type]
        end_year_value = int(end_year)  # type: ignore[arg-type]

        start_tuple = (start_year_value, MONTH_NAME_TO_NUMBER[normalized_start_month])
        end_tuple = (end_year_value, MONTH_NAME_TO_NUMBER[normalized_end_month])
        if start_tuple > end_tuple:
            raise ValueError("Historical range start must be before or equal to end.")

        request.historical_metrics_options.year_month_range.start.year = start_year_value
        request.historical_metrics_options.year_month_range.start.month = getattr(
            client.enums.MonthOfYearEnum,
            normalized_start_month,
        )
        request.historical_metrics_options.year_month_range.end.year = end_year_value
        request.historical_metrics_options.year_month_range.end.month = getattr(
            client.enums.MonthOfYearEnum,
            normalized_end_month,
        )

    if has_explicit_range or include_average_cpc:
        request.historical_metrics_options.include_average_cpc = bool(include_average_cpc)


def generate_keyword_ideas(
    *,
    customer_id: str,
    seed_mode: str,
    keywords: list[str] | None = None,
    url: str | None = None,
    site_url: str | None = None,
    language_id: str = DEFAULT_LANGUAGE_ID,
    location_ids: list[str] | None = None,
    network: str = "GOOGLE_SEARCH_AND_PARTNERS",
    include_adult_keywords: bool = False,
    limit: int = 50,
    page_token: str | None = None,
    keyword_annotation: list[str] | None = None,
    aggregate_metric_types: list[str] | None = None,
    start_year: int | None = None,
    start_month: str | int | None = None,
    end_year: int | None = None,
    end_month: str | int | None = None,
    include_average_cpc: bool = False,
    login_customer_id: str | None = None,
) -> dict[str, Any]:
    normalized_seed_mode = _validate_seed_mode(seed_mode)
    normalized_network = normalize_keyword_plan_network(network)
    normalized_limit = clamp_limit(limit)

    normalized_keywords: list[str] | None = None
    normalized_url: str | None = None
    normalized_site_url: str | None = None

    if normalized_seed_mode == "keywords":
        normalized_keywords = normalize_keyword_list(keywords)
    elif normalized_seed_mode == "url":
        normalized_url = normalize_url_seed(url)
    elif normalized_seed_mode == "keyword_and_url":
        normalized_keywords = normalize_keyword_list(keywords)
        normalized_url = normalize_url_seed(url)
    else:
        normalized_site_url = normalize_site_seed(site_url)

    normalized_annotations = normalize_keyword_annotations(keyword_annotation)
    normalized_aggregate_metric_types = normalize_aggregate_metric_types(
        aggregate_metric_types
    )

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

    if page_token is not None:
        normalized_page_token = str(page_token).strip()
        if normalized_page_token:
            request.page_token = normalized_page_token

    try:
        request.keyword_plan_network = getattr(
            client.enums.KeywordPlanNetworkEnum,
            normalized_network,
        )
    except AttributeError as exc:
        raise ValueError(
            f"Unsupported keyword plan network {normalized_network!r} for this Google Ads client version."
        ) from exc

    for annotation_name in normalized_annotations:
        try:
            request.keyword_annotation.append(
                getattr(client.enums.KeywordPlanKeywordAnnotationEnum, annotation_name)
            )
        except AttributeError as exc:
            raise ValueError(
                f"Unsupported keyword annotation {annotation_name!r} for this Google Ads client version."
            ) from exc

    if normalized_aggregate_metric_types:
        for metric_type in normalized_aggregate_metric_types:
            try:
                request.aggregate_metrics.aggregate_metric_types.append(
                    getattr(client.enums.KeywordPlanAggregateMetricTypeEnum, metric_type)
                )
            except AttributeError as exc:
                raise ValueError(
                    f"Unsupported aggregate metric type {metric_type!r} for this Google Ads client version."
                ) from exc

    _apply_historical_metrics_options(
        request,
        start_year=start_year,
        start_month=start_month,
        end_year=end_year,
        end_month=end_month,
        include_average_cpc=include_average_cpc,
        client=client,
    )

    if normalized_seed_mode == "keywords":
        request.keyword_seed.keywords.extend(normalized_keywords or [])
    elif normalized_seed_mode == "url":
        request.url_seed.url = normalized_url or ""
    elif normalized_seed_mode == "keyword_and_url":
        request.keyword_and_url_seed.url = normalized_url or ""
        request.keyword_and_url_seed.keywords.extend(normalized_keywords or [])
    else:
        request.site_seed.site = normalized_site_url or ""

    response = service.generate_keyword_ideas(request=request)
    first_page_response = getattr(response, "_response", None)

    items: list[dict[str, Any]] = []
    for idea in response:
        item: dict[str, Any] = {
            "keyword": str(idea.text),
            "metrics": _keyword_idea_metrics_to_dict(idea.keyword_idea_metrics),
            "close_variants": [str(variant) for variant in getattr(idea, "close_variants", [])],
        }

        annotations = _keyword_annotations_to_dict(idea.keyword_annotations)
        if annotations is not None:
            item["annotations"] = annotations

        items.append(item)

        if len(items) >= normalized_limit:
            break

    aggregate_metrics = None
    if first_page_response is not None:
        aggregate_metrics = _aggregate_metric_results_to_dict(
            getattr(first_page_response, "aggregate_metric_results", None)
        )

    next_page_token = None
    total_size = 0
    if first_page_response is not None:
        raw_next_page_token = str(getattr(first_page_response, "next_page_token", "")).strip()
        next_page_token = raw_next_page_token or None
        total_size = to_int(getattr(first_page_response, "total_size", None))

    return {
        "seed_mode": normalized_seed_mode,
        "count": len(items),
        "total_size": total_size,
        "next_page_token": next_page_token,
        "aggregate_metrics": aggregate_metrics,
        "items": items,
    }
