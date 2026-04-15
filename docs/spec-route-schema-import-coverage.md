# Spec: Prevent route imports from referencing missing schema modules

## Deliverable
Ensure route modules do not import nonexistent `app.schemas.*` modules.

## Rules
- Add automated coverage that fails when a route imports a schema module with no
  corresponding file in `app/schemas`.
- Remove the dead `app.schemas.bank_import` import from
  `app/routes/bank_import.py`.
- Do not change the bank import endpoint contract beyond removing the broken,
  unused import.
