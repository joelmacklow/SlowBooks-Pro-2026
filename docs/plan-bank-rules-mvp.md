# Plan: Bank Rules MVP

## Objective
Add a safe NZ-first Bank Rules MVP that gives imported bank lines deterministic payee/pattern-based categorization without auto-posting accounting entries behind the operator's back.

## Why this slice is next
- `docs/localization_summary.md` lists **Bank rules MVP** as **Priority 1** in the active next slices and describes it as deterministic payee/pattern categorization built on the current import/reconciliation foundations.
- The current banking flow already supports statement import, invoice/bill matching, and manual coding, but it has **no persistent rule model** and **no rule evaluation path** during import or reconciliation.

## Current state summary
- Imported statement lines land as `BankTransaction` rows with `match_status="unmatched"` and no rule metadata: `app/services/ofx_import.py`
- Matching today is document-focused only (`invoice` / `bill`) via amount/reference/payee heuristics: `app/services/reconciliation_matching.py`
- Manual coding already exists and posts journals safely through `/api/banking/transactions/{txn_id}/code`: `app/routes/banking.py`
- Banking UI already has reconciliation and one-off coding surfaces but no rules management surface: `app/static/js/banking.js`

## Recommended MVP shape
Use **persistent deterministic suggestion rules**, not silent auto-posting.

### Recommended behavior
1. Add persistent **BankRule** records with:
   - `name`
   - `priority`
   - `is_active`
   - `bank_account_id` nullable for "all bank accounts"
   - `direction` (`inflow`, `outflow`, `any`)
   - exact match criteria fields for deterministic matching:
     - `payee_contains`
     - `description_contains`
     - `reference_contains`
     - `code_equals`
   - `target_account_id`
   - optional `memo_template` / `default_description`
2. Evaluate rules **in priority order** for imported unmatched bank lines after import and when rendering reconciliation suggestions.
3. Stamp the best matching rule onto the bank line as a **suggested category**, but do **not** create the journal automatically.
4. In reconciliation UI, show the matched rule and add a one-click **Apply Rule** action that reuses the existing coding flow.
5. Keep document matching (`invoice` / `bill`) higher-trust and separate from rule-based coding.

### Why this option
- Reuses the existing import and reconciliation flow instead of creating a second banking pipeline.
- Keeps accounting mutation explicit and operator-approved.
- Fits the repo's current auth/audit model because rule CRUD and rule application stay behind `banking.manage`.
- Keeps rule evaluation deterministic and explainable.

### Explicit non-goals for MVP
- No machine-learning or fuzzy categorization engine.
- No automatic journal posting at import time.
- No split transactions.
- No vendor/customer creation from rules.
- No budget integration yet.

## Constraints
- Preserve current document matching behavior in `app/services/reconciliation_matching.py`.
- Stay behind `banking.manage` / `banking.view` permissions already used by banking routes.
- Keep rules deterministic and priority-ordered; no hidden scoring once a rule matches.
- Any schema changes must use Alembic migrations under `alembic/versions`.
- Reuse existing `code_bank_transaction` journaling logic rather than creating a second posting path.

## Impacted files
- `app/models/banking.py`
- `app/schemas/banking.py`
- `app/routes/banking.py`
- `app/services/ofx_import.py`
- `app/services/reconciliation_matching.py`
- `app/static/js/banking.js`
- `alembic/versions/<new_bank_rules_migration>.py`
- `tests/test_banking_reconciliation_matching.py`
- new focused tests such as:
  - `tests/test_bank_rules.py`
  - `tests/js_banking_rules_ui.test.js`

## Implementation steps
1. **Schema + model**
   - Add `BankRule` model and relationships in `app/models/banking.py`.
   - Add suggested-rule fields on `BankTransaction` if needed (`suggested_rule_id`, `suggested_account_id`, `rule_match_reason`).
   - Create Alembic migration.
2. **Rule evaluation service**
   - Add a focused service module (recommended: `app/services/bank_rules.py`) for:
     - normalizing candidate text
     - deterministic rule matching
     - priority ordering
     - explanation strings for UI/tests
3. **Import integration**
   - In `app/services/ofx_import.py`, evaluate active rules after dedup/import row construction and persist suggested rule metadata without posting journals.
4. **Route layer**
   - Add CRUD routes for bank rules under `app/routes/banking.py`.
   - Add an `apply-rule` action that converts a suggested rule into the existing coding flow.
   - Keep `/code` as the single journal-posting implementation.
5. **UI**
   - Add a Banking settings/rules surface in `app/static/js/banking.js`.
   - Show matched-rule badges and one-click apply actions in reconciliation view.
6. **Tests**
   - Rule ordering / determinism
   - account scoping
   - inflow/outflow filtering
   - import dedup does not double-apply
   - apply-rule reuses coding safely
   - UI render/interaction coverage

## Acceptance criteria
- Operators can create, edit, disable, and delete bank rules from the banking surface.
- Imported bank lines can show a deterministic suggested category from the highest-priority matching rule.
- Rule application does not auto-post until an operator explicitly applies the suggestion.
- Applying a rule produces the same accounting result as manual coding through the existing coding path.
- Rules can be scoped by direction and optionally by bank account.
- Ties are resolved only by explicit priority, not unstable query ordering.
- Existing invoice/bill matching tests continue to pass.

## Risks and mitigations
- **Risk:** Rule suggestions overshadow invoice/bill matching.
  - **Mitigation:** Keep rule suggestions visually separate and do not replace existing document-match suggestions.
- **Risk:** Auto-posting could misclassify transactions.
  - **Mitigation:** MVP stops at suggested categorization; posting still requires explicit apply.
- **Risk:** Rule ordering becomes unstable.
  - **Mitigation:** Use explicit integer priority plus stable secondary ordering in code/tests.
- **Risk:** Multi-company or bank-account scoping leaks rules too broadly.
  - **Mitigation:** Support nullable global rules plus explicit bank-account scope and test both.

## Verification plan
- Targeted Python tests for rule matching, import integration, and apply-rule behavior.
- Targeted JS tests for rule-management and reconciliation suggestion UI.
- `git diff --check`
- Security pass focused on:
  - auth boundaries for rule CRUD/apply
  - safe account targeting
  - no hidden auto-post behavior

## Suggested execution lane
This is a **standard multi-file feature slice** that should be executed on a dedicated branch with:
- one backend lane for model/migration/service/routes
- one frontend lane for banking UI
- one verification lane for Python + JS regression coverage
