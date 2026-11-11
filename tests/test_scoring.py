from app.scans.scoring import matches_domain, source_state, summarize


def test_weighted_score_and_failures():
    queries = [{"weight": 2, "demand": 100}, {"weight": 1, "demand": 50}]
    results = [
        {"query_index": 0, "state": "first_mention"},
        {"query_index": 0, "state": "not_cited"},
        {"query_index": 1, "state": "mentioned"},
        {"query_index": 1, "state": "failed"},
        {"query_index": 0, "state": "no_overview"},
    ]
    # (2 + 1) / (2 + 2 + 1) = 60%; unweighted 2/3 = 67%.
    result = summarize(queries, results)
    assert result == {
        "score": 60,
        "cited": 2,
        "checked": 3,
        "expected": 5,
        "rate": 67,
        "excluded": 2,
        "demand": 150,
    }


def test_unavailable_is_not_zero():
    assert summarize([{"weight": 2}], [{"query_index": 0, "state": "failed"}])["score"] is None
    assert summarize([{"weight": 2}], [])["demand"] is None


def test_domain_boundary_and_position():
    assert matches_domain("https://service.example.com/page", "example.com")
    assert not matches_domain("https://notexample.com", "example.com")
    assert not matches_domain("https://example.com.evil.com", "example.com")
    sources = [{"url": "https://other.com"}] * 3 + [{"url": "https://example.com"}]
    assert source_state(sources, "example.com") == "mentioned"
