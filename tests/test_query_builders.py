import asyncio

import pytest

from flin_google_ads_mcp.google_ads import (
    build_geo_target_constant_resource_names,
    build_language_constant_resource_name,
    normalize_aggregate_metric_types,
    normalize_customer_id,
    normalize_keyword_annotations,
    normalize_keyword_list,
    normalize_keyword_plan_network,
    normalize_month,
    normalize_site_seed,
    normalize_url_seed,
)
from flin_google_ads_mcp.server import mcp


def test_server_exposes_expected_keyword_idea_tools() -> None:
    tools = asyncio.run(mcp.list_tools())
    assert [tool.name for tool in tools] == [
        "google_ads_authorization_url",
        "google_ads_exchange_authorization_code",
        "keyword_ideas_from_keywords",
        "keyword_ideas_from_url",
        "keyword_ideas_from_keyword_and_url",
        "keyword_ideas_from_site",
        "keyword_ideas_historical",
    ]


def test_normalize_customer_id_removes_separators() -> None:
    assert normalize_customer_id("123-456-7890") == "1234567890"


def test_normalize_customer_id_rejects_bad_length() -> None:
    with pytest.raises(ValueError):
        normalize_customer_id("123")


def test_normalize_keyword_list_requires_values() -> None:
    with pytest.raises(ValueError):
        normalize_keyword_list(None)


def test_normalize_keyword_list_cleans_input() -> None:
    assert normalize_keyword_list([" running shoes ", "", "sneakers"]) == [
        "running shoes",
        "sneakers",
    ]


def test_normalize_url_seed_rejects_blank() -> None:
    with pytest.raises(ValueError):
        normalize_url_seed(" ")


def test_normalize_site_seed_rejects_blank() -> None:
    with pytest.raises(ValueError):
        normalize_site_seed(" ")


def test_normalize_keyword_plan_network_accepts_google_search() -> None:
    assert normalize_keyword_plan_network("google_search") == "GOOGLE_SEARCH"


def test_normalize_keyword_plan_network_rejects_unknown_network() -> None:
    with pytest.raises(ValueError):
        normalize_keyword_plan_network("DISPLAY")


def test_normalize_month_supports_string_and_int() -> None:
    assert normalize_month("january") == "JANUARY"
    assert normalize_month(12) == "DECEMBER"


def test_normalize_month_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        normalize_month(13)


def test_normalize_keyword_annotations_supports_keyword_concept() -> None:
    assert normalize_keyword_annotations(["keyword_concept"]) == ["KEYWORD_CONCEPT"]


def test_normalize_keyword_annotations_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        normalize_keyword_annotations(["foo"])


def test_normalize_aggregate_metric_types_supports_device() -> None:
    assert normalize_aggregate_metric_types(["device"]) == ["DEVICE"]


def test_normalize_aggregate_metric_types_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        normalize_aggregate_metric_types(["geo"])


def test_build_language_constant_resource_name_uses_digits() -> None:
    assert build_language_constant_resource_name("1-0-0-0") == "languageConstants/1000"


def test_build_geo_target_constant_resource_names_defaults_to_us() -> None:
    assert build_geo_target_constant_resource_names(None) == ["geoTargetConstants/2840"]


def test_build_geo_target_constant_resource_names_normalizes_ids() -> None:
    assert build_geo_target_constant_resource_names(["2-8-4-0", "2036"]) == [
        "geoTargetConstants/2840",
        "geoTargetConstants/2036",
    ]
