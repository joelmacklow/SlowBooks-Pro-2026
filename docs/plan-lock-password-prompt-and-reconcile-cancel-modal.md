# Plan: closing-date password prompt and reconciliation cancel modal

## Objective
Fix two UI/UX gaps: (1) when a company-admin closing-date lock blocks a change, the app should prompt in-app for the override password and retry; (2) reconciliation cancel should use the app modal instead of the browser `confirm()` dialog.

## Current state summary
- `check_closing_date()` supports a password argument, but most routes call it without a password and there is no browser-to-server transport for override password on ordinary API calls (`app/services/closing_date.py`).
- API failures currently bubble back as plain thrown `Error(detail)` strings from `API.raw()` with no special lock-handling flow (`app/static/js/api.js`).
- The app already has modal primitives via `openModal()` / `closeModal()` (`app/static/js/utils.js`), so password/cancel dialogs can stay in-app.
- Reconciliation cancel still uses browser `confirm()` for imported reconciliations (`app/static/js/banking.js:407-416`).

## Constraints
- Preserve org-lock semantics: company override prompt must not bypass org-admin locks.
- Keep closing-date override transport centralized rather than adding per-route UI hacks.
- Keep the reconciliation cancel backend path unchanged; this is a dialog/UI refinement.

## Implementation sketch
1. Add a request-scoped closing-date password transport (e.g. request header) that `check_closing_date()` can read without changing every route signature.
2. Extend `API.raw()` to detect company-admin lock responses, prompt for override password in-app, then retry once with the override header.
3. Add an `App`-level password prompt helper/modal.
4. Replace reconciliation cancel `confirm()` with an in-app modal confirmation helper.
5. Add focused JS regressions for both flows and minimal backend coverage for header/context propagation if needed.

## Acceptance criteria
- Company-admin lock errors trigger an in-app password prompt.
- Entering the correct password retries the original request and succeeds.
- Org-lock errors do not offer a bypass prompt.
- Reconciliation cancel uses an in-app modal instead of browser `confirm()`.
