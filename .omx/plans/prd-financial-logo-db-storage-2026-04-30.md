# PRD — Persist uploaded company logo in the database and rebalance report header

## Date
2026-04-30

## Objective
Make uploaded company logos survive program updates by persisting the image payload in the database, while slightly shrinking the financial report header tile and enlarging the rendered top-right logo.

## Problem
The current logo upload flow stores the image file on disk and only remembers a filesystem path in settings. If a program update or deployment clears uploaded files, the logo can disappear even though the configuration still exists. The newly added top-right logo copy in financial PDFs also needs a small layout refinement: the text tile should be a little smaller and the logo should be a little larger.

## Scope
### In scope
- database-backed storage of the uploaded company logo image payload
- keeping the existing upload path for compatibility, while adding a durable DB-backed fallback
- using the DB-backed logo payload when rendering PDFs and the company settings UI preview
- slightly reducing the report/title tile footprint and increasing the logo display size
- updating regression tests around upload persistence and PDF rendering
- schema migration for the settings value column if needed for logo payload size

### Out of scope
- redesigning the whole PDF header system
- changing non-logo settings behavior
- modifying email templates
- removing the existing file-based upload path entirely

## Requirements
1. Uploaded company logos must be persisted in the database, not only on disk.
2. The uploaded logo should still continue to work with the existing static upload path when present.
3. PDF rendering should prefer the DB-backed logo source so report generation does not depend on uploaded files surviving updates.
4. The settings page should continue to show the logo after reloads, even if the file copy is missing.
5. The financial report title/header tile should be slightly smaller and the logo slightly larger.
6. Existing PDF and upload validation behavior must remain intact.

## Implementation sketch
- Add a new settings key for a DB-backed logo data URI payload.
- Store the uploaded image bytes as a data URI in the database during upload.
- Continue writing the file to the uploads directory for compatibility.
- Update the PDF service and settings UI to use the DB-backed payload as a fallback or preferred source.
- Increase shared logo display size slightly and trim the report header tile width.
- Add/adjust migration(s) so the settings table can hold the logo payload.

## Risks
- Storing the logo payload in settings increases database row size.
- A migration is required for the settings value column if the payload exceeds the previous short-string limit.
- The report header can become cramped if the logo is enlarged too aggressively.
- The report template is structurally separate from the shared document partials, so it must stay in sync manually.

## Acceptance criteria
- A uploaded logo survives if the static upload directory is cleared, because the DB copy remains available.
- PDF generation uses the DB-backed logo source when needed.
- The logo is visibly a bit larger and the report header tile a bit smaller.
- The upload and PDF formatting tests continue to pass.
