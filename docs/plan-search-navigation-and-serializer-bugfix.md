# Plan: Search navigation and serializer bugfix

## Objective
Fix the broken global-search navigation paths for estimates, customers, and credit notes, and remove the Pydantic serializer warnings caused by nested invoice/credit memo response payloads being built from plain dictionaries.

## Current failures
- Searching an estimate number returns a fallback `#<id>` label and only routes to the estimate list.
- Searching a customer name returns a result, but clicking it does not open a useful detail view.
- Credit note search is missing entirely.
- Invoice and credit memo APIs log serializer warnings for nested application objects.

## Constraints
- Keep the fix scoped; do not redesign search ranking.
- Reuse existing customer, invoice, estimate, and credit-note APIs where practical.
- Preserve current response shapes while switching nested payloads to typed response models.

## Impacted files
- `app/routes/search.py`
- `app/routes/invoices.py`
- `app/routes/credit_memos.py`
- `app/static/js/app.js`
- `app/static/js/customers.js`
- targeted regression tests

## Implementation sketch
1. Extend unified search to return explicit display labels and credit memo results.
2. Update global-search click handlers:
   - estimates -> estimate detail loader
   - credit notes -> credit memo detail loader
   - customers -> customer detail route
3. Add a customer detail screen that shows:
   - customer summary/details
   - invoice history
   - estimate history
   - credit note history
   - current balance
4. Replace raw dict nested payloads in invoice and credit memo response builders with typed nested response objects.
5. Add backend and frontend regression tests.

## Acceptance criteria
- Searching an estimate number shows the estimate number label and opens estimate detail.
- Searching a customer name opens a customer detail page with contact details and document history.
- Searching a credit note number returns the credit note and opens credit memo detail.
- Invoice and credit memo API responses no longer emit the reported nested serializer warnings.

## Verification
- Targeted Python tests for unified search and serializer builders.
- Targeted JS tests for search-result navigation and customer detail rendering.
- `git diff --check`

## Risks
- Customer detail may become chatty because it composes data from multiple existing endpoints.
- Search click handlers depend on loading detail state before routing.
