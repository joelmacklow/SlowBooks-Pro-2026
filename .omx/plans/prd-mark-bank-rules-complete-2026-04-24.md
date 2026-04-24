# PRD: mark Bank Rules MVP complete

## Objective
Refresh the canonical NZ backlog so it no longer presents Bank Rules MVP as the next pending implementation slice now that the feature exists on `main`.

## Constraints
- Documentation-only status cleanup; do not change runtime code.
- Preserve the active next-slices ordering while promoting the next genuinely pending slice.
- Ground the status update in existing implementation evidence: `app/models/banking.py`, `app/services/bank_rules.py`, `app/routes/banking.py`, `app/services/ofx_import.py`, `app/static/js/banking.js`, and bank-rule tests.

## Implementation sketch
- Update `docs/localization_summary.md` Remaining Todo narrative to mention Bank Rules MVP as completed shared banking infrastructure.
- Remove Bank Rules MVP from active pending priorities.
- Promote Budget vs Actual to Priority 1 and renumber subsequent pending slices.
- Add/adjust a numbered backlog note so future sessions know bank rules are complete and should be reused.

## Impacted files
- `.omx/plans/prd-mark-bank-rules-complete-2026-04-24.md`
- `.omx/plans/test-spec-mark-bank-rules-complete-2026-04-24.md`
- `docs/localization_summary.md`

## Test plan
- Manual review of the active next-slices list for accurate ordering.
- `git diff --check`.

## Risk notes
- Low risk: docs-only change.
- Main risk is stale backlog wording causing duplicate implementation work; this update removes that ambiguity.
