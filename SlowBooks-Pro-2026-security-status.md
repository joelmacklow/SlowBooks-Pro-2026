## Security status summary

Snapshot date: 2026-04-18

This summary reconciles the original `SlowBooks-Pro-2026-threat-model.md` findings with the current repository state after the completed hardening slices.

## Resolved findings

### 1. Public report and statement exposure — resolved
- **Original risk:** unauthenticated financial reports and statement routes (`TM-001`, `TM-004`)
- **Current state:** report, statement PDF, and statement email routes now require explicit permissions in `app/routes/reports.py`.
- **Evidence:** `app/routes/reports.py`, report-auth regression coverage in tests
- **Result:** remote unauthenticated report/statement access described in the original threat model is no longer possible through those routes.

### 2. Raw `X-Company-Database` trust boundary bypass — resolved
- **Original risk:** request-scoped DB selection trusted raw company headers (`TM-002`)
- **Current state:** `app/database.py:get_db()` now derives non-default company DB selection from validated auth context instead of trusting raw headers.
- **Evidence:** `app/database.py`
- **Result:** invalid or unauthenticated scoped requests no longer pivot directly into another company DB session.

### 3. First-user bootstrap takeover — materially reduced / resolved for default path
- **Original risk:** arbitrary fresh-instance takeover through `/api/auth/bootstrap-admin` (`TM-003`)
- **Current state:** bootstrap is allowed from loopback by default and otherwise requires a valid bootstrap token.
- **Evidence:** `app/routes/auth.py`, `.env.example`
- **Result:** anonymous non-loopback bootstrap is blocked; local first-run remains possible.

### 4. Plaintext closing-date secret storage — resolved
- **Original risk:** `closing_date_password` stored and compared in plaintext (`TM-006`)
- **Current state:** new values are hashed, API responses mask the secret, and legacy plaintext values are upgraded after successful use.
- **Evidence:** `app/services/closing_date.py`, `app/routes/settings.py`
- **Result:** new plaintext storage for this secret is removed.

### 5. SMTP secret exposure through settings/runtime — materially reduced
- **Original risk:** plaintext SMTP secret storage and use (`TM-006`)
- **Current state:** settings responses mask SMTP secrets, runtime SMTP auth uses `SMTP_PASSWORD` from environment only, and legacy DB SMTP password rows are cleaned up once env-managed SMTP is ready.
- **Evidence:** `app/services/email_service.py`, `app/routes/settings.py`, `app/static/js/settings.js`
- **Result:** runtime no longer depends on DB-stored SMTP passwords; settings/UI no longer act as an SMTP secret display surface.

### 6. Oversized upload/import abuse — resolved for targeted file-ingest paths
- **Original risk:** oversized upload/import requests could exhaust resources (`TM-007`)
- **Current state:** explicit file-size caps now protect logo upload, CSV imports, IIF import/validate, bank statement ingest, and Xero import bundles.
- **Evidence:** `app/services/upload_limits.py`, related route modules
- **Result:** these file-ingest paths now fail fast with `413` instead of fully processing arbitrarily large payloads.

### 7. Burst abuse on high-risk email/import surfaces — partially resolved
- **Original risk:** repeated email/import abuse could degrade service (`TM-004`, `TM-007`)
- **Current state:** lightweight in-memory per-host throttling protects SMTP test email, document email routes, major import/upload endpoints, and backup create/download/restore operations.
- **Evidence:** `app/services/rate_limit.py`, targeted routes including `app/routes/backups.py`
- **Result:** abuse resistance is improved across the main high-value operational surfaces in the default single-process deployment model.

### 8. Wildcard CORS browser exposure — resolved
- **Original risk:** wildcard browser origins could read sensitive responses (`TM-005`)
- **Current state:** `app/main.py` now uses env-driven `CORS_ALLOW_ORIGINS` with loopback-safe defaults rather than wildcard origins.
- **Evidence:** `app/main.py`, `app/config.py`, `.env.example`, `tests/test_docker_config.py`
- **Result:** the previous wildcard CORS posture is no longer present by default.

