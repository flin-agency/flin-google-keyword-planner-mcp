"""Offline integration tests against real SDK messages and paging contracts."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from google.ads.googleads.client import GoogleAdsClient
from google.auth.credentials import AnonymousCredentials

from flin_google_ads_mcp import google_ads as ads


@pytest.fixture(params=[True, False], ids=["proto-plus", "protobuf"])
def sdk(request, monkeypatch):
    client = GoogleAdsClient(
        credentials=AnonymousCredentials(),
        developer_token="test",
        use_proto_plus=request.param,
    )
    service = Mock()
    monkeypatch.setattr(client, "get_service", lambda _: service)
    monkeypatch.setattr(ads, "get_google_ads_client", lambda _: client)
    return client, service


def message(client, name, values):
    value = client.get_type(name)
    pb = getattr(value, "_pb", value)
    from google.protobuf.json_format import ParseDict

    ParseDict(values, pb)
    return value


@pytest.mark.parametrize(
    "mode,seed",
    [
        ("keywords", {"keywords": ["wanderung"]}),
        ("url", {"url": "https://example.com/page"}),
        (
            "keyword_and_url",
            {"keywords": ["wanderung"], "url": "https://example.com/page"},
        ),
        ("site", {"site_url": "https://example.com"}),
    ],
)
def test_seed_requests_use_one_page_and_preserve_targeting(sdk, mode, seed):
    client, service = sdk
    page = message(
        client,
        "GenerateKeywordIdeaResponse",
        {
            "results": [
                {
                    "text": "wanderung",
                    "keywordIdeaMetrics": {
                        "avgMonthlySearches": "0",
                        "competition": "LOW",
                        "lowTopOfPageBidMicros": "1250000",
                        "monthlySearchVolumes": [
                            {"year": 2025, "month": "JANUARY", "monthlySearches": "0"}
                        ],
                    },
                    "keywordAnnotations": {
                        "concepts": [
                            {
                                "name": "outdoor",
                                "conceptGroup": {
                                    "name": "activity",
                                    "type_": "NON_BRAND",
                                },
                            }
                        ]
                    },
                }
            ],
            "nextPageToken": "page-2",
            "totalSize": "5",
            "aggregateMetricResults": {
                "deviceSearches": [{"device": "MOBILE", "searchCount": "20"}]
            },
        },
    )

    def pages():
        yield page
        pytest.fail("A short page must not trigger automatic page fetching")

    service.generate_keyword_ideas.return_value = SimpleNamespace(pages=pages())
    result = ads.generate_keyword_ideas(
        customer_id="123-456-7890",
        seed_mode=mode,
        **seed,
        language_id="1001",
        location_ids=["2756"],
        limit=50,
        page_token="page-1",
        keyword_annotation=["KEYWORD_CONCEPT"],
        aggregate_metric_types=["DEVICE"],
        include_average_cpc=True,
        start_year=2025,
        start_month=1,
        end_year=2025,
        end_month=12,
    )
    request = service.generate_keyword_ideas.call_args.kwargs["request"]
    pb = getattr(request, "_pb", request)
    assert (
        pb.WhichOneof("seed")
        == {
            "keywords": "keyword_seed",
            "url": "url_seed",
            "keyword_and_url": "keyword_and_url_seed",
            "site": "site_seed",
        }[mode]
    )
    assert request.page_token == "page-1"
    assert request.page_size == 50
    assert request.customer_id == "1234567890"
    assert request.historical_metrics_options.include_average_cpc
    assert request.historical_metrics_options.year_month_range.start.year == 2025
    assert service.generate_keyword_ideas.call_args.kwargs["timeout"] == 30
    assert result["next_page_token"] == "page-2"
    assert result["count"] == 1
    assert result["total_size"] == 5
    assert result["targeting"]["locations"] == ["geoTargetConstants/2756"]
    assert result["targeting"]["language"] == "languageConstants/1001"
    metrics = result["items"][0]["metrics"]
    assert metrics["competition"] == "LOW"
    assert metrics["average_monthly_searches"] == 0
    assert metrics["competition_index"] is None
    assert metrics["average_cpc"] is None
    assert metrics["low_top_of_page_bid"] == 1.25
    assert metrics["monthly_search_volumes"][0]["month"] == "JANUARY"
    assert metrics["monthly_search_volumes"][0]["monthly_searches"] == 0
    assert result["items"][0]["annotations"]["concepts"][0]["group_type"] == "NON_BRAND"
    assert result["aggregate_metrics"]["device_searches"][0]["device"] == "MOBILE"


def test_historical_metrics_uses_exact_endpoint_and_accounts_for_variants(sdk):
    client, service = sdk
    service.generate_keyword_historical_metrics.return_value = message(
        client,
        "GenerateKeywordHistoricalMetricsResponse",
        {
            "results": [
                {"text": "hike", "closeVariants": ["hikes"], "keywordMetrics": {}}
            ],
        },
    )
    result = ads.generate_keyword_historical_metrics(
        customer_id="1234567890",
        keywords=["hike", "hikes", "unknown"],
        location_ids=[],
    )
    request = service.generate_keyword_historical_metrics.call_args.kwargs["request"]
    assert list(request.keywords) == ["hike", "hikes", "unknown"]
    assert list(request.geo_target_constants) == []
    assert result["count"] == 1
    assert result["requested_count"] == 3
    assert result["unmatched_keywords"] == ["unknown"]
    assert result["items"][0]["metrics"]["average_monthly_searches"] is None
    service.generate_keyword_ideas.assert_not_called()


@pytest.mark.parametrize(
    "options",
    [
        {"start_year": 2025},
        {"start_year": 2025, "start_month": 12, "end_year": 2025, "end_month": 1},
        {"start_year": 0, "start_month": 1, "end_year": 2025, "end_month": 1},
    ],
)
def test_invalid_historical_ranges_do_not_call_google(sdk, options):
    _, service = sdk
    with pytest.raises(ValueError):
        ads.generate_keyword_historical_metrics(
            customer_id="1234567890", keywords=["hike"], **options
        )
    service.generate_keyword_historical_metrics.assert_not_called()


def test_empty_page_preserves_continuation_token(sdk):
    client, service = sdk
    page = message(
        client,
        "GenerateKeywordIdeaResponse",
        {"nextPageToken": "next", "totalSize": "2"},
    )
    service.generate_keyword_ideas.return_value = SimpleNamespace(pages=iter([page]))
    result = ads.generate_keyword_ideas(
        customer_id="1234567890", seed_mode="keywords", keywords=["hike"]
    )
    assert result["items"] == []
    assert result["next_page_token"] == "next"


@pytest.mark.parametrize("value", ["abc1234567890", "１２３４５６７８９０"])
def test_invalid_customer_ids_are_not_silently_rewritten(value):
    with pytest.raises(ValueError):
        ads.normalize_customer_id(value)


@pytest.mark.parametrize(
    "value",
    [
        "example.com",
        "file:///etc/passwd",
        "https://user:pass@example.com",
        "https://example.com:99999",
        "https://exa mple.com",
    ],
)
def test_url_validation(value):
    with pytest.raises(ValueError):
        ads.normalize_url_seed(value)


def test_keyword_limits_and_deduplication():
    assert ads.normalize_keyword_list(["hike", " hike ", ""]) == ["hike"]
    with pytest.raises(ValueError, match="20"):
        ads.normalize_keyword_list([str(i) for i in range(21)])
    with pytest.raises(ValueError, match="strings"):
        ads.normalize_keyword_list([None])
    assert (
        len(ads.normalize_keyword_list([str(i) for i in range(21)], max_keywords=10000))
        == 21
    )


def test_location_limits_and_worldwide():
    assert ads.build_geo_target_constant_resource_names([]) == []
    assert ads.build_geo_target_constant_resource_names(["2756", "2756"]) == [
        "geoTargetConstants/2756"
    ]
    with pytest.raises(ValueError, match="10"):
        ads.build_geo_target_constant_resource_names([str(i) for i in range(11)])


def test_retry_policy_excludes_quota_and_auth_errors():
    from google.api_core.exceptions import (
        DeadlineExceeded,
        PermissionDenied,
        ResourceExhausted,
        ServiceUnavailable,
    )

    def method(*, request, retry, timeout):
        assert retry._predicate(ServiceUnavailable("temporary"))
        assert retry._predicate(DeadlineExceeded("temporary"))
        assert not retry._predicate(ResourceExhausted("quota"))
        assert not retry._predicate(PermissionDenied("auth"))
        assert timeout == 30
        return "ok"

    assert ads._read_request(method, object()) == "ok"
