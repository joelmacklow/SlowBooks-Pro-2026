# Balance Sheet Current Earnings Bugfix Specification

## Goal
Make the balance sheet include earnings-to-date in equity and clearly show whether the report balances.

## Required Behavior
- The balance sheet must include unclosed earnings-to-date in the equity section/total.
- The response and rendered report must show:
  - `Total Liabilities + Equity`
  - `Difference` between Assets and Liabilities+Equity
- A balanced report should show a zero difference.
- Existing asset/liability/equity account rows must continue to use natural positive signs.

## Constraints
- Do not add a separate closing-entry workflow in this slice.
- Do not change report permissions or the as-of-date contract.
- Keep the UI/PDF changes limited to the balance sheet.

## Verification
- Targeted Python tests for balanced totals and current-earnings inclusion.
- Targeted JS rendering test for the balance-sheet rows.
- `node --check app/static/js/reports.js`
- `git diff --check`
