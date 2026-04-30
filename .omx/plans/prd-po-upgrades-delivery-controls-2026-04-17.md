# PRD — Purchase Order delivery controls and document actions

## Date
2026-04-17

## Problem
Purchase orders currently allow a free-form delivery address and do not expose a print/PDF action in the PO UI. That creates delivery-control risk because goods can be directed to arbitrary destinations, and it slows PO fulfillment workflows.

## Goals
1. Restrict PO delivery destinations to an approved list of company locations.
2. Make the approved location list admin-managed.
3. Replace the PO delivery address free-text field with a selectable approved location list.
4. Add PO document actions in the PO detail workflow so users can email the PO to the vendor and open a printable PDF.
5. Preserve existing PO email + PDF backend behavior while tightening server-side delivery validation.

## Non-goals
- Full warehouse/location master-data module.
- Vendor-specific delivery rules.
- Changing who may create purchase orders.
- Reworking unrelated settings or purchasing flows.

## Users
- Operations/admin users who manage company settings and approved delivery locations.
- Purchasing users who create, update, email, and print purchase orders.

## Requirements
### Approved delivery locations
- Add an admin-only settings surface for approved PO delivery locations.
- Store delivery locations as a managed list in company settings.
- Include the company’s primary address as an approved location when present so admins do not need to duplicate it.
- Expose a read endpoint for purchasing users to retrieve the approved delivery options without exposing sensitive settings.

### Purchase order editor
- Replace free-form `Delivery Address` entry with a required select/list of approved delivery locations.
- Existing POs should still display their saved delivery address text.
- New or edited POs must save only approved location values.
- Server-side validation must reject unapproved `ship_to` values even if a client is tampered with.

### Document actions
- Add actions alongside the PO create/update button for:
  - Email PO to vendor email
  - Print / PDF
- Keep actions permission-aware and usable from the PO detail workflow.
- Keep list-level PO actions functional; adding PDF there too is acceptable if low-risk.

## Security / RBAC
- Only users with `settings.manage` may manage the approved delivery-location list.
- Purchasing users may select from the approved list but may not define arbitrary destinations.
- Delivery location enforcement must happen on the server.

## Acceptance criteria
1. Admin can save approved PO delivery locations in settings.
2. Purchasing users can load approved delivery locations without requiring full settings access.
3. PO detail screen renders a select/list of approved locations instead of a free-text textarea.
4. Creating/updating a PO with an unapproved `ship_to` is rejected by the API.
5. PO detail screen exposes Email and Print/PDF actions beside the primary save button when appropriate.
6. Email defaults to the vendor email when present.
7. Existing tests and new PO-specific tests pass.
