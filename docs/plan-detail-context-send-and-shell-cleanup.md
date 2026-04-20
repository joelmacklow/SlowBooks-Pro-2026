# Plan: context-aware detail cancel, draft invoice send action, and shell/nav cleanup

## Objective
Improve navigation predictability and UI clarity by (1) making detail-page cancel/back actions return to the calling context, (2) exposing an easy send action for valid draft invoices, and (3) cleaning up the app shell so the left menu and shortcut area read as one coherent navigation surface.

## Current state summary
- Document detail screens currently hard-code list-page back navigation instead of returning to where they were opened from:
  - invoices use `App.navigate('#/invoices')` in the detail header and cancel action (`app/static/js/invoices.js`, `renderDetailScreen()`)
  - estimates use `App.navigate('#/estimates')` in their detail screen (`app/static/js/estimates.js`)
  - credit memos use `App.navigate('#/credit-memos')` in their detail screen (`app/static/js/credit_memos.js`)
  - customer overview launches those detail screens from a different context (`app/static/js/customers.js`, `renderDetailScreen()` buttons), so cancel/back currently drops users out of customer context.
- Existing tests already encode the current fixed-back behavior, which makes this slice a good candidate for a focused regression update rather than broad refactor (`tests/js_document_detail_alignment.test.js`).
- Draft invoices already have a backend send transition:
  - route exists at `POST /api/invoices/{invoice_id}/send` and only allows draft invoices (`app/routes/invoices.py:345+`)
  - frontend currently exposes `Mark Sent` on existing draft invoices (`app/static/js/invoices.js:252-255`, `markSent()` at `app/static/js/invoices.js:467+`)
- The app shell is still split between a top shortcut bar and a separate sidebar:
  - top shortcut/menu area and duplicate brand/logo live in `index.html` under `#topbar`
  - left nav/logo live separately in `index.html` under `#sidebar`
  - shell styling is mostly in `app/static/css/style.css` and `app/static/css/dark.css`
- The current left nav is visually sectioned with static `li.nav-section` labels, but it does not accordion/collapse (`index.html`, `app/static/css/style.css`).

## Constraints
- Preserve current document-detail route structure (`#/invoices/detail`, `#/estimates/detail`, `#/credit-memos/detail`) rather than introducing brand-new routes.
- Keep context-aware return behavior generic and reusable across detail pages; avoid page-specific ad hoc hacks.
- Reuse the existing invoice send route/state transition instead of creating a second “send” backend path.
- Visual cleanup should reduce duplication, not introduce a second navigation system.
- Keep the shell change reviewable; this slice should not redesign every page layout.

## Recommended implementation sketch
1. **Context-aware detail navigation state**
   - Add a lightweight detail-origin tracker in `App` (for example current route + hash + optional page-specific payload) so callers can set “return to” before opening a detail screen.
   - Update invoice/estimate/credit/customer-linked entry points to register origin context before navigating to detail.
   - Replace hard-coded detail cancel/back buttons with an `App.navigateBackToContext(fallbackHash)` helper.

2. **Draft invoice send action**
   - Replace or supplement `Mark Sent` with a clearer draft-only `Send` action on valid existing draft invoices.
   - Define “valid” as the current saved-draft state having the minimum sendable fields already present (customer, lines, due date/date) rather than inventing new backend validation in this slice.
   - Reuse the existing send transition route; if email sending is not intended, use naming/copy that matches the actual behavior.

3. **Shell / visual cleanup**
   - Move the left menu flush to the top of the page by visually joining `#sidebar` with the top shortcut area.
   - Remove the redundant logo/brand from the shortcut bar once the shell is unified.
   - Introduce accordion behavior for nav sections (Customers & Sales, Vendors & Payables, Banking, etc.) for clarity.

4. **Regression coverage**
   - Update/add JS tests for context-aware cancel/back from list pages and customer overview.
   - Add JS coverage for the draft-invoice send action visibility rules.
   - Add shell/nav structure tests where practical to lock the unified sidebar/topbar and accordion behavior.

## Impacted files
- `app/static/js/app.js` — route helpers, detail-origin state, shell/nav accordion behavior.
- `app/static/js/invoices.js` — invoice detail cancel/back and draft send action.
- `app/static/js/estimates.js` — estimate detail cancel/back.
- `app/static/js/credit_memos.js` — credit detail cancel/back.
- `app/static/js/customers.js` — customer overview launches should set return context.
- `index.html` — sidebar/topbar/shortcut structure.
- `app/static/css/style.css` and `app/static/css/dark.css` — unified shell styling and accordion states.
- `tests/js_document_detail_alignment.test.js` — update for context-aware back behavior.
- New focused shell/nav JS test(s) as needed.

## Acceptance criteria
- Opening invoice/estimate/credit detail from a list returns to that list on cancel/back.
- Opening invoice/estimate/credit detail from customer overview returns to customer overview on cancel/back.
- Existing saved draft invoices with required fields show a clear send action.
- The draft send action reuses the existing invoice send route/state transition.
- Sidebar visually reaches the top, shortcut area visually joins it, and the redundant topbar logo is removed.
- Left navigation sections accordion for clarity without breaking route access.

## Test plan
- JS tests for detail-origin tracking from invoices list, estimates list, credit memo list, and customer overview.
- JS test for draft-invoice send action visibility and handler target.
- JS test(s) for unified shell/nav structure and accordion toggling.
- `git diff --check` on artifacts.

## Risks and mitigations
- **Risk:** Detail-return state becomes stale or survives too long.  
  **Mitigation:** keep the origin tracker narrow and refresh it only when entering detail pages.
- **Risk:** “Send” wording mismatches actual invoice behavior.  
  **Mitigation:** explicitly document whether the action means status transition, email, or both before implementation.
- **Risk:** Shell cleanup causes broad visual regressions.  
  **Mitigation:** keep the HTML/CSS diff localized to `index.html` and shared shell styles, with targeted visual structure tests.
- **Risk:** Accordion nav hurts discoverability.  
  **Mitigation:** default key sections open and preserve active-section visibility when route changes.
