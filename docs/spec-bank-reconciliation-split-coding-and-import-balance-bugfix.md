# Spec: bank reconciliation split coding + import balance bugfix

## Feature request
While reconciling a bank account in the detail view, the user needs to split one statement line across multiple chart-of-accounts targets.

## Bug
When reconciliation is incomplete or fails, imported statement transactions have already been added to the linked bank account balance. They should not affect the account balance until reconciliation completes successfully.

## Desired behavior

### Split coding
- Users can code one imported bank line to multiple accounts from reconciliation detail.
- Split lines must total the statement amount exactly.
- Submission creates one balanced accounting transaction.

### Import balance application
- Statement import should stage imported lines without mutating `BankAccount.balance`.
- Successful reconciliation completion should apply the net imported batch effect exactly once.
- Failed/incomplete reconciliation should not touch the bank account balance.

## Functional requirements

### Data model
- Support either:
  - a `BankTransactionSplit` child table, and
  - import batch application tracking on `Reconciliation` or a dedicated batch model

### API
- Add split-coding request schema and endpoint for bank transactions.
- Preserve the existing simple coding endpoint.
- Reconciliation completion must enforce one-time balance application for import-backed reconciliations.

### UI
- Reconciliation detail must expose a split-coding action.
- Split editor must show running totals and block submit when totals do not balance.
- Existing match/code actions remain available.

## Out of scope
- Automatic rule-driven split coding
- Template-driven recurring splits
- Budget-vs-actual work

## Acceptance criteria
1. Import preview/import no longer changes `BankAccount.balance`.
2. Completing reconciliation for an import batch changes `BankAccount.balance` once by the batch net amount.
3. Split-coded transactions create balanced journals with one bank-side line and multiple destination lines.
4. Split-coded transactions appear as coded/reconciled in reconciliation detail.
5. Retry/double-complete protection prevents duplicate balance application.

## Test plan
- Python:
  - import does not mutate bank balance
  - complete reconciliation applies batch delta once
  - split coding posts balanced journal lines
  - split coding rejects mismatched totals
- JS:
  - split coding modal/editor render
  - sum validation blocks invalid submit
  - successful submit calls the new split-coding endpoint
