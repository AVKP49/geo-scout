from datetime import timedelta
from typing import Any

from email_validator import EmailNotValidError, validate_email
from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy.exc import IntegrityError
from werkzeug.wrappers import Response as WerkzeugResponse

from app import csrf, limiter
from app.models import DomainReservation, EmailCapture, Event, FreeScan, db, now
from app.reports import report_data, sample_report
from app.scans.tasks import run_free_scan
from app.security import SiteError, fetch_page, ip_hash, normalize_url, verify_captcha

web = Blueprint("web", __name__)


def readiness() -> tuple[bool, list[str]]:
    required = (
        "PERPLEXITY_API_KEY",
        "DATAFORSEO_LOGIN",
        "DATAFORSEO_PASSWORD",
        "TURNSTILE_SITE_KEY",
        "TURNSTILE_SECRET_KEY",
    )
    missing = [key for key in required if not current_app.config[key]]
    return bool(current_app.config["SCAN_ENABLED"] and not missing), missing


def api_error(code: str, message: str, status: int) -> tuple[Response, int]:
    return jsonify(data=None, error={"code": code, "message": message}), status


@web.get("/")
def landing() -> str:
    return render_template(
        "landing.html", ready=readiness()[0], site_key=current_app.config["TURNSTILE_SITE_KEY"]
    )


@web.get("/healthz")
@limiter.exempt
def health() -> Response:
    return jsonify(status="ok", phase=0, live_scans=readiness()[0])


@web.post("/api/v1/queries/suggest")
def suggestions() -> Response | tuple[Response, int]:
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict) or not isinstance(data.get("category"), str):
        return api_error("INPUT", "Send your business details and category.", 400)
    product = current_app.config["PRODUCT"]
    category = product["categories"].get(data.get("category", ""))
    if not category:
        return api_error("CATEGORY", "Choose a business category.", 400)
    if not all(
        isinstance(data.get(k), str) and 1 <= len(data[k].strip()) <= 100
        for k in ("business_name", "city")
    ):
        return api_error("INPUT", "Enter your business name and city first.", 400)
    queries = [
        text.format(
            city=data["city"].strip(),
            business=data["business_name"].strip(),
            service=category["service"],
        )
        for text in category.get("queries", product["default_queries"])
    ]
    return jsonify(data={"queries": queries}, error=None)


@web.post("/api/v1/free-scans")
@limiter.limit(lambda: current_app.config["PRODUCT"]["scan_rate_limit"])
def start_scan() -> tuple[Response, int]:
    if not readiness()[0]:
        return api_error(
            "NOT_READY", "Live scans are not available yet. Explore a sample report below.", 503
        )
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return api_error("INPUT", "Send a scan form.", 400)
    product = current_app.config["PRODUCT"]
    for key, low, high in [("business_name", 2, 100), ("city", 2, 100), ("website_url", 3, 2048)]:
        if not isinstance(data.get(key), str) or not low <= len(data[key].strip()) <= high:
            return api_error("INPUT", f"Check {key.replace('_', ' ')}.", 400)
    if not isinstance(data.get("category"), str) or data["category"] not in product["categories"]:
        return api_error("CATEGORY", "Choose a category.", 400)
    texts = data.get("queries")
    if (
        not isinstance(texts, list)
        or not product["min_queries"] <= len(texts) <= product["max_queries"]
    ):
        return api_error(
            "QUERIES", f"Use {product['min_queries']} to {product['max_queries']} questions.", 400
        )
    if any(not isinstance(q, str) or not 1 <= len(q.strip()) <= 200 for q in texts):
        return api_error("QUERIES", "Each question needs 1–200 characters.", 400)
    texts = [q.strip() for q in texts]
    if len(set(q.casefold() for q in texts)) != len(texts):
        return api_error("QUERIES", "Remove duplicate questions.", 400)
    if not verify_captcha(data.get("captcha", ""), request.remote_addr or ""):
        return api_error("CAPTCHA", "Complete the security check and try again.", 400)
    try:
        website, domain = normalize_url(data["website_url"])
        reservation = db.session.get(DomainReservation, domain)
        if reservation and reservation.expires_at.replace(tzinfo=now().tzinfo) > now():
            return api_error(
                "SCAN_LIMIT", "This website already has a free scan within the last 30 days.", 409
            )
        first = fetch_page(website)
        if normalize_url(first["url"])[1] != domain:
            return api_error(
                "REDIRECT_DOMAIN",
                "This site redirects to another domain. Enter the final website URL.",
                400,
            )
    except SiteError as error:
        return api_error("WEBSITE", str(error), 400)
    business = data["business_name"].strip()
    scan = FreeScan(
        business_name=business,
        website_url=website,
        normalized_domain=domain,
        city=data["city"].strip(),
        category=data["category"],
        site_evidence=[first],
        queries=[
            {"text": text, "weight": 1 if business.casefold() in text.casefold() else 2}
            for text in texts
        ],
        ip_hash=ip_hash(request.remote_addr or ""),
    )
    try:
        # Expired reservations are deleted conditionally; concurrent insert is protected by the PK.
        db.session.query(DomainReservation).filter(
            DomainReservation.domain == domain, DomainReservation.expires_at <= now()
        ).delete(synchronize_session="fetch")
        db.session.add(scan)
        db.session.flush()
        db.session.add(
            DomainReservation(
                domain=domain,
                scan_id=scan.id,
                expires_at=now() + timedelta(days=product["cooldown_days"]),
            )
        )
        db.session.add(Event(name="scans_started", scan_id=scan.id))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return api_error("SCAN_LIMIT", "A free scan for this website already exists.", 409)
    try:
        run_free_scan.apply_async(args=[scan.id], retry=False)
    except Exception:
        scan.status = "failed"
        db.session.query(DomainReservation).filter_by(scan_id=scan.id).delete()
        db.session.add(Event(name="scans_failed", scan_id=scan.id))
        db.session.commit()
        return api_error(
            "QUEUE_UNAVAILABLE", "The scan worker is unavailable. Please try again later.", 503
        )
    return jsonify(
        data={"id": scan.id, "status_url": url_for("web.scan_progress", scan_id=scan.id)},
        error=None,
    ), 202


