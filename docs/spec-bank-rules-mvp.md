# Spec: Bank Rules MVP

## Problem
SlowBooks NZ can import bank statements, suggest invoice/bill matches, and manually code bank lines, but it cannot persist deterministic categorization rules for recurring statement descriptions or payees.

## Goal
Introduce a first Bank Rules MVP that helps operators categorize imported bank lines faster while preserving explicit approval before accounting entries are posted.

## User stories
- As a bookkeeper, I can save a rule for recurring statement text so I do not manually choose the same account every import.
- As a reviewer, I can see *why* a rule matched a bank line before applying it.
- As an admin, I can disable or reprioritize a rule without editing imported transactions directly.

## In scope
- Persistent bank rule records
- Deterministic priority-ordered rule matching
- Suggested categorization on imported bank lines
- One-click apply of a matched rule through the existing coding path
- Banking UI for managing rules and applying suggestions
- Regression tests for deterministic behavior and safe posting

## Out of scope
- Auto-posting coded journals during import
- Split rules or percentage allocations
- Fuzzy/ML matching
- Rule-generated counterparties/items
- Budget-vs-actual follow-up work

## Functional requirements

### Data model
- The system stores bank rules with:
  - name
  - priority
  - active flag
  - optional bank-account scope
  - direction scope (`inflow`, `outflow`, `any`)
  - deterministic text criteria
  - target account
  - optional default description text
- The system stores enough metadata on `BankTransaction` to display the winning rule suggestion and explanation without immediately posting.

### Matching
- Rule evaluation is deterministic and stable.
- Rules are checked in ascending priority order.
- The first active matching rule wins.
- Rules only evaluate for unmatched / uncoded imported bank lines.
- Direction scope must be respected.
- Bank-account-scoped rules only apply to matching bank accounts.

### Apply flow
- An operator can apply a suggested rule from the banking/reconciliation UI.
- Applying a rule must reuse the existing coding/journal path, not a duplicate implementation.
- Applying a rule updates the bank line so the UI shows it as coded/reconciled consistently with existing manual coding.

### UI
- Banking UI exposes:
  - list rules
  - create/edit/delete/disable rules
  - priority controls
  - rule suggestion badges/explanations on bank lines
  - one-click apply action

## Acceptance criteria
1. Creating a rule for an outflow payee/code combination causes future matching imported lines to show that suggested account.
2. When multiple rules match the same line, the lower priority number wins every time.
3. Document-match suggestions still appear for invoice/bill candidates and are not replaced by rule suggestions.
4. Applying a rule posts the same journal shape as manual coding for the same account.
5. Disabling a rule prevents it from appearing on newly imported lines.
6. Rule CRUD and apply actions require `banking.manage`.
7. View-only users can see matched rule context but cannot mutate rules or apply them.

## Test plan

### Python
- `tests/test_bank_rules.py`
  - exact priority ordering
  - direction filtering
  - bank-account scoping
  - inactive rules skipped
  - explanation text present
- extend `tests/test_banking_reconciliation_matching.py`
  - rule suggestions coexist with invoice/bill matching
  - apply-rule reuses coding path
- extend statement import tests
  - imported rows receive suggested-rule metadata
  - duplicate imports do not duplicate rule application state

### JS
- `tests/js_banking_rules_ui.test.js`
  - render rule list/form
  - create/edit/delete interactions
  - suggestion badge rendering
  - apply-rule button wiring

## Risks
- Incorrect categorization could create wrong journals if apply flow bypasses review.
- Overly broad text matching could produce noisy suggestions.
- Migration complexity is moderate because banking models already support several matching states.

## Security and operational checks
- Enforce permission checks on rule CRUD and apply endpoints.
- Validate target accounts are active and not the same linked bank account when applying.
- Preserve auditability by relying on existing audited DB writes and explicit operator actions.

## Suggested slice size
One implementation slice is reasonable if limited to:
- deterministic persistent rules
- import-time suggestion metadata
- explicit apply flow
- no auto-posting and no split transactions
