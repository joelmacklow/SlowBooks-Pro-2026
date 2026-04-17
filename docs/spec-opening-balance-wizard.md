# Spec: Opening Balance Setup Wizard

## Goal
Provide a guided setup screen for small-business owners to enter opening balances without requiring manual journal-entry knowledge.

## Required Behavior
- Add a new **Opening Balances** page under Accounting.
- The page is only available when the chart of accounts is ready through one of:
  - a built-in chart template loaded from Settings,
  - a successful Xero import, or
  - a legacy database that already has active balance-sheet accounts.
- When the chart is not ready, show a blocked state with links to Settings and Xero Import.
- The ready state must list active asset, liability, and equity accounts with amount inputs.
- Saving must create one balanced journal entry using the existing journal engine.
- Users may either:
  - balance the entry manually, or
  - enable an auto-balance helper that posts the difference to a chosen equity account.

## API
- Add `GET /api/opening-balances/status` returning readiness metadata.
- Add `POST /api/opening-balances` accepting:
  - `date`
  - `description`
  - optional `reference`
  - `lines[]` of `{ account_id, amount }`
  - optional `auto_balance_account_id`
- Posting rules:
  - positive asset amounts debit the account
  - positive liability/equity amounts credit the account
  - negative amounts invert the normal side
  - zero lines are ignored
  - reject when the chart is not ready
  - reject when no non-zero lines remain
  - reject unbalanced entries unless auto-balance is enabled

## State Tracking
- Persist chart readiness metadata in settings:
  - `chart_setup_source`
  - `chart_setup_ready_at`
- Set the metadata when a chart template load succeeds and when Xero import succeeds.

## Verification
- Backend tests for readiness tracking and opening-balance posting.
- Frontend tests for blocked/ready states, balancing behavior, and route registration.
- `git diff --check`
