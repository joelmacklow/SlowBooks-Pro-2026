# Spec: closing-date password prompt and reconciliation cancel modal

## Requirements summary
Closing-date password override exists in backend logic but has no UI prompt/retry path, so users only see an error. Reconciliation cancel still uses the browser confirm dialog instead of the app modal system.

## Functional requirements
- Detect company-admin closing-date lock responses and prompt for override password in-app.
- Retry the blocked request once with the provided override password.
- Do not prompt for org-lock failures.
- Replace reconciliation cancel browser confirm with app modal confirmation.

## File-level notes
- `app/services/closing_date.py` — read request-scoped override password when explicit password arg is absent.
- `app/database.py` or similar request dependency path — capture override header into request-scoped state.
- `app/static/js/api.js` — detect lock errors, prompt, retry.
- `app/static/js/app.js` or `utils.js` — reusable modal helpers.
- `app/static/js/banking.js` — modal-based reconciliation cancel confirmation.
- focused JS tests for API retry + banking cancel dialog.
