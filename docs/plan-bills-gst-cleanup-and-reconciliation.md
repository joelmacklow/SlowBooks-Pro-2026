# Plan: Bills GST cleanup and bill-style reconciliation coding

## Objective
Restore end-to-end GST correctness for purchases by (1) making the Enter Bill flow behave like invoices with live GST-aware subtotal/tax/total feedback, and (2) extending bank reconciliation split coding so purchase-style outflows can allocate GST correctly while still balancing to the bank statement total.

## Current state summary
- Bills already store GST per line and calculate purchase GST server-side. The bill route resolves line GST codes and runs `calculate_document_gst(..., gst_context="purchase")` before saving totals and posting journals (`app/routes/bills.py:149-178`, `app/services/gst_lines.py:27-38`, `app/services/gst_calculations.py:64-118`).
- Bill rows persist `gst_code` / `gst_rate` and header totals (`subtotal`, `tax_amount`, `total`) already exist in the model/schema (`app/models/bills.py:42-47`, `app/models/bills.py:75-85`, `app/schemas/bills.py:7-15`, `app/schemas/bills.py:56-76`).
- The Enter Bill modal exposes a GST selector per line, but the UI only renders static qty/rate/amount cells and a save button — no live GST subtotal/tax/total panel, no invoice-style totals model, and no visible recalculation hooks (`app/static/js/bills.js:122-158`, `app/static/js/bills.js:161-203`).
- Invoices already have the reference interaction: a GST-aware `_totals()` helper plus Subtotal/Tax/Total rendering in the detail screen (`app/static/js/invoices.js:131-138`, `app/static/js/invoices.js:206-219`).
- Bank reconciliation split coding currently accepts only `account_id`, `amount`, and `description` per split line, and posts those amounts directly as gross account debits/credits with no GST metadata or purchase/sales context (`app/schemas/banking.py:85-93`, `app/routes/banking.py:465-539`, `app/static/js/banking.js:560-570`, `app/static/js/banking.js:615-629`).
- Bill matching in reconciliation only supports paying an existing outstanding bill; it does not help a user allocate a new supplier payment across multiple expense/GST lines (`app/routes/banking.py:383-413`).

## Constraints
- Reuse the existing NZ GST engine rather than inventing bill-only tax math (`app/services/gst_calculations.py:64-118`).
- Keep bill create/update journaling aligned with current AP posting rules: expense net debits + GST debit + AP credit (`app/routes/bills.py:30-70`, `app/routes/bills.py:156-178`, `tests/test_document_gst_calculations.py:176-206`).
- Do not regress existing bill payment / outstanding bill matching in reconciliation (`app/routes/banking.py:383-413`).
- Preserve the existing simple split-coding path for non-bill/non-GST transactions; GST-aware purchase splitting should extend it, not remove it (`app/routes/banking.py:418-539`).
- Keep the scope reviewable: this slice should fix GST correctness and reconciliation usability, not redesign all AP flows.

## Recommended implementation sketch
1. **Bills UI parity with invoices**
   - Refactor `BillsPage.showForm()` to maintain draft line state, reuse the same GST helper pattern invoices use, and recalculate each line amount plus subtotal/GST/grand total on qty/rate/GST changes.
   - Add an invoice-style totals panel to the Enter Bill modal showing Subtotal, GST, and Grand Total before save.
   - Ensure the per-line amount column reflects the selected GST mode consistently with the backend purchase context.

2. **Bill detail and payload cleanup**
   - Make bill detail output show subtotal/tax/total explicitly, not only total/paid/balance, so the saved bill reflects the same GST breakdown the user saw when entering it.
   - If needed, extend bill response payloads with any missing derived values needed by the UI, but prefer existing `subtotal`, `tax_amount`, and `total` fields already in `BillResponse`.

3. **GST-aware reconciliation split coding for purchases**
   - Extend bank split-code schemas so a split line can carry `gst_code` (and derived `gst_rate`) for purchase-style outflows.
   - Add a purchase-mode split-code path that uses `calculate_document_gst(..., gst_context="purchase")` to transform gross split inputs into net expense debits plus input-GST debit, while still crediting the linked bank account for the gross statement amount.
   - Keep the current gross-only split path for transfers / non-GST / simple categorization.

4. **Reconciliation UX for bill-style coding**
   - Update the split-code modal to let users choose GST per split line and see running Subtotal/GST/Total validation before submitting.
   - Make the reconciliation UI clearly indicate when it is doing bill-style purchase allocation versus generic split coding.

5. **Regression coverage**
   - Add JS tests for bill-entry live totals and GST recalculation.
   - Add backend tests for GST-aware purchase split coding journals and exact-total validation.
   - Add integration tests that prove a GST-coded supplier outflow can be reconciled and balances exactly to the bank line.

## Impacted files
- `app/static/js/bills.js` — Enter Bill modal behavior, line recalculation, totals panel, bill detail totals.
- `app/static/js/invoices.js` — reference pattern to mirror or extract shared GST totals behavior from.
- `app/routes/bills.py` — verify UI/server parity and expose any missing bill detail data.
- `app/schemas/banking.py` — extend split-code request models for GST-aware purchase splits.
- `app/routes/banking.py` — add GST-aware split posting path without regressing the existing generic split flow.
- `app/static/js/banking.js` — reconciliation split modal, GST controls, validation, bill-style totals display.
- `app/services/gst_calculations.py` / `app/services/gst_lines.py` — reuse existing GST engine and line resolution rather than duplicate logic.
- `tests/test_document_gst_calculations.py` — extend bill-side GST coverage.
- `tests/test_bank_reconciliation_split_coding.py` — extend split-coding coverage for GST-aware purchase allocations.
- New focused JS test(s), likely under `tests/js_bills_*.test.js` and/or existing banking reconciliation UI tests.

## Acceptance criteria
- In Enter Bill, changing qty/rate/GST updates the line amount immediately and keeps a visible Subtotal, GST, and Grand Total in sync before save.
- Saving a bill produces the same subtotal/tax/total the user saw in the modal, including mixed GST-code bills.
- Bill detail shows subtotal, GST, and total clearly.
- Reconciliation split coding can capture GST per purchase split line and validate that the gross bank line total balances exactly.
- GST-aware purchase split coding posts balanced journals that separate expense net amounts from input GST.
- Existing non-GST split coding and existing outstanding-bill matching still work unchanged.

## Test plan
- Targeted JS tests for bill modal recalculation, totals rendering, and GST-code changes.
- Targeted JS tests for reconciliation split modal GST fields and running-balance validation.
- Python unit/integration tests for:
  - mixed-GST bill create/update totals;
  - GST-aware purchase split coding journal construction;
  - exact-total mismatch rejection;
  - preservation of current simple split-coding behavior;
  - preservation of current bill-match reconciliation behavior.
- `git diff --check`, targeted pytest, and targeted JS runs for touched paths.

## Risks and mitigations
- **Risk:** UI totals drift from backend totals.  
  **Mitigation:** drive both from the existing GST calculation contract and add parity tests using the same sample payloads.
- **Risk:** GST-aware split coding breaks transfer/income scenarios.  
  **Mitigation:** keep a separate purchase-style branch in the API/UI and preserve the current generic split path for non-purchase flows.
- **Risk:** Users confuse bill-style coding with paying an existing bill.  
  **Mitigation:** keep existing outstanding-bill match flow intact and label the new split mode explicitly as purchase allocation / bill-style coding.
- **Risk:** Scope balloons into full bill editing redesign.  
  **Mitigation:** limit this slice to GST visibility/correctness and reconciliation allocation, not broader AP workflow changes.
