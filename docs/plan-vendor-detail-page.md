# Plan: vendor detail page aligned to customer detail page

## Objective
Add a vendor detail page similar to the customer detail page, showing vendor details, preferred-supplier items, outstanding bill history, payment history, and a vendor credit balance view grounded in current AP data.

## Current state summary
- Vendors currently only have a list page + modal edit form; there is no vendor detail screen (`app/static/js/vendors.js`).
- Customer detail already provides the reference pattern: header, summary cards, details section, and linked document history (`app/static/js/customers.js`).
- Items already track a preferred supplier via `item.vendor_id`, and the existing items API can filter by `vendor_id` (`app/models/items.py:25-45`, `app/routes/items.py:12-30`).
- Bills already support vendor filtering and expose status/balance data (`app/routes/bills.py:105-119`, `app/models/bills.py`).
- Bill payments already support vendor filtering through `/bill-payments?vendor_id=...` (`app/routes/bill_payments.py:19-34`).
- There is no first-class vendor credit memo object today. The closest current “vendor credit balance” surface is unallocated bill payments, which the GST return service already computes as `payment.amount - allocated` (`app/services/gst_return.py:222-230`, `app/services/gst_return.py:326`).
- Vendors already have a `balance` field in the model/response, so the detail page can surface current net AP balance immediately (`app/models/contacts.py`, `app/schemas/contacts.py`).

## Constraints
- Reuse the customer-detail UI pattern instead of inventing a separate vendor-detail architecture.
- Do not invent a new vendor-credit subsystem in this slice; derive “credit balance” from current bill-payment/allocation data unless a later slice introduces first-class vendor credits.
- Keep list/edit flows working; vendor detail should be additive.
- Prefer current APIs and small route additions over a large aggregate backend redesign.

## Recommended implementation sketch
1. **Vendor detail state + route**
   - Add `/vendors/detail` route entry in `App.routes`.
   - Add `VendorsPage.view(id)` and `VendorsPage.renderDetailScreen()` mirroring customer detail behavior.

2. **Data loading**
   - Load vendor core record via `/vendors/{id}`.
   - Load preferred items via `/items?active_only=true&vendor_id={id}`.
   - Load bills via `/bills?vendor_id={id}`.
   - Load bill payments via `/bill-payments?vendor_id={id}`.
   - Derive outstanding bills and vendor credit balance client-side from existing payloads, or add a small backend summary route if the client-side shape becomes too awkward.

3. **Detail layout**
   - Summary cards: current balance, credit balance, contact channel(s).
   - Vendor details section: terms, tax/account number, default expense account, address, notes.
   - Preferred items section.
   - Outstanding bills / bill history section.
   - Payment history section.

4. **Regression coverage**
   - Add focused JS coverage similar to `tests/js_customer_detail_navigation.test.js` but for vendors.
   - Confirm preferred items and outstanding bill rows render from filtered API data.

## Impacted files
- `app/static/js/vendors.js` — add detail state, view loader, renderDetailScreen.
- `app/static/js/app.js` — add `/vendors/detail` route.
- Potentially `app/routes/vendors.py` only if extra summary data is needed.
- Existing APIs likely sufficient: `app/routes/items.py`, `app/routes/bills.py`, `app/routes/bill_payments.py`.
- New JS regression test for vendor detail navigation/rendering.

## Acceptance criteria
- Clicking a vendor from the vendor list opens a vendor detail page.
- Vendor detail shows preferred-supplier items using current `items.vendor_id` data.
- Vendor detail shows outstanding bills and bill history.
- Vendor detail shows vendor credit balance based on current AP data (e.g. unallocated bill payments) and current vendor balance.
- Vendor detail shows edit action and returns cleanly to the vendor list.

## Test plan
- JS test for vendor detail route + rendering.
- JS test for preferred items, bills, and credit-balance display from mocked API responses.
- `git diff --check` on planning artifacts.

## Risks and mitigations
- **Risk:** “Credit balance” is ambiguous without a first-class vendor-credit model.  
  **Mitigation:** explicitly define it in this slice as unallocated bill payments and label it accordingly if needed.
- **Risk:** Client-side composition becomes too complex.  
  **Mitigation:** start with existing filtered APIs; add a small backend summary only if the UI becomes awkward.
- **Risk:** Vendor balance field semantics may differ from user expectations.  
  **Mitigation:** show both net balance and derived outstanding/credit breakdown so the page is transparent about what is being shown.
