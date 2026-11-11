from datetime import timedelta
from typing import Any

import httpx
from celery import shared_task
from flask import current_app

from app.models import EmailCapture, EmailDelivery, Event, FreeScan, db, now


def email_content(
    sequence: int, capture: EmailCapture, scan: FreeScan, config: dict[str, Any]
) -> tuple[str, str]:
    base = config["PUBLIC_BASE_URL"]
    link = f"{base}/r/{scan.report_slug}"
    if sequence == 1:
        subject = f"Your visibility report for {scan.business_name}"
        body = f"Here's your report: {link}\n\nStart with the suggested action and review the evidence on the report. These are sampled API observations; they don't predict every customer's answer."
    elif sequence == 2:
        subject = "Did you make the change?"
        body = f"Did you make the suggested change in your report? Reply yes or no.\n\nYour report: {link}\n\nWe haven't re-scanned your site, so we don't know whether its visibility has changed."
    else:
        subject = "Would a weekly visibility check help?"
        price = config["PRODUCT"]["starter_price_usd"]
        body = f"We're exploring weekly visibility checks at ${price}/month. The paid product isn't available yet.\n\nBook a 15-minute conversation: {config['FOUNDER_CALENDAR_URL']}\n\nYour report: {link}"
    body += f"\n\nUnsubscribe: {base}/unsubscribe/{capture.unsubscribe_token}"
    return subject, body


@shared_task(name="app.mail.send_due_emails")  # type: ignore[untyped-decorator]
def send_due_emails() -> None:
    config = dict(current_app.config)
    if not config["POSTMARK_SERVER_TOKEN"] or not config["EMAIL_FROM"]:
        return
    captures = db.session.query(EmailCapture).filter(EmailCapture.unsubscribed_at.is_(None)).all()
    for capture in captures:
        for sequence, day in [(1, 0), (2, 3), (3, 7)]:
            if sequence > 1 and not config["POSTMARK_FOLLOWUP_STREAM"]:
                continue
            if capture.created_at.replace(tzinfo=now().tzinfo) > now() - timedelta(days=day):
                continue
            if sequence == 3 and not config["FOUNDER_CALENDAR_URL"]:
                continue
            # Claim a unique delivery before sending: ambiguous failures require human review,
            # never an automatic duplicate send. Beat runs as a single service.
            if (
                db.session.query(EmailDelivery)
                .filter_by(capture_id=capture.id, sequence=sequence)
                .first()
            ):
                continue
            scan = db.session.get(FreeScan, capture.scan_id)
            if not scan:
                continue
            subject, body = email_content(sequence, capture, scan, config)
            delivery = EmailDelivery(capture_id=capture.id, sequence=sequence)
            db.session.add(delivery)
            db.session.commit()
            try:
                response = httpx.post(
                    config["PRODUCT"]["postmark_endpoint"],
                    headers={"X-Postmark-Server-Token": config["POSTMARK_SERVER_TOKEN"]},
                    json={
                        "From": config["EMAIL_FROM"],
                        "To": capture.email,
                        "Subject": subject,
                        "TextBody": body,
                        "MessageStream": "outbound"
                        if sequence == 1
                        else config["POSTMARK_FOLLOWUP_STREAM"],
                        "Headers": [
                            {
                                "Name": "List-Unsubscribe",
                                "Value": f"<{config['PUBLIC_BASE_URL']}/unsubscribe/{capture.unsubscribe_token}>",
                            },
                            {
                                "Name": "List-Unsubscribe-Post",
                                "Value": "List-Unsubscribe=One-Click",
                            },
                        ],
                    },
                    timeout=15,
                )
                response.raise_for_status()
                if response.json().get("ErrorCode") != 0:
                    raise ValueError("mail delivery rejected")
                delivery.status = "sent"
                delivery.sent_at = now()
                db.session.add(
                    Event(
                        name="report_email_sent" if sequence == 1 else "followup_email_sent",
                        scan_id=scan.id,
                    )
                )
            except (httpx.HTTPError, ValueError):
                delivery.status = "needs_review"
                db.session.add(Event(name="email_delivery_needs_review", scan_id=scan.id))
            db.session.commit()
