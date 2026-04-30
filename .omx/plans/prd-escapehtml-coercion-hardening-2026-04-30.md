# PRD: Harden shared HTML escaping against non-string inputs

## Objective
Make the shared `escapeHtml()` helper robust when callers pass numbers, nullish values, or other non-string primitives.

## Constraints
- Preserve HTML escaping behavior for existing string inputs.
- Avoid changing the behavior of unrelated UI code.
- Keep the fix centralized rather than patching every callsite.

## Implementation sketch
- Coerce the input to a string at the start of `escapeHtml()` in `app/static/js/utils.js`.
- Add regression coverage that exercises numeric and nullish inputs.
- Keep the payroll-specific fix in place as defense in depth.

## Impacted files
- `app/static/js/utils.js`
- `tests/js_formatting.test.js`

## Test plan
- Run the formatting utility test.
- Re-run the payroll UI test to ensure the earlier crash remains fixed.
- Run diff hygiene checks.

## Risk notes
- This changes a shared utility, so verify no UI text rendering regressions in common paths.
