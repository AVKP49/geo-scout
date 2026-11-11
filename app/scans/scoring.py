from collections import Counter
from typing import Any
from urllib.parse import urlsplit


def matches_domain(url: str, domain: str) -> bool:
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return host == domain or host.endswith("." + domain)


def source_state(sources: list[dict[str, Any]], domain: str) -> str:
    for position, source in enumerate(sources):
        if matches_domain(source["url"], domain):
            return "first_mention" if position < 3 else "mentioned"
    return "not_cited"


def summarize(queries: list[dict[str, Any]], results: list[dict[str, Any]]) -> dict[str, Any]:
    checked = [r for r in results if r["state"] not in {"failed", "no_overview"}]
    denominator = sum(queries[r["query_index"]]["weight"] for r in checked)
    numerator = sum(
        queries[r["query_index"]]["weight"]
        for r in checked
        if r["state"] in {"first_mention", "mentioned"}
    )
    cited = sum(r["state"] in {"first_mention", "mentioned"} for r in checked)
    return {
        "score": round(100 * numerator / denominator) if denominator else None,
        "cited": cited,
        "checked": len(checked),
        "expected": len(results),
        "rate": round(100 * cited / len(checked)) if checked else None,
        "excluded": len(results) - len(checked),
        "demand": sum(q["demand"] for q in queries)
        if all(q.get("demand") is not None for q in queries)
        else None,
    }


def competitors(results: list[dict[str, Any]], domain: str) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    evidence: dict[str, dict[str, Any]] = {}
    for result in results:
        seen: set[str] = set()
        for source in result.get("sources", []):
            host = (urlsplit(source["url"]).hostname or "").removeprefix("www.")
            if host and not matches_domain(source["url"], domain) and host not in seen:
                seen.add(host)
                counts[host] += 1
                evidence[host] = source
    # These are cited sources, not necessarily competing businesses (directories may appear).
    return [
        {"domain": host, "count": count, **evidence[host]} for host, count in counts.most_common(1)
    ]
