# Spec: Search navigation and serializer bugfix

## User-facing bugs
1. Searching an invoice number works and opens invoice detail.
2. Searching an estimate number returns a fallback label like `#2` and clicking it does nothing useful.
3. Searching a customer name returns the customer, but clicking it does not open a detail view.
4. Credit note search returns nothing.
5. API logs show serializer warnings for nested invoice credit applications and credit memo applications.

## Desired behavior
- Estimates, customers, invoices, and credit notes should all behave consistently in global search:
  - search result label is meaningful
  - clicking the result opens the correct detail view

## Functional requirements

### Search endpoint
- Must return `credit_memos` results when `memo_number` matches the query.
- Should include a stable display label for estimates and credit memos, rather than relying on JS fallbacks.

### Search navigation
- Estimate search click should call the estimate detail loader before routing.
- Credit memo search click should call the credit memo detail loader before routing.
- Customer search click should open a dedicated customer detail route.

### Customer detail page
- Shows customer summary:
  - name/company/contact info
  - billing/shipping details
  - current account balance
- Shows recent or full history tables for:
  - invoices
  - estimates
  - credit notes
- Reuses existing APIs where practical.

### Serialization warnings
- Invoice response nested `applied_credits` must be constructed as `InvoiceCreditApplicationResponse` objects.
- Credit memo response nested `applications` must be constructed as `CreditApplicationResponse` objects.
- Response shape must remain unchanged for clients.

## Test plan
- Python:
  - unified search returns estimate/customer/credit memo labels and IDs
  - invoice/credit memo response helpers return typed nested objects
- JS:
  - search click opens estimate detail
  - search click opens credit memo detail
  - search click opens customer detail
  - customer detail page renders related document sections

## Out of scope
- Vendor detail pages
- New customer backend aggregate endpoint
- Search ranking overhaul
