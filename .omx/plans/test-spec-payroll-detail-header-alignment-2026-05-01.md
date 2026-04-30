# Test spec — payroll detail header alignment

## Coverage goals
Ensure the payroll detail header renders the back button on the far right and keeps process immediately to its left when the process action is available.

## Scenarios
1. New pay-run detail screen places the back button in the right-side header action area.
2. Existing pay-run detail screen places process to the left of back.
3. The back button still uses the correct origin-aware label.

## Expected assertions
- The payroll detail HTML contains a right-side header action group.
- In the rendered header, the process button appears before the back button.
- The back button label remains unchanged.

## Test files to update or add
- `tests/js_nz_payroll_ui.test.js`
