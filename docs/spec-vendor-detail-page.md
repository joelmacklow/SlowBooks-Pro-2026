# Spec: vendor detail page aligned to customer detail page

## Requirements summary
Vendors need a detail page similar to customers. It should show vendor details, preferred items, outstanding bills, payment history, and a credit-balance view based on existing AP data.

## Functional requirements
- Add a vendor detail route/screen.
- Vendor detail must show:
  - core vendor details
  - preferred-supplier items
  - outstanding bills / bill history
  - vendor balance
  - vendor credit balance
- Preferred items come from current `items.vendor_id`.
- Credit balance should be derived from current AP artifacts unless a later slice introduces a dedicated vendor-credit model.

## Proposed design
### A. Route/state
- Add `#/vendors/detail` to `App.routes`.
- Add `VendorsPage.view(id)` that loads vendor detail context and navigates to the detail route.

### B. Data sources
- `/vendors/{id}` for vendor core data.
- `/items?active_only=true&vendor_id={id}` for preferred items.
- `/bills?vendor_id={id}` for bill history/outstanding bills.
- `/bill-payments?vendor_id={id}` for payment history.
- Credit balance = unallocated portion of bill payments unless later replaced by a dedicated model.

### C. Layout
- Match customer detail page structure closely for consistency.
- Include summary cards, details section, preferred items section, bills section, payment section.

## Out of scope
- New vendor-credit database model.
- New AP workflow behavior beyond display/detail navigation.
- Reworking vendor list/edit flows outside adding detail entry.

## Verification steps
1. Open vendor detail from vendor list.
2. Confirm preferred items show only items where `vendor_id` matches.
3. Confirm outstanding bills/history render correctly.
4. Confirm vendor credit balance shows from unallocated bill payments.

## Risk notes
- If current AP data is insufficient for a trustworthy “credit balance” label, implementation should label it explicitly as “Unallocated Bill Payments” rather than implying a fuller credit subsystem.
