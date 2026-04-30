# Company Snapshot QB Style Cleanup Specification

## Goal
Align the Company Snapshot dashboard visuals more closely with the original QB-style dashboard while leaving the underlying widgets and data behavior unchanged.

## Required Behavior
- Snapshot hero and widget containers should use flatter, more rectangular QB-style framing instead of modern rounded cards.
- Dashboard comparison bars and cash-flow bars should render with squared edges, stronger frame/baseline treatment, and QB-style color/gradient cues.
- The watchlist table should use sharper QB-style borders, header shading, and row separators.
- Dark theme styling should preserve the same shape language and readable contrast.

## Constraints
- Do not add, remove, or reorder widgets as part of this slice.
- Do not change dashboard API calls, permissions, or data formatting logic.
- Do not introduce new packages, image assets, or chart libraries.

## Verification
- Targeted JS dashboard render coverage for the new presentation hooks/classes.
- Targeted regression run for dashboard RBAC rendering.
- `git diff --check` plus a focused manual code review of light/dark theme styling.
