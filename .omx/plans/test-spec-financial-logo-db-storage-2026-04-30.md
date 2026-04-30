# Test Spec — Persist uploaded company logo in the database and rebalance report header

## Date
2026-04-30

## Verification targets

### 1. Upload persistence
Extend upload tests so successful logo upload asserts:
- the file still saves to the upload directory
- the settings table stores a DB-backed `company_logo_data_uri` value
- the stored value looks like a data URI, not just a filesystem path

### 2. PDF rendering fallback
Add a PDF formatting regression that verifies:
- if `company_logo_data_uri` is present, the rendered HTML uses it
- the report/invoice family still renders logo markup correctly

### 3. Header sizing tweak
Add a lightweight template regression that checks:
- the shared logo block is slightly larger than before
- the report header tile is slightly smaller / narrower than before

### 4. Existing invariants
Keep assertions for:
- Inter font loading
- A4 / 1.5cm page setup
- currency/date formatting
- escaped HTML fields
- report footer/page numbering behavior

## Safety checks
- `./.venv/bin/python -m pytest tests/test_pdf_service_formatting.py tests/test_report_pdf_layout.py tests/test_tax_upload_auth_gap_cleanup.py`
- `git diff --check`

## Review focus
- the DB-backed logo is used as a durable fallback
- the settings UI and PDF templates still show the same logo after reloads
- the header size tweak does not disturb report tables or document content
