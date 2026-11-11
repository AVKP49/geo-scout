from datetime import timedelta
from decimal import Decimal

import pytest

from app.models import CostEntry, DomainReservation, EmailCapture, Event, FreeScan, db, now
from app.scans.engines import EngineAnswer, EngineError
from app.scans.tasks import run_free_scan


@pytest.fixture
def live_test(app, monkeypatch):
    app.config.update(
        SCAN_ENABLED=True,
        PERPLEXITY_API_KEY="test-only",
        DATAFORSEO_LOGIN="test-only",
        DATAFORSEO_PASSWORD="test-only",
        TURNSTILE_SITE_KEY="test-only",
        TURNSTILE_SECRET_KEY="test-only",
    )
    monkeypatch.setattr("app.web.routes.verify_captcha", lambda *args: True)
    monkeypatch.setattr(
        "app.web.routes.fetch_page",
        lambda url: {
            "url": url,
            "status": 200,
            "text": "HVAC services in Fremont",
            "schema": False,
            "links": [],
        },
    )
    monkeypatch.setattr(
        "app.scans.tasks.lookup", lambda id, qs: [{**q, "demand": None} for q in qs]
    )
    monkeypatch.setattr(
        "app.web.routes.run_free_scan.apply_async", lambda args, **kw: run_free_scan(args[0])
    )

    def fake(engine, query, city, config):
        if engine == "gemini":
            raise EngineError("TERMS_RESTRICTED")
        if engine == "google_aio":
            raise EngineError("HTTP_ERROR")
        return EngineAnswer(
            sources=[{"url": "https://example.com/service", "title": "Example"}],
            snippet="Fixture answer",
            cost_usd=Decimal("0.005"),
            cost_basis="provider_reported",
        )

    monkeypatch.setattr("app.scans.tasks.request_engine", fake)
    return {
        "business_name": "Example",
        "website_url": "https://example.com",
        "city": "Fremont, CA",
        "category": "hvac",
        "queries": ["AC repair Fremont", "HVAC Fremont", "Example reviews"],
        "captcha": "test-only",
    }


def test_scan_to_report_with_engine_failure(app, client, live_test):
    response = client.post("/api/v1/free-scans", json=live_test)
    assert response.status_code == 202
    id = response.json["data"]["id"]
    status = client.get(f"/api/v1/free-scans/{id}").json["data"]
    assert status["status"] == "complete"
    report = client.get(status["report_url"])
    assert b"Cited in" in report.data and b"3 of 3" in report.data
    assert b"Not checked" in report.data and b"Not covered" in report.data
    assert b"Unavailable" in report.data
    assert b"Fixture answer" in report.data
    with app.app_context():
        assert db.session.query(Event).filter_by(name="scans_completed").count() == 1
        assert sum(c.amount_usd or 0 for c in db.session.query(CostEntry)) == Decimal("0.015")
    assert client.post("/api/v1/free-scans", json=live_test).status_code == 409
    assert (
        client.post(
            "/api/v1/free-scans", json={**live_test, "website_url": "https://shop.example.com"}
        ).status_code
        == 409
    )


def test_invalid_queries_and_disabled_scan(client, live_test, app):
    assert (
        client.post(
            "/api/v1/free-scans", json={**live_test, "queries": ["same", "Same", "other"]}
        ).status_code
        == 400
    )
    app.config["SCAN_ENABLED"] = False
    assert client.post("/api/v1/free-scans", json=live_test).status_code == 503


def test_rate_limit_is_enforced(client, live_test):
    statuses = [
        client.post("/api/v1/free-scans", json={**live_test, "queries": []}).status_code
        for _ in range(6)
    ]
    assert statuses[-1] == 429


def test_unsubscribe_get_does_not_mutate(app, client):
    with app.app_context():
        scan = FreeScan(
            business_name="Example",
            website_url="https://example.com",
            normalized_domain="example.com",
            city="Fremont",
            category="hvac",
            queries=[],
            ip_hash="test",
        )
        db.session.add(scan)
        db.session.flush()
        capture = EmailCapture(scan_id=scan.id, email="test@example.com")
        db.session.add(capture)
        db.session.commit()
        token = capture.unsubscribe_token
        client.get(f"/unsubscribe/{token}")
        assert capture.unsubscribed_at is None
        assert client.post(f"/unsubscribe/{token}").status_code == 200
        db.session.refresh(capture)
        assert capture.unsubscribed_at is not None


def test_cooldown_can_expire(app, client, live_test):
    first = client.post("/api/v1/free-scans", json=live_test)
    assert first.status_code == 202
    with app.app_context():
        reservation = db.session.get(DomainReservation, "example.com")
        reservation.expires_at = now() - timedelta(seconds=1)
        db.session.commit()
    assert client.post("/api/v1/free-scans", json=live_test).status_code == 202


def test_csrf_gate_and_sample_isolation(app, client):
    app.config["WTF_CSRF_ENABLED"] = True
    assert client.post("/api/v1/free-scans", json={}).status_code == 400
    for kind in ["hvac", "plumber", "food"]:
        page = client.get(f"/sample/{kind}")
        assert page.status_code == 200
        assert b"Fictional business" in page.data
    with app.app_context():
        assert db.session.query(FreeScan).count() == 0
        assert db.session.query(Event).count() == 0
