# Test Spec — Document template refresh from DOCX references

## Date
2026-04-21

## Verification targets

### 1. Page setup regression coverage
Extend `tests/test_pdf_service_formatting.py` so generated HTML for:
- invoice
- estimate/quote
- credit note
- purchase order
- statement
- payroll payslip
- report

asserts the correct page rule:
- portrait docs: `@page { size: A4; margin: 1.5cm; }`
- report template: A4 portrait/landscape variants still preserve `margin: 1.5cm`

### 2. Reference-family structure checks
Add/assert rendered HTML includes stable markers for the refreshed layout, such as:
- invoice / quote / credit note family titles and shared structural classes
- statement summary/aging section markers
- purchase order delivery/details section markers
- footer/remittance/payment-advice markers if implemented

### 3. Existing formatting and safety invariants
Keep/extend assertions for:
- NZ date rendering
- currency rendering
- escaped untrusted HTML fields
- expected company settings rendering

### 4. Optional targeted snapshot-style assertions
Where useful, assert presence of stable class names or section labels instead of brittle whole-template string matches.

## Safety checks
- `./.venv/bin/python -m unittest tests.test_pdf_service_formatting`
- targeted related tests that exercise PDF/email flows if touched:
  - `tests.test_document_email_delivery`
  - `tests.test_nz_address_labels`
  - `tests.test_payroll_payslips`
- `./.venv/bin/python -m py_compile app/services/pdf_service.py`
- `git diff --check`

## Review focus
- no letter-sized page rules remain in active printable templates
- no stale template variants remain without a clear reason
- no loss of existing escaped rendering behavior
- no print-only CSS that clips totals/footer content on A4 with 1.5cm margins
