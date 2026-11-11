from datetime import timedelta

from app.mail import send_due_emails
from app.models import EmailCapture, EmailDelivery, Event, FreeScan, db, now


def test_email_sequence_does_not_duplicate_and_respects_unsubscribe(app, monkeypatch):
    app.config.update(
        POSTMARK_SERVER_TOKEN="fixture-only",
        EMAIL_FROM="sender@example.com",
        FOUNDER_CALENDAR_URL="https://example.com/book",
    )
    calls = []

    class Result:
        def raise_for_status(self):
            pass

        def json(self):
            return {"ErrorCode": 0}

    monkeypatch.setattr("app.mail.httpx.post", lambda *a, **k: calls.append(k["json"]) or Result())
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
        capture = EmailCapture(
            scan_id=scan.id, email="test@example.com", created_at=now() - timedelta(days=8)
        )
        db.session.add(capture)
        db.session.commit()
        send_due_emails()
        assert len(calls) == 3
        assert all("Unsubscribe:" in c["TextBody"] for c in calls)
        assert db.session.query(EmailDelivery).filter_by(status="sent").count() == 3
        send_due_emails()
        assert len(calls) == 3
        capture.unsubscribed_at = now()
        db.session.commit()
        send_due_emails()
        assert len(calls) == 3
        assert db.session.query(Event).filter_by(name="report_email_sent").count() == 1