def get_scan(scan_id: str) -> FreeScan:
    scan = db.session.get(FreeScan, scan_id)
    if not scan:
        abort(404)
    if scan.status in {"queued", "running"} and scan.created_at.replace(
        tzinfo=now().tzinfo
    ) < now() - timedelta(minutes=10):
        scan.status = "failed"
        db.session.commit()
    return scan


@web.get("/scan/<scan_id>")
def scan_progress(scan_id: str) -> str | WerkzeugResponse:
    scan = get_scan(scan_id)
    if scan.status == "complete":
        return redirect(url_for("web.report", slug=scan.report_slug))
    return render_template("progress.html", scan=scan)


@web.get("/api/v1/free-scans/<scan_id>")
def scan_status(scan_id: str) -> Response:
    scan = get_scan(scan_id)
    return jsonify(
        data={
            "status": scan.status,
            "progress": scan.progress,
            "total": len(scan.queries),
            "report_url": url_for("web.report", slug=scan.report_slug)
            if scan.status == "complete"
            else None,
        },
        error=None,
    )


@web.get("/scan/<scan_id>/fragment")
def progress_fragment(scan_id: str) -> str:
    return render_template("progress_wrapper.html", scan=get_scan(scan_id))


@web.get("/r/<slug>")
def report(slug: str) -> str:
    scan = db.session.query(FreeScan).filter_by(report_slug=slug, status="complete").first()
    if not scan:
        abort(404)
    return render_template(
        "report.html",
        report=report_data(scan, current_app.config["PRODUCT"]),
        email_ready=bool(
            current_app.config["POSTMARK_SERVER_TOKEN"] and current_app.config["EMAIL_FROM"]
        ),
    )


@web.get("/sample/<kind>")
def example(kind: str) -> str:
    try:
        report = sample_report(kind, current_app.config["PRODUCT"])
    except KeyError:
        abort(404)
    return render_template("report.html", report=report, email_ready=False)


@web.post("/r/<slug>/email")
@limiter.limit("5 per hour")
def capture_email(slug: str) -> tuple[Response, int]:
    scan = db.session.query(FreeScan).filter_by(report_slug=slug, status="complete").first()
    if not scan:
        abort(404)
    if not current_app.config["POSTMARK_SERVER_TOKEN"] or not current_app.config["EMAIL_FROM"]:
        return api_error(
            "EMAIL_UNAVAILABLE", "Email delivery is not available yet. Save the report link.", 503
        )
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return api_error("INPUT", "Send your email and consent choice.", 400)
    if data.get("consent") is not True:
        return api_error("CONSENT", "Please confirm you want the report and follow-up emails.", 400)
    try:
        email = validate_email(str(data.get("email", "")), check_deliverability=False).normalized
    except EmailNotValidError:
        return api_error("EMAIL", "Enter a valid email address.", 400)
    try:
        db.session.add(EmailCapture(scan_id=scan.id, email=email))
        db.session.add(Event(name="email_captures", scan_id=scan.id))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return api_error("ALREADY_SAVED", "An email has already been saved for this report.", 409)
    return jsonify(
        data={"message": "Saved. Your report email is queued for delivery."}, error=None
    ), 202


@web.get("/unsubscribe/<token>")
def unsubscribe_page(token: str) -> str:
    if not db.session.query(EmailCapture).filter_by(unsubscribe_token=token).first():
        abort(404)
    return render_template("unsubscribe.html", token=token, done=False)


@web.post("/unsubscribe/<token>")
@csrf.exempt  # type: ignore[untyped-decorator]
@limiter.limit("20 per hour")
def unsubscribe(token: str) -> str:
    capture = db.session.query(EmailCapture).filter_by(unsubscribe_token=token).first()
    if not capture:
        abort(404)
    capture.unsubscribed_at = now()
    db.session.commit()
    return render_template("unsubscribe.html", token=token, done=True)


@web.get("/privacy")
def privacy() -> str:
    return render_template("privacy.html")


@web.get("/robots.txt")
def robots() -> Response:
    return Response(
        "User-agent: *\nDisallow: /r/\nDisallow: /scan/\nDisallow: /api/\n", mimetype="text/plain"
    )


@web.app_errorhandler(404)
def missing(error: Any) -> tuple[str, int]:
    return render_template("error.html", message="We couldn't find that page."), 404


@web.app_errorhandler(429)
def limited(error: Any) -> tuple[Response, int]:
    return api_error("RATE_LIMIT", "Too many requests. Please try again later.", 429)
