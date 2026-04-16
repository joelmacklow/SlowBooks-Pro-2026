# Security Review — Upstream bug/security carryover for NZ branch (2026-04-16)

## Scope Reviewed
- `app/services/email_service.py`
- `app/services/closing_date.py`
- `app/routes/uploads.py`
- `app/static/js/utils.js`
- `app/services/accounting.py`
- `app/templates/statement_pdf.html`
- `Dockerfile`
- `scripts/backup.sh`
- related regression tests

## Review Focus
- Email header-injection and SMTP connection lifecycle safety
- Timing-safe secret comparison for closing-date overrides
- Logo upload MIME hardening for SVG/XSS risk
- Frontend escaping/date correctness that affects rendered and injected UI content
- Journal-line validation before posting
- Container/runtime least-privilege and shell-pipeline robustness

## Findings
1. **Email sending is now safer against header injection and leaked SMTP sessions**
   - Recipient and subject headers are stripped of CR/LF before MIME headers are built.
   - SMTP connections are now closed on failure as well as success, covering login/auth errors.

2. **Closing-date password checks now use a timing-safe comparison**
   - `hmac.compare_digest()` replaces plain string equality for the password override path.

3. **Logo upload no longer accepts SVG**
   - The route now allows PNG/JPEG/GIF only, removing the most obvious scriptable image surface from the logo-upload flow.

4. **Frontend escaping/date helpers are safer and less error-prone**
   - `escapeHtml()` now escapes single quotes as well as the existing HTML metacharacters.
   - `todayISO()` now uses the local calendar date rather than UTC truncation, avoiding date drift around timezone boundaries.

5. **Journal creation now rejects invalid line shapes earlier**
   - Negative amounts and lines with both debit and credit are rejected before balance posting logic runs.

6. **Infrastructure hardening is improved without changing app behavior**
   - The container now runs as a dedicated non-root user.
   - `scripts/backup.sh` now uses `set -eo pipefail` so pipeline failures are not silently swallowed.

## Residual Risks
- Attachment upload/download hardening from the upstream refactor remains deferred because that feature does not exist yet on this NZ branch.
- Multi-company `X-Company-Id` header behavior remains deferred to a future real multi-company context-switching slice.
- The Python suite still emits pre-existing SQLite `ResourceWarning` noise unrelated to these fixes.

## Verification
- `.venv/bin/python -m unittest tests.test_document_email_delivery tests.test_tax_upload_auth_gap_cleanup tests.test_pdf_service_formatting tests.test_closing_date_security tests.test_accounting_validation tests.test_docker_config`
- `.venv/bin/python -m unittest discover -s tests`
- `for f in tests/js_*.test.js; do node "$f"; done`
- `.venv/bin/python -m py_compile app/routes/uploads.py app/services/accounting.py app/services/closing_date.py app/services/email_service.py tests/test_document_email_delivery.py tests/test_tax_upload_auth_gap_cleanup.py tests/test_accounting_validation.py tests/test_closing_date_security.py tests/test_pdf_service_formatting.py tests/test_docker_config.py`
- `bash -n scripts/backup.sh scripts/docker-entrypoint.sh`
- `git diff --check`

## Conclusion
- No new CRITICAL/HIGH issues were introduced by this carryover slice.
- The implemented subset is appropriate for `nz-localization`; the remaining upstream items should stay deferred until their NZ-specific product or architectural prerequisites exist.
