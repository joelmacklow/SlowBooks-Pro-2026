# Test Spec — Company logo copy in the top-right corner of financial reports

## Date
2026-04-30

## Verification targets

### 1. Shared PDF template coverage
Extend `tests/test_pdf_service_formatting.py` so rendered HTML for representative PDF document generators includes:
- `class="header-logo"`
- the resolved local company logo URI

Covered generators should include at least:
- invoice
- estimate/quote
- statement
- payroll payslip
- report

### 2. Header stability
Keep existing assertions for:
- A4 / 1.5cm page setup
- Inter font loading
- currency/date formatting
- escaped HTML fields
- report footer/page numbering behavior

### 3. Logo fallback behavior
Verify templates still render cleanly if no logo is configured by preserving existing behavior for the company name / text header path.

### 4. Local asset resolution
Ensure the test company logo resolves from local uploads/static handling, not from external URLs.

## Safety checks
- `./.venv/bin/python -m pytest tests/test_pdf_service_formatting.py tests/test_report_pdf_layout.py`
- `git diff --check`

## Review focus
- the right-side logo is present but not disruptive
- the report template matches the shared family behavior
- no external network dependency is introduced
