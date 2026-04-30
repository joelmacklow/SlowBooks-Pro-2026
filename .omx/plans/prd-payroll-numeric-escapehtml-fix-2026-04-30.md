# PRD: Fix payroll activation crash on numeric tax year rendering

## Objective
Prevent the payroll page from crashing when it renders a numeric tax year through `escapeHtml()`.

## Constraints
- Keep the payroll page behavior and layout unchanged.
- Make the fix as narrow as possible.
- Preserve existing HTML escaping for untrusted values.

## Implementation sketch
- Convert the payroll tax year to a string before passing it to `escapeHtml()` in the list and detail views.
- Add a regression test that fails if payroll rendering passes a non-string into `escapeHtml()`.

## Impacted files
- `app/static/js/payroll.js`
- `tests/js_nz_payroll_ui.test.js`

## Test plan
- Run the payroll UI regression test.
- Run any focused JS test that exercises payroll rendering.
- Confirm the specific `str.replace is not a function` crash no longer occurs.

## Risk notes
- Low risk: this only changes how one numeric display value is coerced before escaping.
