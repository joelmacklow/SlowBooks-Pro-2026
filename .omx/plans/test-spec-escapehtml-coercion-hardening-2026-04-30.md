# Test Spec: Harden shared HTML escaping against non-string inputs

## Coverage goals
1. `escapeHtml()` should still correctly escape normal strings.
2. `escapeHtml()` should accept numbers without throwing.
3. `escapeHtml()` should treat nullish values as empty strings.

## Assertions
- `escapeHtml(2027)` returns `2027` safely escaped as text.
- `escapeHtml(null)` returns an empty string.
- Existing string escaping behavior remains unchanged.

## Verification
- `node tests/js_formatting.test.js`
- `node tests/js_nz_payroll_ui.test.js`
- `git diff --check`
