import os
import threading
from decimal import Decimal
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

from app.scans.engines import EngineAnswer, EngineError
from app.scans.tasks import run_free_scan

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_E2E") != "1", reason="Run with RUN_E2E=1 and installed Chromium"
)


@pytest.fixture
def browser_server(app, monkeypatch):
    app.config.update(
        SCAN_ENABLED=True,
        PERPLEXITY_API_KEY="fixture-only",
        DATAFORSEO_LOGIN="fixture-only",
        DATAFORSEO_PASSWORD="fixture-only",
        TURNSTILE_SITE_KEY="fixture-only",
        TURNSTILE_SECRET_KEY="fixture-only",
    )
    monkeypatch.setattr("app.web.routes.verify_captcha", lambda *args: True)
    monkeypatch.setattr(
        "app.web.routes.fetch_page",
        lambda url: {
            "url": url,
            "status": 200,
            "text": "Fremont HVAC services",
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

    def fixture_answer(engine, query, city, config):
        if engine == "gemini":
            raise EngineError("TERMS_RESTRICTED")
        return EngineAnswer(
            sources=[{"url": "https://example.com", "title": "Fixture citation"}],
            snippet="Fixture-only answer",
            cost_usd=Decimal("0.001"),
            cost_basis="provider_reported",
        )

    monkeypatch.setattr("app.scans.tasks.request_engine", fixture_answer)
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join()


@pytest.mark.parametrize("width", [360, 1440])
def test_public_flow_and_layout(browser_server, width):
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 1000})
        page.route("https://challenges.cloudflare.com/**", lambda route: route.abort())
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(browser_server)
        page.locator("#business_name").fill("Example")
        page.locator("#website_url").fill("example.com")
        page.locator("#city").fill("Fremont, CA")
        page.locator("#category").select_option("hvac")
        page.locator("#suggest-button").click()
        page.locator("#query-0").wait_for(state="visible")
        assert page.locator("#query-list input").count() == 5
        page.locator("#query-0").fill("HVAC repair Fremont")
        page.locator("#start-button").click()
        page.wait_for_url("**/r/**")
        assert "Cited in" in page.locator(".report-hero").inner_text()
        assert "10 of 10" in page.locator(".report-hero").inner_text()
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        page.locator(".evidence summary").first.click()
        assert "Fixture citation" in page.locator(".evidence").first.inner_text()
        assert not errors
        out = Path("docs/screenshots")
        out.mkdir(parents=True, exist_ok=True)
        # Screenshots for publication use explicitly watermarked sample routes only.
        page.goto(browser_server + "/sample/hvac")
        assert "Fictional business" in page.locator(".sample-banner").inner_text()
        page.screenshot(path=str(out / f"report-{width}.png"), full_page=True)
        page.goto(browser_server)
        page.screenshot(path=str(out / f"landing-{width}.png"), full_page=True)
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        browser.close()
