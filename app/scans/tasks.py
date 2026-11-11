import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from typing import Any
from urllib.parse import urlsplit

from celery import shared_task
from flask import current_app

from app.models import CostEntry, DomainReservation, Event, FreeScan, ScanResult, db, now
from app.scans.client import request_engine
from app.scans.demand import lookup
from app.scans.engines import EngineAnswer, EngineError
from app.scans.scoring import source_state
from app.security import SiteError, fetch_page


def crawl(scan: FreeScan, maximum: int) -> list[dict[str, Any]]:
    pages = list(scan.site_evidence)
    first = pages[0] if pages else {}
    host = urlsplit(first.get("url", scan.website_url)).hostname
    seen = {first.get("url")}
    for url in first.get("links", []):
        if len(pages) >= maximum:
            break
        parsed = urlsplit(url)
        if (
            parsed.hostname != host
            or url in seen
            or parsed.query
            or parsed.fragment
            or parsed.path.lower().endswith((".pdf", ".jpg", ".png", ".zip"))
        ):
            continue
        seen.add(url)
        try:
            pages.append(fetch_page(url))
        except SiteError:
            pages.append({"url": url, "status": None, "text": "", "schema": False})
    return [{k: v for k, v in p.items() if k != "links"} for p in pages]


def run_one(
    engine: str, index: int, query: str, city: str, config: dict[str, Any]
) -> tuple[str, int, EngineAnswer | None, str | None, list[tuple[Decimal | None, str]]]:
    costs: list[tuple[Decimal | None, str]] = []
    for attempt in range(3):
        try:
            answer = request_engine(engine, query, city, config)
            costs.append((answer.cost_usd, answer.cost_basis))
            return engine, index, answer, None, costs
        except EngineError as error:
            if error.code in {"TERMS_RESTRICTED", "NOT_CONFIGURED"}:
                costs.append((Decimal(0), "not_called"))
                return engine, index, None, error.code, costs
            costs.append(
                (error.cost_usd, "provider_reported" if error.cost_usd is not None else "unknown")
            )
            if not error.retryable or attempt == 2:
                return engine, index, None, error.code, costs
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


@shared_task(name="app.scans.tasks.run_free_scan")  # type: ignore[untyped-decorator]
def run_free_scan(scan_id: str) -> None:
    # Atomic claim prevents duplicate task delivery from charging the engines twice.
    claimed = (
        db.session.query(FreeScan)
        .filter_by(id=scan_id, status="queued")
        .update({"status": "running"})
    )
    db.session.commit()
    if not claimed:
        return
    scan = db.session.get(FreeScan, scan_id)
    assert scan is not None
    config = dict(current_app.config)
    engines = config["PRODUCT"]["engines"]
    try:
        scan.site_evidence = crawl(scan, config["PRODUCT"]["max_site_pages"])
        scan.queries = lookup(scan_id, scan.queries)
        scan.progress = {engine: 0 for engine in engines}
        db.session.commit()
        with ThreadPoolExecutor(max_workers=5) as executor:
            jobs = [
                executor.submit(run_one, engine, i, q["text"], scan.city, config)
                for i, q in enumerate(scan.queries)
                for engine in engines
            ]
            for future in as_completed(jobs):
                engine, index, answer, error, costs = future.result()
                for cost, basis in costs:
                    db.session.add(
                        CostEntry(scan_id=scan_id, provider=engine, amount_usd=cost, basis=basis)
                    )
                state = (
                    "failed"
                    if answer is None
                    else (
                        "no_overview"
                        if answer.no_overview
                        else source_state(answer.sources, scan.normalized_domain)
                    )
                )
                db.session.add(
                    ScanResult(
                        scan_id=scan_id,
                        query_index=index,
                        engine=engine,
                        state=state,
                        sources=answer.sources if answer else [],
                        snippet=answer.snippet if answer else "",
                        response_ref=answer.response_ref if answer else None,
                        error_code=error,
                        usage=answer.usage if answer else {},
                        cost_usd=answer.cost_usd if answer else None,
                        cost_basis=answer.cost_basis if answer else "unknown",
                        attempts=len(costs),
                    )
                )
                scan.progress = {**scan.progress, engine: scan.progress[engine] + 1}
                db.session.commit()
        good = (
            db.session.query(ScanResult)
            .filter(ScanResult.scan_id == scan_id, ScanResult.state != "failed")
            .count()
        )
        scan.status = "complete" if good else "failed"
        scan.completed_at = now()
        db.session.add(Event(name="scans_completed" if good else "scans_failed", scan_id=scan_id))
        total = sum(
            (entry.amount_usd or Decimal(0))
            for entry in db.session.query(CostEntry).filter_by(scan_id=scan_id)
        )
        if total > Decimal(config["PRODUCT"]["scan_budget_usd"]):
            db.session.add(Event(name="scan_budget_exceeded", scan_id=scan_id))
            current_app.logger.warning("Scan cost budget exceeded; review cost ledger.")
        if not good:
            db.session.query(DomainReservation).filter_by(scan_id=scan_id).delete()
        db.session.commit()
    except Exception:
        db.session.rollback()
        scan = db.session.get(FreeScan, scan_id)
        if scan:
            scan.status = "failed"
            scan.completed_at = now()
            db.session.query(DomainReservation).filter_by(scan_id=scan_id).delete()
            db.session.add(Event(name="scans_failed", scan_id=scan_id))
            db.session.commit()
        current_app.logger.error(
            "Scan job failed; provider data and credentials omitted from logs."
        )
