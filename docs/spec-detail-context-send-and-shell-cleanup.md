# Spec: context-aware detail cancel, draft invoice send action, and shell/nav cleanup

## Requirements summary
The app currently treats document detail pages as if they only ever originate from their own list pages, but users also enter them from customer overview and other context screens. Cancel/back should return users to the calling context. At the same time, valid saved draft invoices need an obvious end-of-month send action, and the shell should be visually simplified by unifying the left navigation and shortcut area.

## Functional requirements
1. **Context-aware detail return**
   - Invoice, estimate, and credit detail screens must return to the context they were opened from.
   - If no return context is available, each detail screen can fall back to its list page.

2. **Draft invoice send action**
   - Existing draft invoices that are valid enough to send should expose a clear send action.
   - The action must reuse the existing invoice send route/state transition.

3. **Shell visual cleanup**
   - Sidebar should visually extend to the top of the app shell.
   - Shortcut/top action area should visually join the sidebar to the right.
   - Redundant topbar logo/brand should be removed.
   - Left nav should accordion by section.

## Proposed design
### A. Detail-origin tracking
- Add a small origin contract in `App`, for example:
  - `App.setDetailOrigin({ hash, label, page })`
  - `App.navigateBackToContext(fallbackHash)`
- Entry points like `InvoicesPage.open()`, `EstimatesPage.open()`, and `CreditMemosPage.open()` should accept or infer an origin before navigating to detail.
- Customer overview launches should set origin to `#/customers/detail`.

### B. Draft invoice action
- On existing invoice detail screens, when status is `draft` and required fields are already present, show a `Send` button instead of/alongside the current `Mark Sent` button.
- Reuse the existing `POST /api/invoices/{id}/send` route.
- If the business meaning is “mark as sent” rather than email dispatch, the final label/copy should make that explicit in the implementation phase.

### C. Shell/nav cleanup
- Consolidate topbar/sidebar relationship in `index.html` so the left nav visually reaches the top edge.
- Remove duplicate brand element from the shortcut bar.
- Convert static nav sections into collapsible groups while keeping the current routes intact.

## Out of scope
- Broad route redesign for all entities.
- Reworking customer overview itself beyond origin tracking.
- Full responsive shell redesign.
- Introducing a new email/send backend flow beyond the existing invoice send route.

## Verification steps
1. Open invoice detail from invoices list; cancel/back returns to invoices list.
2. Open invoice detail from customer overview; cancel/back returns to customer overview.
3. Repeat for estimate and credit note detail.
4. Open a valid saved draft invoice and confirm a send action is present.
5. Verify shell shows one unified left/top navigation surface with no duplicate logo and accordion sections working.

## File-level notes
- `app/static/js/app.js`
  - likely home for generic origin-tracking helper and accordion state.
- `app/static/js/invoices.js`
  - detail actions and send-action visibility.
- `app/static/js/estimates.js`
  - context-aware back/cancel.
- `app/static/js/credit_memos.js`
  - context-aware back/cancel.
- `app/static/js/customers.js`
  - set origin before opening related document detail.
- `index.html`
  - shell structure and redundant brand removal.
- `app/static/css/style.css`, `app/static/css/dark.css`
  - shell and accordion styling.

## Risk notes
- Navigation context state must not leak between unrelated detail screens.
- Shell cleanup needs careful testing because `index.html` and shared CSS affect every screen.
