# Plan: bank reconciliation split coding + import balance bugfix

## Objective
Plan the next banking slice that adds split coding from the reconciliation detail view and fixes the import bug where incomplete/failed reconciliation runs still mutate the linked bank account balance.

## Why this is next
- `docs/localization_summary.md:184` marks Bank Rules MVP as Priority 1 on top of the existing reconciliation/import foundations.
- `docs/localization_summary.md:215-216` explicitly says bank-rule work should integrate with the current import/reconciliation model and stay behind the current auth/audit expectations.
- The current reconciliation detail view already exposes one-shot matching/coding, so split coding is the natural next banking workflow upgrade.

## Current state

### Reconciliation detail flow
- Reconciliation detail pulls imported lines and shows one-action match/coding controls: `app/routes/banking.py:516-537`, `app/static/js/banking.js:358-404`
- Single-account coding only is available today via `/transactions/{txn_id}/code`: `app/routes/banking.py:407-451`
- The coding payload only allows one account plus description: `app/schemas/banking.py`
- The bank transaction model only stores one `category_account_id` and one `transaction_id`: `app/models/banking.py:51-82`

### Import-side balance mutation bug
- Statement import inserts `BankTransaction` rows and immediately adds the imported net amount to `BankAccount.balance`: `app/services/ofx_import.py:181-233`
- Reconciliation creation/completion does not reverse or defer that import-time balance mutation; completion only validates cleared totals and flips reconciliation status: `app/routes/banking.py:504-512`, `app/routes/banking.py:516-537`, `app/routes/banking.py:495-513`
- Therefore, if reconciliation is never completed or fails difference validation, imported batch amounts have already leaked into the bank account balance.

## Recommended feature shape

### 1. Split coding from reconciliation detail
Introduce explicit split coding as a reconciliation-only extension of the existing bank transaction coding flow.

#### Recommended backend shape
- Add a dedicated split persistence model, e.g. `BankTransactionSplit`, with:
  - `bank_transaction_id`
  - `account_id`
  - `amount`
  - `description`
  - `line_order`
- Add a new endpoint:
  - `POST /api/banking/transactions/{txn_id}/code-split`
- Keep the current `/code` endpoint for simple one-line coding.
- Split coding should create **one journal entry** with:
  - one bank-account balancing line
  - N chart-of-accounts split lines
- Persist enough metadata to show a readable matched label/summary later in reconciliation and the register.

#### Recommended UI shape
- Add a “Split code” action beside the current “Code transaction” flow in reconciliation detail.
- Open a modal/editor that allows multiple lines:
  - account
  - amount
  - description
- Require the split lines to total the absolute statement amount before allowing submit.
- Show a clear summary after successful application, e.g. “Split coded across 3 accounts”.

### 2. Import balance bugfix
Move imported-statement balance mutation to reconciliation completion rather than import time.

#### Recommended behavior
- `import_transactions()` should create/import the bank lines and import batch metadata **without mutating `BankAccount.balance`**.
- When a reconciliation created for an `import_batch_id` is successfully completed:
  - apply the net imported batch delta to `BankAccount.balance` exactly once
  - stamp that batch as applied so retries/reopens cannot double-apply

#### Suggested data support
Choose one of:
- add `balance_applied_at` / `balance_applied_reconciliation_id` on `Reconciliation`, or
- add a small `BankImportBatch` model that tracks:
  - `import_batch_id`
  - `bank_account_id`
  - `net_amount`
  - `balance_applied_at`
  - `applied_reconciliation_id`

The second option is cleaner if more import lifecycle behavior is expected later.

## Constraints
- Preserve current explicit approval for matching/coding; no silent auto-posting.
- Reuse the existing `create_journal_entry()` accounting path for split-coded entries.
- Keep all banking mutation paths behind `banking.manage`.
- Keep reconciliation completion idempotent for import-batch balance application.
- Add Alembic migration(s) for any schema additions.

## Impacted files
- `app/models/banking.py`
- `app/schemas/banking.py`
- `app/routes/banking.py`
- `app/services/ofx_import.py`
- `app/static/js/banking.js`
- new migration under `alembic/versions/`
- tests:
  - `tests/test_banking_reconciliation_matching.py`
  - `tests/test_bank_import_csv.py`
  - new focused tests such as `tests/test_bank_reconciliation_split_coding.py`
  - JS banking reconciliation UI tests

## Acceptance criteria

### Split coding
- A reconciliation user can split-code one imported bank line across multiple chart accounts.
- Split-coded lines must balance exactly to the statement amount before submit.
- Applying split coding creates a balanced journal entry and marks the bank line reconciled/coded.
- Reconciliation detail shows a readable split-coded summary afterward.

### Import balance bugfix
- Importing a statement batch does **not** immediately change `BankAccount.balance`.
- Completing reconciliation for that import batch applies the batch delta once.
- Failing or abandoning reconciliation leaves `BankAccount.balance` unchanged.
- Re-opening/retrying completion cannot double-apply the same import batch.

## Risks and mitigations
- **Risk:** Split coding introduces double-posting or unbalanced journals.
  - **Mitigation:** Validate exact summed split total before posting and add focused accounting tests.
- **Risk:** Import batch balance can be applied twice.
  - **Mitigation:** Persist one-time application state keyed by reconciliation/import batch.
- **Risk:** UI complexity makes reconciliation slower.
  - **Mitigation:** Keep one-shot coding as default and make split coding an explicit secondary path.

## Verification plan
- Targeted Python tests for:
  - split coding journal construction
  - incomplete reconciliation leaves bank balance unchanged
  - complete reconciliation applies import batch delta once
- Targeted JS tests for:
  - split coding editor render/validation
  - reconciliation detail workflow
- `git diff --check`
- Security review of:
  - account targeting
  - auth boundary
  - idempotent reconciliation completion
