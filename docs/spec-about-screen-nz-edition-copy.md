# Spec: update About screen branding to the NZ edition

## Goal
Make the About/splash screen identify the product as the NZ-localized edition and stop referring to the old `2026 Edition` / `PostgreSQL 16` wording.

## Required Behavior
- The splash/about subtitle must read `2026 New Zealand Edition`.
- The matching sidebar edition label must read `2026 New Zealand Edition`.
- The About popup descriptive text must explicitly describe the app as the NZ-localized clean-room reimplementation.
- The About popup database/version line must reference `PostgreSQL 18`.

## Verification
- Confirm `index.html` contains the new edition wording and no longer contains the old About-screen `2026 Edition` or `PostgreSQL 16` strings.
- `git diff --check` must pass.

## Assumptions
- The product name remains `Slowbooks Pro`; only the edition/about wording changes.
- The broader README/docs branding remains out of scope for this slice.
