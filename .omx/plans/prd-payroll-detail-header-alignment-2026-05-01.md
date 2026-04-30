# Payroll detail header alignment

## Objective
Align the payroll detail screen header with the rest of the routed detail pages by moving the back action to the far right of the header bar and placing the process action immediately to its left.

## Constraints
- Keep the change limited to payroll detail header layout.
- Preserve existing payroll behavior and actions.
- Do not alter the routed-detail navigation pattern introduced in the previous slice.

## Implementation sketch
- Update the payroll detail screen header markup so the right-side action group contains the process button first and the back button last.
- Keep the back button label/origin logic intact.
- Verify the rendered HTML order in payroll UI tests.

## Impacted files
- `app/static/js/payroll.js`
- `tests/js_nz_payroll_ui.test.js`

## Test plan
- Run the targeted payroll UI test.
- Run the broader hash-routing test to ensure the routed-detail helper still behaves.
- Run `git diff --check`.

## Risk notes
- Low risk because the change is presentation-only.
- The main failure mode is accidental regression in the detail header markup order.
