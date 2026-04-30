# Test Spec: Fix payroll activation crash on numeric tax year rendering

## Coverage goals
1. Payroll rendering should accept numeric `tax_year` values.
2. `escapeHtml()` should only receive strings in the payroll page render path.
3. The payroll HTML should still include the tax year value and other existing content.

## Assertions
- Rendering the payroll page with `tax_year: 2027` does not throw.
- The rendered HTML includes `2027`.
- The test harness can enforce that `escapeHtml()` receives a string for payroll fields.

## Verification
- `node tests/js_nz_payroll_ui.test.js`
- Optional: targeted Node smoke test for payroll render if needed
