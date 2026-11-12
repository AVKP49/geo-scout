# GEO Scout

Phase 0 of a local AI-search visibility product. Flask, Jinja, Tailwind and HTMX;
PostgreSQL, Celery and Redis for live scanning. Public source repository:
https://github.com/AVKP49/geo-scout

## Current status

Public preview: **https://avkp49.github.io/geo-scout/**

GitHub Pages serves the business form, editable suggested questions and three fictional
sample reports. It does not run live scans or collect email addresses. The full Flask
backend requires separate hosting.

Working local preview and tested scan orchestration using fixtures. Real adapters exist
for Google AI Overviews via DataForSEO and Perplexity Agent API. Live scans are disabled
until credentials, costs, commercial terms and accuracy are verified. Gemini is excluded
because its grounding terms restrict this tracking use. No billing/dashboard is built.

See [original spec](docs/SPEC.md), [build decisions](docs/decisions.md),
[vendor verification](docs/vendor-check.md) and [launch checklist](docs/launch.md).

## Local preview (no accounts needed)

To regenerate the GitHub Pages preview, run `.venv/bin/python scripts/export_pages.py`.
Publish the contents of `dist/pages/` to the `gh-pages` branch. Pages uses that branch's
root directory; no API credentials or database records are included in the export.

```sh
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.lock
cp .env.example .env
.venv/bin/flask --app wsgi db upgrade
.venv/bin/flask --app wsgi run --host 127.0.0.1 --port 5050
```

Open http://127.0.0.1:5050. Explore the editable query form and three clearly labeled
sample reports. Preview does not consume API credit or capture emails.

Tailwind preflight and HTMX are committed; the design uses app.css. To build utilities after template edits:
`python3.12 scripts/build_assets.py`. Upstream artifacts are pinned and SHA-256 checked.

## Live scanning setup

1. Supply PostgreSQL and Redis. Local Compose needs `LOCAL_DB_PASSWORD`; then run
   `docker compose up -d`. Set DATABASE_URL to the local PostgreSQL port 5434 and
   REDIS_URL to the local Redis port 6381. SQLite/memory limits are development-only.
2. Configure DataForSEO, Perplexity and Turnstile through ignored `.env` locally or
   hosting secrets. Never paste keys into code or GitHub issues. Gemini is not required.
3. Configure Postmark sender verification and an appropriate message stream; add a real
   founder calendar URL. Follow-up emails only go to visitors who expressly consent.
4. Apply migrations. Start the worker: `.venv/bin/celery -A celery_app.celery worker
   --loglevel=warning --concurrency=2`. Start exactly one Beat process for email scheduling.
5. Set SCAN_ENABLED=true only after the launch checklist has passed. The UI remains
   unavailable if required keys are absent. A broker failure returns an actionable error.

Backend variables and engine endpoints/effort/limits/templates/rules live in `.env` and
`config/product.json`. No API call depends on a browser-held secret.

## Verification

```sh
.venv/bin/ruff check app tests scripts wsgi.py celery_app.py
.venv/bin/mypy app
.venv/bin/pytest -q
.venv/bin/playwright install chromium
RUN_E2E=1 .venv/bin/pytest tests/test_e2e.py -q
.venv/bin/pip-audit --no-deps --disable-pip -r requirements.lock
```

No tests call paid APIs. E2E scan coverage uses isolated fixtures, not real results.
The GitHub Actions template covers lint, strict type checks, unit/integration/E2E checks,
dependency and secret audits, and the container build. It is currently saved at
`docs/ci.workflow.yml`: the connected GitHub token lacks workflow scope. After GitHub
authentication is updated, move it to `.github/workflows/ci.yml` and push to enable CI.

## Validation metrics and privacy maintenance

`flask --app wsgi metrics` reports real scan/capture/call events. After verifying a real
calendar booking, use `flask --app wsgi record-call SCAN_ID`; a link click is never counted
as a booking. `flask --app wsgi costs` reports provider-returned amounts and unknown costs.

Schedule `flask --app wsgi purge-expired --apply` daily to enforce 90-day free-scan retention.
Without --apply it is a dry run. Keep backup retention aligned with this policy. Process
deletion requests within 30 days; free-scan data has no paid-account lifecycle yet.

## Deployment

GitHub holds source/CI; **GitHub Pages cannot run this backend**. `Dockerfile` and
`fly.toml` are deployment-ready configuration, not proof of a running service. Provision
hosting, PostgreSQL and Redis, set secrets, review exact proxy hops, deploy staging, test
the scan and email failure paths, and obtain Ajay's staging review before production.

Rollback: deploy the preceding application image; keep Phase 0 tables intact. The initial
migration can be downgraded only on an empty development DB. In production, prefer a
forward repair migration; downgrading would delete scan/customer data.
