import json
from datetime import timedelta
from typing import Any

import click
from flask import current_app

from app.models import (
    CostEntry,
    DomainReservation,
    EmailCapture,
    EmailDelivery,
    Event,
    FreeScan,
    ScanResult,
    db,
    now,
)


def register_commands() -> None:
    @current_app.cli.command("metrics")
    def metrics() -> None:
        """Validation counts. Calls must be confirmed, never inferred from link clicks."""
        names = [
            "scans_started",
            "scans_completed",
            "email_captures",
            "calls_booked",
            "scan_budget_exceeded",
            "email_delivery_needs_review",
        ]
        counts: dict[str, Any] = {
            name: db.session.query(Event).filter_by(name=name).count() for name in names
        }
        counts["email_capture_percent"] = (
            round(100 * counts["email_captures"] / counts["scans_completed"], 1)
            if counts["scans_completed"]
            else None
        )
        click.echo(json.dumps(counts, indent=2))

    @current_app.cli.command("record-call")
    @click.argument("scan_id")
    def record_call(scan_id: str) -> None:
        """Record one genuinely booked interview for a scan after calendar verification."""
        if not db.session.get(FreeScan, scan_id):
            raise click.ClickException("Scan not found.")
        if not db.session.query(Event).filter_by(name="calls_booked", scan_id=scan_id).first():
            db.session.add(Event(name="calls_booked", scan_id=scan_id))
            db.session.commit()
        click.echo("Confirmed call recorded.")

    @current_app.cli.command("costs")
    def costs() -> None:
        """Amounts explicitly returned by providers, plus unknown-cost counts."""
        for scan in db.session.query(FreeScan).order_by(FreeScan.created_at.desc()).limit(100):
            entries = db.session.query(CostEntry).filter_by(scan_id=scan.id).all()
            click.echo(
                json.dumps(
                    {
                        "scan_id": scan.id,
                        "provider_reported_usd": str(sum((e.amount_usd or 0) for e in entries)),
                        "unknown_cost_entries": sum(e.basis == "unknown" for e in entries),
                    }
                )
            )

    @current_app.cli.command("purge-expired")
    @click.option("apply", "--apply", is_flag=True, help="Apply deletion; default is a dry run.")
    def purge_expired(apply: bool) -> None:
        """Delete free scans and associated personal data older than 90 days."""
        ids = [
            s.id
            for s in db.session.query(FreeScan).filter(
                FreeScan.created_at < now() - timedelta(days=90)
            )
        ]
        click.echo(f"Expired scans: {len(ids)}")
        if not apply or not ids:
            return
        capture_ids = [
            c.id for c in db.session.query(EmailCapture).filter(EmailCapture.scan_id.in_(ids))
        ]
        db.session.query(EmailDelivery).filter(EmailDelivery.capture_id.in_(capture_ids)).delete(
            synchronize_session=False
        )
        models: list[Any] = [EmailCapture, CostEntry, ScanResult, DomainReservation, Event]
        for model in models:
            db.session.query(model).filter(model.scan_id.in_(ids)).delete(synchronize_session=False)
        db.session.query(FreeScan).filter(FreeScan.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
        click.echo("Expired scan data deleted.")
