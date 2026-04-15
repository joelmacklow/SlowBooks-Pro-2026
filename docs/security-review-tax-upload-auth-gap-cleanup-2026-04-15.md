# Security Review — Tax And Upload Auth Gap Cleanup (2026-04-15)

## Scope Reviewed
- `app/routes/tax.py`
- `app/routes/uploads.py`
- `tests/test_tax_upload_auth_gap_cleanup.py`
- `tests/test_schedule_c_disabled.py`

## Review Focus
- Whether the residual public legacy tax surface is now fully retired on the NZ branch
- Whether company-logo uploads now require the existing settings permission boundary
- Whether the slice changes only the auth/retirement posture without widening file or tax behavior

## Findings
1. **Legacy tax mappings are now retired with the rest of the NZ-disabled tax surface**
   - `/api/tax/mappings` now returns the same NZ-specific `410 Gone` disabled response as the Schedule C endpoints.
   - This removes the last active-looking public API under the retired US tax surface.

2. **Company logo uploads now require `settings.manage`**
   - `/api/uploads/logo` now reuses the existing settings/admin permission boundary rather than remaining publicly callable.
   - Authorized uploads still preserve existing MIME validation and `company_logo_path` update behavior.

3. **No new sensitive data exposure or storage path broadening was introduced**
   - The upload flow still writes only the fixed company-logo filename into the existing uploads directory.
   - The tax route remains retired rather than repurposed, which avoids introducing interim NZ income-tax semantics.

## Residual Risks
- The broader uploads surface is still single-purpose today; future general uploads should be threat-modeled separately before adding new file types or destinations.
- NZ income-tax replacement is still a product gap; this slice secures retirement posture rather than implementing replacement functionality.

## Conclusion
- No new CRITICAL/HIGH issues identified in this slice.
- Residual risk is **LOW**, mostly limited to future expansion of uploads or future NZ income-tax product work.
