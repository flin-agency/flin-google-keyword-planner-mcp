import asyncio

import pytest

from flin_google_ads_mcp.google_ads import (
    build_geo_target_constant_resource_names,
    build_language_constant_resource_name,
    normalize_customer_id,
    normalize_keyword_plan_network,
    normalize_keyword_seed,
)
from flin_google_ads_mcp.server import mcp


def test_server_exposes_only_keyword_research_tool() -> None:
    tools = asyncio.run(mcp.list_tools())
    assert [tool.name for tool in tools] == ["keyword_research"]


def test_normalize_customer_id_removes_separators() -> None:
    assert normalize_customer_id("123-456-7890") == "1234567890"


def test_normalize_customer_id_rejects_bad_length() -> None:
    with pytest.raises(ValueError):
        normalize_customer_id("123")


def test_normalize_keyword_seed_requires_keywords_or_url() -> None:
    with pytest.raises(ValueError):
        normalize_keyword_seed(keywords=None, url=None)


def test_normalize_keyword_seed_cleans_input() -> None:
    keywords, url = normalize_keyword_seed(
        keywords=[" running shoes ", "", "sneakers"], url=" https://example.com "
    )
    assert keywords == ["running shoes", "sneakers"]
    assert url == "https://example.com"


def test_normalize_keyword_plan_network_accepts_google_search() -> None:
    assert normalize_keyword_plan_network("google_search") == "GOOGLE_SEARCH"


def test_normalize_keyword_plan_network_rejects_unknown_network() -> None:
    with pytest.raises(ValueError):
        normalize_keyword_plan_network("DISPLAY")


def test_build_language_constant_resource_name_uses_digits() -> None:
    assert build_language_constant_resource_name("1-0-0-0") == "languageConstants/1000"


def test_build_geo_target_constant_resource_names_defaults_to_us() -> None:
    assert build_geo_target_constant_resource_names(None) == ["geoTargetConstants/2840"]


def test_build_geo_target_constant_resource_names_normalizes_ids() -> None:
    assert build_geo_target_constant_resource_names(["2-8-4-0", "2036"]) == [
        "geoTargetConstants/2840",
        "geoTargetConstants/2036",
    ]
