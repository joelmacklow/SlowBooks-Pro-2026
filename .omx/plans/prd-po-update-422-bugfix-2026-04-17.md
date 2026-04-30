# PRD — Purchase Order update 422 bugfix

## Date
2026-04-17

## Problem
Updating an existing purchase order currently fails with `PUT /api/purchase-orders/{id}` returning HTTP 422, so the UI shows an error and the update does not persist.

## Goal
Restore successful purchase order updates without regressing the new PO create/add-new/email/PDF workflows.

## Requirements
- Reproduce the update failure with an automated test.
- Identify whether the 422 is request-body validation or response validation.
- Apply the minimal backend or UI fix needed so valid PO updates succeed.
- Keep create, create-and-dispatch, and existing saved-PO actions working.

## Acceptance criteria
1. A valid PO update request succeeds without 422.
2. The PO update UI path can submit a normal saved PO edit payload.
3. Existing PO create/email/PDF/add-new tests still pass.
