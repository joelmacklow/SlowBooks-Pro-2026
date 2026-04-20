# Spec: Search navigation and serializer bugfix

## User-visible bugs
1. Invoice search works and opens invoice detail.
2. Estimate search shows a raw `#id` label and opens the estimate list instead of the detail screen.
3. Customer search returns a customer but clicking it does not open a meaningful detail page.
4. Credit note search returns nothing.
5. API logs show serializer warnings for nested invoice credit applications and credit memo applications.

## Desired behavior
- Search results for invoices, estimates, customers, and credit notes should all have meaningful labels and open the correct detail view.

## Functional requirements

### Unified search
- Return `credit_memos` when `memo_number` matches.
- Return explicit `display` labels for invoices, estimates, and credit notes.

### Search navigation
- Estimate result click must open estimate detail.
- Credit note result click must open credit memo detail.
- Customer result click must open a dedicated customer detail route.

### Customer detail
- Show customer summary:
  - contact details
  - billing/shipping information
  - current balance
- Show history tables for:
  - invoices
  - estimates
  - credit notes

### Serializer cleanup
- `InvoiceResponse.applied_credits` must be populated with `InvoiceCreditApplicationResponse` objects.
- `CreditMemoResponse.applications` must be populated with `CreditApplicationResponse` objects.

## Out of scope
- Vendor detail pages
- Search ranking overhaul
- New aggregate backend endpoint for customer detail

## Test plan
- Python:
  - unified search returns estimate/customer/credit-note labels and ids
  - invoice/credit memo helpers build typed nested response models
- JS:
  - search HTML includes the correct estimate/customer/credit-note navigation targets
  - customer detail route renders document history sections
