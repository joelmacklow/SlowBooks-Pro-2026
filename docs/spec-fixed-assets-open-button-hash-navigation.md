# Fixed Assets Open Button Hash Navigation Fix Specification

## Goal
Ensure programmatic navigations carry route query parameters into the rendered page by keeping `location.hash` in sync.

## Required Behavior
- Calling `App.navigate('#/fixed-assets/detail?id=1')` must update `location.hash` to that exact value before the detail page reads query params.
- Existing same-hash navigations should still render without unnecessary hash churn.
- The fix should work for fixed-assets and any other programmatic route that relies on hash query params.

## Constraints
- Do not reintroduce duplicate row links.
- Do not replace hash routing with a different navigation system in this slice.

## Verification
- Targeted app hash-routing regression coverage.
- Targeted fixed-assets UI regression coverage.
- `git diff --check`
