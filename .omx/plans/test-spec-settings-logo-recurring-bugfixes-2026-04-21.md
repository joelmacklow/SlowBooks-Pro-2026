# Test Spec — Settings logo upload + recurring invoice schedule bugfixes

## Date
2026-04-21

## Verification targets

### Settings / logo upload
- JS test for settings page logo upload copy and accept attribute:
  - no SVG advertised
  - accepted file types align with backend support
- Python upload tests for:
  - successful logo upload through the managed writable directory
  - clean error on write-permission failure during file save
  - SVG still rejected with aligned error messaging

### Recurring invoice editor
- JS test for recurring editor preview behavior:
  - changing frequency recalculates `Next Invoice Date`
  - changing start date recalculates `Next Invoice Date`
  - changing terms to `next_month_day:1` recalculates `Invoice Due Date`
  - labels make the distinction between invoice-generation date and invoice due date clear
- Python recurring route test for update behavior:
  - `customer_id` and `start_date` accepted on update
  - `next_due` recalculated when schedule-affecting fields change

## Safety checks
- `node tests/js_settings_logo_upload.test.js` (or updated equivalent)
- `node tests/js_recurring_detail_flow.test.js`
- `./.venv/bin/python -m unittest tests.test_tax_upload_auth_gap_cleanup tests.test_upload_size_hardening tests.test_recurring_schedule_updates`
- `./.venv/bin/python -m py_compile app/main.py app/routes/uploads.py app/routes/recurring.py app/services/recurring_service.py app/static/js/settings.js app/static/js/recurring.js`
- `git diff --check`
