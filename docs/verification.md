# Verification — 2026-11-11

## Completed locally

- Ruff lint and strict mypy checks passed.
- 26 unit/integration tests passed. Two browser cases are skipped unless RUN_E2E=1.
- Fixture scan start → worker → report passed with an engine failure; no paid calls.
- Domain boundaries, Perplexity numbered citations and retrieved-but-uncited exclusions tested.
- Domain cooldown/expiry, rate limits and CSRF checks passed.
- Consented email sequence tested with fake Postmark responses; no real mail sent.
- Costs preserve sub-cent amounts; unavailable costs remain unknown.
- SAMPLE pages create no scan records or analytics events.
- Both migrations applied; Alembic db check reported no schema drift.
- Dependency audit reported no known vulnerabilities for pinned installed packages.
- Copy scan found none of the specified banned terms in templates/emails.
- Local metrics: zero scans, zero captures, zero bookings. No invented traction.

## Not yet verified

- Browser visual/E2E checks: Chromium failed with macOS MachPort permission denial;
  the Meta browser fallback expected /proc/net/tcp. Browser tests are committed for Linux CI.
- Standalone Tailwind execution was killed in this session. Checked-in Tailwind preflight
  and custom CSS serve the preview; the workflow has a checksum-pinned utility build step.
- CI is a template in docs/ci.workflow.yml because OAuth lacks workflow scope. The app
  code itself is pushed to the private repository.
- Docker build, PostgreSQL/Redis services, email sender verification, authenticated
  provider responses, manual citation accuracy and actual scan billing.
- Public staging/production and Ajay's review. Phase 0 is not launch-complete.

See launch.md for release gates. Local preview: http://127.0.0.1:5050 while its server runs.