### 9. Sensitive-route auth regressions — resolved
- **Original risk:** future sensitive routes could silently lose auth/permission coverage (`Issue 9` from the threat model resolution list)
- **Current state:** the repo now includes a broad route-auth contract harness covering sensitive routers and expected permission requirements.
- **Evidence:** `tests/test_sensitive_route_auth_contract.py`
- **Result:** permission drift on covered sensitive endpoints now fails CI immediately.

### 10. Operational safeguard drift — materially reduced
- **Original risk:** future refactors could silently drop rate limits, upload size checks, secret masking, bootstrap trust checks, or explicit CORS configuration.
- **Current state:** the repo now includes an operational security contract harness that locks those safeguard markers and invariants.
- **Evidence:** `tests/test_operational_security_contract.py`
- **Result:** key operational controls are now protected by focused regression coverage instead of relying on manual review alone.

### 11. Insecure deployment defaults — materially reduced
- **Original risk:** public Postgres exposure, weak default credentials, and debug-default posture (`TM-008`)
- **Current state:** bundled Postgres is no longer published by default, compose now requires explicit `POSTGRES_PASSWORD`, docs use non-legacy credential examples, and debug defaults are false.
- **Evidence:** `docker-compose.yml`, `.env.example`, `README.md`, `INSTALL.md`, `app/config.py`
- **Result:** copy-paste deployment risk is significantly reduced.

## Partially resolved findings

### 1. Rate limiting is process-local only
- **Original risk:** burst abuse and repeated expensive operations (`TM-007`)
- **Current state:** rate limiting exists, but it is in-memory and per-process.
- **Evidence:** `app/services/rate_limit.py`
- **Residual risk:** multi-worker or multi-instance deployments will not share rate-limit state.

### 2. Secrets-at-rest outside the completed slices still depend on broader operational controls
- **Original risk:** DB/backup readers could recover sensitive data (`TM-006`)
- **Current state:** closing-date and SMTP secret handling were hardened, and managed backup artifacts are now tightened to owner-only directory/file permissions when created or served. Backups still contain application data and any remaining sensitive settings/records.
- **Evidence:** `app/services/backup_service.py`, `app/routes/backups.py`, settings model, repo backup behavior
- **Residual risk:** backups remain high-value artifacts and still require host-level protection, encrypted storage, and careful operator handling.

### 3. Deployment defaults are safer, but operator misconfiguration is still possible
- **Original risk:** reachable hosts with unsafe defaults (`TM-008`)
- **Current state:** defaults are safer and docs are clearer.
- **Evidence:** deployment files and config helpers
- **Residual risk:** a determined operator can still publish services or set weak secrets manually.

## Still-open findings

### 1. Expensive non-file operations are still synchronous — still open
- **Original risk:** availability degradation from heavy PDF/report/email work (`TM-007`)
- **Current state:** size limits and throttling help, but document generation/email/import work still runs inline in request handlers.
- **Evidence:** document email + PDF routes remain synchronous
- **Status:** still open
- **Recommended next step:** move expensive email/PDF/import work to background jobs or asynchronous worker lanes where appropriate.

## Recommended next actions

1. **Medium** — Consider background/offline processing for heavy PDF/email/import workflows.
2. **Medium** — Review backup/restore operational guidance and artifact protection posture.
3. **Medium** — Replace per-process in-memory throttling with a shared store if the app is deployed across multiple workers or instances.
4. **Low** — Extend the contract harness as new sensitive routes or ingest surfaces are added.

## Short conclusion

The highest-risk findings from the original threat model—public report exposure, raw company-scope trust, bootstrap takeover, wildcard CORS, plaintext operational secret handling, insecure deployment defaults, and uncontrolled upload size—have been materially reduced or resolved in the repository. The main remaining repo-level work is operational hardening around synchronous expensive workflows, backup protection posture, and more durable shared throttling for multi-instance deployments.
