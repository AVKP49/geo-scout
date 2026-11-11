from typing import Any

from app.models import FreeScan, ScanResult, db
from app.scans.diagnosis import recommend
from app.scans.scoring import competitors, summarize


def report_data(scan: FreeScan, product: dict[str, Any]) -> dict[str, Any]:
    results = [
        {
            "query_index": r.query_index,
            "engine": r.engine,
            "state": r.state,
            "sources": r.sources,
            "snippet": r.snippet,
            "error_code": r.error_code,
        }
        for r in db.session.query(ScanResult)
        .filter_by(scan_id=scan.id)
        .order_by(ScanResult.query_index, ScanResult.engine)
    ]
    rows = []
    for i, q in enumerate(scan.queries):
        own = [r for r in results if r["query_index"] == i]
        summary = summarize([q], [{**r, "query_index": 0} for r in own])
        rows.append(
            {
                **q,
                "results": own,
                "summary": summary,
                "sources": competitors(own, scan.normalized_domain),
                "recommendation": recommend(
                    q["text"], scan.city, scan.site_evidence, product["recommendations"]
                ),
            }
        )
    # Prioritize uncited money queries; avoid an invented numerical opportunity score.
    rows.sort(key=lambda q: (q["summary"]["cited"] > 0, -q["weight"], -(q.get("demand") or 0)))
    return {
        "business_name": scan.business_name,
        "website_url": scan.website_url,
        "city": scan.city,
        "date": scan.completed_at,
        "rows": rows,
        "summary": summarize(scan.queries, results),
        "top_fix": rows[0]["recommendation"],
        "sample": False,
        "slug": scan.report_slug,
    }


def sample_report(kind: str, product: dict[str, Any]) -> dict[str, Any]:
    # Fictional examples are explicitly labeled; no sample records enter live tables or events.
    presets = {
        "hvac": ("Example Heating & Air", "Fremont, CA", "hvac"),
        "plumber": ("Example Plumbing", "San Jose, CA", "plumber"),
        "food": ("Example Recipe Journal", "Mountain View, CA", "food_blog"),
    }
    if kind not in presets:
        raise KeyError(kind)
    business, city, category = presets[kind]
    c = product["categories"][category]
    texts = [
        t.format(city=city, business=business, service=c["service"])
        for t in c.get("queries", product["default_queries"])
    ]
    queries = [
        {
            "text": text,
            "weight": 1 if business in text else 2,
            "demand": [260, 170, 110, 90, 40][i],
            "demand_source": "Illustrative sample values; not vendor measurements",
        }
        for i, text in enumerate(texts)
    ]
    results = [
        {
            "query_index": i,
            "engine": engine,
            "state": "failed"
            if engine == "gemini"
            else ("first_mention" if (i + j) % 3 == 0 else "not_cited"),
            "sources": [],
            "snippet": "Illustrative sample. No live API answer was used.",
            "error_code": "TERMS_RESTRICTED" if engine == "gemini" else None,
        }
        for i in range(5)
        for j, engine in enumerate(product["engines"])
    ]
    recommendation = {
        "title": "Answer the service question clearly",
        "action": "Add a factual service-area section using your own verified details.",
        "evidence": "Illustrative example of a recommendation; no website was checked.",
        "draft": "Suggested heading: AC repair in Fremont\n\n[Business name] provides [verified services] in [actual service area]. Contact us via [verified contact method] to discuss your needs.",
        "pages": [],
    }
    rows = [
        {
            **q,
            "summary": summarize(
                [q], [{**r, "query_index": 0} for r in results if r["query_index"] == i]
            ),
            "results": [r for r in results if r["query_index"] == i],
            "sources": [],
            "recommendation": recommendation,
        }
        for i, q in enumerate(queries)
    ]
    return {
        "business_name": business,
        "website_url": "https://example.com",
        "city": city,
        "date": None,
        "rows": rows,
        "summary": summarize(queries, results),
        "top_fix": recommendation,
        "sample": True,
        "slug": kind,
    }
