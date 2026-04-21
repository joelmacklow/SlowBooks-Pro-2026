# Test Spec — Invoice template follow-up fixes

## Date
2026-04-21

## Verification targets
- Extend `tests/test_pdf_service_formatting.py` invoice assertions to cover:
  - logo path replacing company-name header text block
  - GST number rendering
  - no duplicate top-of-document due-date subtitle
  - richer Bill To / Payment Advice customer details
  - nowrap markers/classes for invoice number / amount-due fields
- Keep HTML escaping assertions intact for untrusted invoice/customer/company fields.

## Safety checks
- `./.venv/bin/python -m unittest tests.test_pdf_service_formatting tests.test_nz_address_labels`
- `./.venv/bin/python -m py_compile app/services/pdf_service.py tests/test_pdf_service_formatting.py`
- `git diff --check`
