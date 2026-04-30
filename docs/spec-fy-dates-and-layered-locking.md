# Spec: FY dates and org/admin layered locking

## Requirements summary
The app currently has only one company-level closing date stored in per-company settings. For multi-company SaaS accounting, we need explicit financial year dates and two lock layers:
1. a company-admin lock date managed in company settings; and
2. an organization/admin lock date managed from the companies/admin layer.

The effective lock must be the stricter of the two. Company-admin password override must remain available for the company-admin lock only and must never bypass an org/admin lock.

## Functional requirements
1. **Financial year settings**
   - Company settings must persist `financial_year_start` and `financial_year_end`.
   - FY dates must validate as a sensible date range.

2. **Layered locking**
   - Company settings continue to manage company-admin lock date + optional override password.
   - Companies/admin surface manages org lock date per company.
   - Effective lock date = later of company-admin lock and org lock.
   - Effective lock enforcement must work across current/default company and additional company scopes.

3. **Override semantics**
   - Company-admin password override can unlock only company-admin layer blocks.
   - If an org lock is the blocking layer, override must be rejected.

4. **UX requirements**
   - Settings page must label the company lock clearly.
   - Companies page must show/edit org lock dates.
   - Error messaging should indicate whether the blocking lock is company-admin or org-admin.

## Proposed design
### A. Company settings
- Add FY date keys to `DEFAULT_SETTINGS`.
- Settings API simply round-trips them like existing date settings.
- Settings page adds FY start/end inputs near localization/period controls.

### B. Master company metadata
- Extend `Company` with `org_lock_date` (and optional `org_lock_note` if helpful).
- Extend company list/update payloads to include org lock fields.
- Add a minimal update route for companies admin.

### C. Closing-date service
- Add helper(s) that inspect the current company database name from the active session bind, then look up the corresponding master `Company` row.
- Compute layered lock metadata:
  - company_lock_date
  - org_lock_date
  - effective_lock_date
  - blocking_layer
- `check_closing_date()` should use that metadata.

### D. Error handling
- Company lock block message should keep password-override semantics.
- Org lock block message should explicitly state that organization lock prevents override.

## Out of scope
- Full period-close workflows beyond date locks.
- Auto-rolling FY dates from year to year.
- Report filtering/reporting behavior keyed off FY dates.

## Verification steps
1. Save FY dates in settings and reload settings; values persist.
2. Set company-admin lock only; blocked transaction can be overridden with password.
3. Set org lock only; blocked transaction cannot be overridden with company password.
4. Set both locks; later date wins.
5. Switch company scope and verify correct org lock applies.

## File-level implementation notes
- `app/models/settings.py`
  - add FY keys to defaults
- `app/models/companies.py`
  - add org lock fields
- `app/routes/settings.py`
  - no special handling beyond FY persistence unless validation helper is added
- `app/routes/companies.py`
  - add update route
- `app/services/closing_date.py`
  - layered lookup/enforcement logic
- `app/static/js/settings.js`
  - FY and company-lock inputs
- `app/static/js/companies.js`
  - org-lock edit/display

## Risk notes
- The highest-risk path is cross-database lookup from company DB to master DB during enforcement.
- The second highest-risk path is accidentally over-broad override behavior; tests must pin that down.
