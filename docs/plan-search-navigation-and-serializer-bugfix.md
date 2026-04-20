# Plan: Search navigation and serializer bugfix

## Objective
Fix the broken global-search navigation paths for estimates, customers, and credit notes, and remove the Pydantic serializer warnings caused by response models being populated with plain dictionaries instead of typed response objects.

## Scope
- Global search result labels and click targets
- Customer detail navigation and detail screen
- Credit note search support
- Invoice / credit memo response serialization warnings

## Known problems
- Estimate search results show fallback `#<id>` labels and do not open the estimate detail screen.
- Customer search results route to the generic customer list instead of a detail view.
- Credit note search is not implemented in the unified search endpoint.
- Invoice and credit memo response builders populate nested response lists with raw dicts, which triggers Pydantic serializer warnings.

## Impacted files
- `app/routes/search.py`
- `app/static/js/app.js`
- `app/static/js/customers.js`
- `app/static/js/estimates.js`
- `app/static/js/credit_memos.js`
- `app/routes/invoices.py`
- `app/routes/credit_memos.py`
- `app/schemas/invoices.py`
- `app/schemas/credit_memos.py`
- targeted regression tests

## Implementation sketch
1. Extend unified search results to include explicit display labels and credit memo results.
2. Update global-search click handlers:
   - estimates -> estimate detail loader
   - credit memos -> credit memo detail loader
   - customers -> customer detail route
3. Add a customer detail screen that pulls:
   - customer summary/details
   - invoice history
   - estimate history
   - credit memo history
   - current account balance
4. Replace raw dict nested payloads in invoice and credit memo response builders with typed nested response models.
5. Add backend and frontend regression tests.

## Acceptance criteria
- Searching an estimate number shows the estimate number label and opens estimate detail.
- Searching a customer name opens a customer detail page with customer details and document history.
- Searching a credit note number returns the credit note and opens credit memo detail.
- Invoice and credit memo API responses no longer emit the reported Pydantic serializer warnings for nested application objects.

## Verification
- Targeted Python tests for search endpoint and serializer builders.
- Targeted JS tests for global search navigation and customer detail behavior.
- `git diff --check`

## Risks
- Customer detail page could make too many API calls if the UI pulls unrelated data.
- Search result click handlers depend on page loaders having valid state before routing.
- Serializer changes must preserve current response shapes.
