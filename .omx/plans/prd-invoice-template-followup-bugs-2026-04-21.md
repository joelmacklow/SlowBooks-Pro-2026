# PRD — Invoice template follow-up fixes after document refresh

## Date
2026-04-21

## Objective
Fix the remaining invoice template regressions reported after the document-family refresh:
- company logo should replace the company-name text when present
- due date should not appear twice at the top of the invoice
- company GST number should appear in the header/company details
- customer details should be richer in the Bill To block
- payment advice should show the customer name/details reliably
- invoice number and amount-due labels/values should not wrap unnecessarily

## Current-state evidence
- The current invoice template lives in `app/templates/invoice_pdf.html`.
- It always renders `company.company_name` as text in the header and does not check `company.company_logo_path`.
- It shows the due date twice near the top:
  - header subtitle: `Due {{ inv.due_date | fdate }}`
  - metadata row: `Due Date`
- Company GST/IRD identity is not shown in the header even though settings data includes `gst_number` and `company_tax_id`.
- Bill To only uses `inv.customer_name` and invoice-stored billing address fields; it omits other customer details such as company/email/phone even when `inv.customer` is available from the relationship.
- Payment Advice uses `inv.customer_name` only, which can be sparse/empty relative to `inv.customer`.
- The shared document theme in `app/templates/_document_theme.html` has no nowrap utility for document numbers or narrow remittance fields.

## Problem
The refreshed invoice template is close, but key production details are still wrong or incomplete for real customer-facing documents, especially when a logo is configured and when the remittance/payment-advice area needs compact, non-wrapping metadata.

## Requirements
1. If `company_logo_path` exists, display the logo in the company header instead of the company-name text block header label.
2. Company GST number must appear in the company details block when available (`gst_number`, falling back to `company_tax_id` if needed).
3. The top-of-document due date should appear only once.
4. Bill To must include richer customer detail when available (name/company/email/phone + address).
5. Payment Advice must show the customer name reliably and avoid empty-name output.
6. Invoice number and Amount Due lines in the compact/remittance area must not wrap unnecessarily.
7. Existing escaping behavior and data bindings must remain intact.

## Recommended direction
- Keep the current refreshed invoice layout, but patch the missing data/display logic directly in `invoice_pdf.html` and the shared theme.
- Use existing invoice/customer/company fields only; do not widen the data model in this slice.
- Add CSS utility classes for non-wrapping remittance/header fields instead of ad hoc inline hacks.

## Acceptance criteria
- Invoice header shows logo instead of company-name text when a logo path exists.
- GST number is visible when configured.
- Due date is no longer duplicated at the top of the invoice.
- Bill To and Payment Advice show customer details reliably.
- Invoice number and amount-due text stay on one line in the compact areas.
- Targeted PDF formatting tests lock the new behavior.

## Risks and mitigations
- **Risk:** company-logo rendering could break text-only fallback.  
  **Mitigation:** preserve the existing company-name text path when no logo is set.
- **Risk:** richer customer detail could expose blank lines/noisy output.  
  **Mitigation:** render each detail conditionally.
- **Risk:** nowrap styles could cause clipping if overused.  
  **Mitigation:** apply them narrowly to invoice/remittance fields only.
