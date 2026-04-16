# Plan: update About screen branding to the NZ edition

## Summary
Refresh the About/splash screen copy so it reflects the current NZ-localized product identity rather than the older generic `2026 Edition` wording, and align the database version text with the current bundled Postgres version.

## Key Changes
- Change the splash/about subtitle to `2026 New Zealand Edition`.
- Change the matching sidebar edition label to `2026 New Zealand Edition`.
- Refresh the splash body copy so it explicitly frames the app as the NZ-localized clean-room reimplementation and updates the database reference to `PostgreSQL 18`.

## Test Plan
- Static verification of the changed strings in `index.html`.
- `git diff --check`.

## Constraints
- Keep this slice limited to the About/splash surface and its paired sidebar edition label.
- Do not broaden into a repo-wide branding rewrite.
