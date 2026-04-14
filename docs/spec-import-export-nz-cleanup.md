# NZ Import/Export Cleanup Specification

## Goal
Make CSV and IIF import/export consistent with the NZ branch while preserving QuickBooks IIF interoperability.

## Required Behavior
- CSV export remains NZ-first for user-facing headers and values.
- IIF export should use the current GST control-account naming where compatibility is not harmed and should stop presenting stale US sales-tax wording in exported splits/messages.
- IIF import must continue accepting legacy-compatible inputs while also handling current NZ GST/account/address assumptions correctly.
- IIF UI and related docs must describe the feature as QuickBooks interoperability for the NZ branch, not as a US-tax-specific workflow.

## Constraints
- Preserve QuickBooks IIF wire structure and practical interoperability.
- No new dependencies.
- Keep backward compatibility for legacy incoming labels where feasible.
- Do not combine this slice with multi-currency or NZ income-tax replacement work.

## Verification
- Backend tests for CSV export labels and IIF export/import behavior.
- Frontend tests for IIF UI wording.
- Full Python/JS suites, syntax checks, and `git diff --check`.
