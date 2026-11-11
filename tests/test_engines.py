from decimal import Decimal

import pytest

from app.scans.engines import EngineError, gemini, google_aio, perplexity


@pytest.fixture
def perplexity_response():
    # Shape taken from the official Agent API reference; values are test-only.
    return {
        "id": "test-response",
        "status": "completed",
        "model": "test-model",
        "output": [
            {"type": "search_results", "results": [{"url": "https://retrieved-only.com"}]},
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Example answer.",
                        "annotations": [
                            {
                                "type": "url_citation",
                                "url": "https://example.com",
                                "title": "Example",
                            }
                        ],
                    }
                ],
            },
        ],
        "usage": {"cost": {"total_cost": 0.00452}},
    }


def test_perplexity_uses_answer_citations_not_search_results(perplexity_response):
    result = perplexity.parse(perplexity_response)
    assert [s["url"] for s in result.sources] == ["https://example.com"]
    assert result.cost_usd == Decimal("0.00452")
    assert result.cost_basis == "provider_reported"


def test_perplexity_unknown_cost_and_incomplete(perplexity_response):
    del perplexity_response["usage"]
    assert perplexity.parse(perplexity_response).cost_usd is None
    perplexity_response["status"] = "incomplete"
    with pytest.raises(EngineError):
        perplexity.parse(perplexity_response)


def test_perplexity_resolves_only_explicit_numbered_references(perplexity_response):
    perplexity_response["output"][0]["results"] = [
        {"id": 1, "url": "https://cited.com", "title": "Cited"},
        {"id": 2, "url": "https://not-cited.com", "title": "Not cited"},
    ]
    content = perplexity_response["output"][1]["content"][0]
    content["annotations"] = []
    content["text"] = "Answer [1]."
    assert [s["url"] for s in perplexity.parse(perplexity_response).sources] == [
        "https://cited.com"
    ]


def test_google_no_overview_is_distinct_from_not_cited():
    response = {
        "status_code": 20000,
        "cost": 0.004,
        "tasks": [
            {
                "status_code": 20000,
                "id": "test",
                "result": [{"items": [{"type": "organic", "url": "https://example.com"}]}],
            }
        ],
    }
    result = google_aio.parse(response)
    assert result.no_overview and not result.sources
    response["tasks"][0]["result"][0]["items"].append(
        {
            "type": "ai_overview",
            "items": [
                {
                    "text": "Answer",
                    "references": [
                        {
                            "type": "ai_overview_reference",
                            "url": "https://example.com",
                            "title": "Source",
                        }
                    ],
                }
            ],
        }
    )
    result = google_aio.parse(response)
    assert not result.no_overview and result.sources[0]["url"] == "https://example.com"


def test_gemini_is_disabled_before_any_request():
    with pytest.raises(EngineError, match="TERMS_RESTRICTED"):
        gemini.payload("test", "test", {})
