# Plan: persist GST return confirmation before settlement/download

## Summary
Add a permanent GST return confirmation record so Box 9 and Box 13 adjustments are saved with the return, the GST box list can be confirmed as a point-in-time snapshot, and the GST101A download follows that confirmation instead of relying on transient UI state.

## Key Changes
- Add a dedicated persisted GST return record for confirmed returns, separate from GST settlement.
- Save Box 9/13 plus the confirmed GST box snapshot and return metadata when a return is confirmed.
- Update GST reports/overview/detail screens so the flow becomes: edit adjustments → refresh summary → confirm return → download GST101A.
- Keep existing GST settlement logic, but treat return confirmation as the prerequisite source of truth for future settlement actions and historical return display.

## Test Plan
- Backend tests for confirmation persistence, historical overview behavior, and confirmed-return snapshot reads.
- Update GST settlement tests to use the confirmed return flow where required.
- Frontend GST report tests for confirm/download button state and confirmed-detail behavior.
- Run targeted GST tests, full Python suite, JS tests, and `git diff --check`.

## Constraints
- Preserve existing legacy settled periods in historical views even if they predate the new confirmed-return record.
- Keep Box 9/13 persistence and confirmed box snapshots immutable once confirmed.
- No new dependencies.
