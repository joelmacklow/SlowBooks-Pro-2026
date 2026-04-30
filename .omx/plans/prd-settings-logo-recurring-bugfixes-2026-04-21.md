# PRD — Settings logo upload + recurring invoice schedule bugfixes

## Date
2026-04-21

## Objective
Fix three related bugs:
1. Settings page logo upload UI advertises SVG support even though the backend rejects it.
2. Logo upload storage fails when the repo-local static uploads directory is not writable.
3. Recurring invoice editor does not re-evaluate schedule/due-date previews when terms, frequency, or start date change, and recurring updates do not persist start-date/customer schedule edits correctly.

## Current-state evidence
- Settings UI currently says `PNG, JPG, or SVG` and uses `accept="image/*"` in `app/static/js/settings.js:111-113`.
- Backend logo upload only allows `image/png`, `image/jpeg`, and `image/gif` in `app/routes/uploads.py:21-49` and returns an error mentioning only PNG/JPEG/GIF.
- Uploads currently write directly to `app/static/uploads` via `UPLOAD_DIR = Path(...)/app/static/uploads` in `app/routes/uploads.py:21`, which can be unwritable in container/runtime setups.
- The app serves `/static` from `app/main.py` via `StaticFiles(directory=str(static_dir))` and does not currently provide a separate writable uploads mount.
- Recurring editor shows a disabled `Next Due` field sourced from persisted `rec.next_due` only in `app/static/js/recurring.js:180-184`; it does not recalculate when the form changes.
- Recurring update payload includes `customer_id` and `start_date` from the form in JS (`app/static/js/recurring.js:350-358`), but the backend `RecurringUpdate` schema does not accept those fields (`app/schemas/recurring.py:31-38`), so edits are silently ignored.
- Backend update route in `app/routes/recurring.py:69-98` does not recalculate `next_due` when schedule fields change.

## Problem
- Users are told SVG is supported when it is not.
- Logo uploads can fail due to writable-storage assumptions tied to the code directory.
- The recurring invoice editor misleads users by showing stale schedule information, especially for rules like `Due 1st of next month`, and backend updates do not fully honor schedule edits.

## Requirements
1. Settings UI must advertise only the image types actually accepted by the backend.
2. Logo upload storage must use a writable managed directory and still be publicly served at a stable `/static/uploads/...` URL.
3. Storage failures during write must produce a clear `Upload storage is not writable` error.
4. Recurring editor must distinguish the next invoice generation date from the invoice due-date preview.
5. Changing recurring `terms`, `frequency`, or `start_date` in the editor must immediately re-evaluate the relevant preview fields.
6. Backend recurring updates must accept and persist `customer_id` and `start_date` edits, and must recalculate `next_due` when schedule-affecting fields change.

## Recommended direction
- Keep SVG unsupported for now; align the UI to the backend instead of widening upload support.
- Serve logo uploads from a dedicated writable uploads directory mounted separately from the repo static tree.
- Add recurring preview helpers in JS:
  - `Next Invoice Date`
  - `Invoice Due Date`
- Recalculate previews client-side using the same frequency + payment-terms logic shape as the backend.
- Recalculate `next_due` server-side when recurring schedule inputs change.

## Acceptance criteria
- Settings page no longer advertises SVG support.
- Logo upload succeeds when the writable uploads directory is available even if `app/static/uploads` is not writable.
- Logo upload returns a clean 500 with `not writable` messaging on write failures.
- Recurring editor preview updates when changing `terms`, `frequency`, or `start_date`.
- Recurring update persists edited `start_date` and `customer_id`.
- `next_due` is re-evaluated after schedule edits rather than left stale.

## Risks and mitigations
- **Risk:** changing uploads storage breaks existing static URL assumptions.  
  **Mitigation:** keep the public path `/static/uploads/...` stable via a dedicated mount.
- **Risk:** recurring next-due recalculation could surprise existing schedules.  
  **Mitigation:** only recalculate when schedule-affecting fields actually change; preserve existing values otherwise.
- **Risk:** front/back preview logic diverges.  
  **Mitigation:** keep both implementations simple and cover them with targeted tests.
