# Spec: Bills GST cleanup and bill-style reconciliation coding

## Requirements summary
The bills workflow already stores GST codes and computes purchase GST on the backend, but the Enter Bill modal does not expose invoice-style live calculations or a subtotal/GST/grand-total summary. Users therefore cannot verify the purchase GST breakdown while entering bills. In bank reconciliation, split coding is currently gross-only and cannot allocate GST across multiple purchase accounts, which makes supplier-payment style reconciliations hard to balance accurately.

## Functional requirements
1. **Bill entry live GST calculations**
   - The Enter Bill modal must recalculate line amounts when quantity, rate, or GST code changes.
   - The modal must show Subtotal, GST, and Grand Total before save.
   - The totals must support mixed GST codes across bill lines.

2. **Bill detail GST visibility**
   - Bill detail must show subtotal, GST, total, paid, and balance, not only total-level values.

3. **GST-aware purchase split coding**
   - Reconciliation split coding must support GST metadata per split line for purchase-style outflows.
   - The user must be able to split one bank statement outflow across multiple expense accounts and GST codes while keeping the overall bank line total balanced.
   - The system must derive the correct net expense + input GST postings from the gross split inputs.

4. **Non-regression requirements**
   - Existing outstanding-bill matching remains available and unchanged.
   - Existing simple split coding remains available for non-purchase or GST-free flows.
   - Existing server-side bill GST posting remains the source of truth for saved bill journals.

## Proposed design
### A. Bills modal parity with invoice editor
- Add a bill-side totals helper modeled on `InvoicesPage._totals()` (`app/static/js/invoices.js:131-138`).
- Add change handlers on bill line qty/rate/GST controls so each row and the totals panel refresh without save.
- Render a right-side summary box in the Enter Bill modal like invoices already do (`app/static/js/invoices.js:206-219`).

### B. Shared GST UI utilities
- Prefer extracting shared client-side GST-total logic into a reusable helper if invoices and bills would otherwise duplicate the same calculations.
- Keep any extraction small and mechanical; do not redesign every sales/purchases editor in the same slice.

### C. GST-aware purchase split coding
- Extend `BankTransactionSplitLine` so the purchase path can carry GST choice per line.
- In `code-split`, detect purchase-style/GST-aware submissions and run them through the purchase GST calculator before posting journals.
- Journal shape for an outflow should become:
  - debit expense net lines;
  - debit GST input line(s) or combined GST line;
  - credit linked bank account gross total.

### D. Reconciliation UX
- Extend the split-code modal with GST selectors and running subtotal/GST/total display.
- Keep the modal validation strict: split gross total must equal the bank statement line exactly.

## Out of scope
- Full bill edit-screen redesign beyond GST/totals parity.
- Automatic bill creation from reconciliation in this slice unless it is strictly necessary to support GST-aware purchase allocation.
- Changes to bank statement import, reconciliation completion, or bank-rule matching unrelated to GST allocation.

## File-level implementation notes
- `app/static/js/bills.js`
  - add draft-state totals helper and row recalculation
  - render Subtotal/GST/Grand Total in Enter Bill and bill detail
- `app/routes/bills.py`
  - verify bill detail response is sufficient for the new UI; only extend if needed
- `app/schemas/banking.py`
  - extend split-line request model with GST fields for purchase splits
- `app/routes/banking.py`
  - add GST-aware purchase split posting branch
- `app/static/js/banking.js`
  - add GST controls and totals preview to reconciliation split-code modal
- Tests
  - extend `tests/test_document_gst_calculations.py`
  - extend `tests/test_bank_reconciliation_split_coding.py`
  - add/extend focused JS tests for bills and reconciliation UI

## Verification steps
1. Enter a bill with one GST15 line and verify live Subtotal/GST/Grand Total match the saved bill.
2. Enter a mixed-GST bill (e.g. GST15 + NO_GST) and verify totals and saved journal split input GST correctly.
3. Reconcile a supplier-payment statement line using split coding across multiple expense accounts with different GST codes and verify the total balances exactly.
4. Reconcile a non-GST split-coded line and verify the old generic split behavior still works.
5. Match an existing outstanding bill in reconciliation and verify the pre-existing bill-payment flow still works.

## Risk notes
- The most likely defect is client/server GST parity drift; treat shared samples and regression tests as mandatory.
- The second biggest risk is overloading split coding with bill semantics; keep the API explicit about when GST-aware purchase allocation is active.
