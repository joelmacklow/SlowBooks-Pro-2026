# Plan: FY dates and org/admin layered locking

## Objective
Implement accounting SaaS best-practice period controls by adding explicit financial year dates and layered closing locks: an organization-level lock managed from the companies/admin surface, plus a company-admin closing date managed in company settings. Enforcement should use the stricter of the two lock dates while keeping company-admin override behavior scoped to the company lock only.

## Current state summary
- Company settings currently support a single `closing_date` and optional `closing_date_password` in per-company settings (`app/models/settings.py:28-74`, `app/routes/settings.py:117-138`, `app/static/js/settings.js` closing-date section).
- Transaction enforcement only checks the per-company settings table and optionally honors the company password override (`app/services/closing_date.py:14-50`).
- Multi-company/admin data lives in the master DB `companies` table and is managed through the Companies routes/UI (`app/models/companies.py:10-18`, `app/routes/companies.py:14-43`, `app/static/js/companies.js:8-89`).
- RBAC already distinguishes company settings admins (`settings.manage`) from organization/company-file admins (`companies.manage`) (`app/services/auth.py:18-43`, `app/services/auth.py:45-84`).
- There is no explicit financial year date range today; only GST/localization settings exist in company settings (`app/models/settings.py:39-74`, `app/static/js/settings.js` localization/closing-date sections).

## Constraints
- Preserve current company-level closing-date password override semantics for company-admin locks.
- Do not allow a company-admin override to bypass an organization-level lock.
- Keep the org lock in the master/company-admin surface rather than leaking it into normal company settings.
- Avoid broad schema churn in the company DB; FY dates can live in existing settings key/value storage.
- Changes must work for default/current company and additional company scopes.

## Recommended implementation sketch
1. **Plan/spec + settings keys**
   - Add company-level FY settings keys, likely `financial_year_start` and `financial_year_end`, to `DEFAULT_SETTINGS` and expose them through settings APIs/UI.
   - Add org-level lock metadata to the master `companies` table, e.g. `org_lock_date` and optional note.

2. **Layered lock enforcement service**
   - Extend closing-date service to compute:
     - company admin lock date from company settings
     - org/admin lock date from the current company entry in the master DB
     - effective lock date = stricter / later of the two
   - Keep password override only for the company-admin lock and only when the blocked date falls solely under that layer.

3. **Admin surfaces**
   - Settings page: add FY start/end fields and relabel company lock section as company-admin lock.
   - Companies page/API: allow org admins to view/update org lock dates per company.

4. **Validation and UX**
   - Validate FY end is after FY start and within a sensible one-year range.
   - Show effective lock context clearly so users know whether a block comes from company admin or org admin.

5. **Regression coverage**
   - Tests for FY settings round-trip and validation.
   - Tests for layered lock enforcement:
     - company lock only
     - org lock only
     - both locks present; stricter wins
     - company password override allowed only when org lock is not the blocking layer
   - UI tests for settings/companies forms where practical.

## Impacted files
- `app/models/settings.py` — new FY default keys.
- `app/models/companies.py` — org-level lock fields.
- `app/routes/settings.py` — expose FY fields and lock metadata for company settings.
- `app/routes/companies.py` — add update path for org-level lock management.
- `app/services/closing_date.py` — layered lock resolution and enforcement.
- `app/services/company_service.py` — include org-lock fields in company payloads.
- `app/static/js/settings.js` — FY date inputs + company-admin lock copy.
- `app/static/js/companies.js` — org lock display/edit UI.
- `app/schemas/*` as needed for route contracts.
- Alembic migration for `companies` master-table fields.
- Focused tests for closing date, settings, companies UI/API.

## Acceptance criteria
- Company settings let admins save FY start and FY end dates.
- Companies/admin surface lets org admins save an org lock date per company.
- Transactions dated on or before the effective layered lock are blocked.
- Company password override still works for company-admin locks but does not bypass an org lock.
- When both locks exist, the stricter/later date is enforced.
- Default/current company and switched company scopes both resolve the correct org lock.

## Test plan
- Python tests for layered lock service behavior and route validation.
- JS tests for settings and companies admin surfaces.
- `git diff --check`, targeted pytest, targeted JS runs.

## Risks and mitigations
- **Risk:** Incorrect company-to-master lookup for non-default company scopes.  
  **Mitigation:** resolve the current DB name from the active session bind and test both default/current and named company scopes.
- **Risk:** Company-admin password override accidentally bypasses org lock.  
  **Mitigation:** explicitly branch by blocking layer and add direct regression tests.
- **Risk:** FY dates become cosmetic only.  
  **Mitigation:** at minimum persist/validate them now and expose them in settings; follow-up work can build reports/period workflows on the same fields.
- **Risk:** Companies UI grows beyond reviewable scope.  
  **Mitigation:** keep org-lock editing minimal and focused; do not redesign multi-company UX in this slice.
