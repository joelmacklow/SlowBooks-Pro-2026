# Security Review — Posting Lifecycle Hardening (2026-04-14)

## Scope Reviewed
- `app/routes/bills.py`
- `app/routes/credit_memos.py`
- `app/schemas/bills.py`
- `app/schemas/credit_memos.py`
- posting lifecycle regression tests

## Review Focus
- Preventing stale or inconsistent journal entries after document edits
- Blocking ambiguous edits once dependent payments or applications exist
- Preserving closing-date controls for reversal-producing changes

## Findings
1. **Financial edits now preserve journal integrity instead of silently diverging**
   - Posted bills and unapplied credit memos now reverse and repost their journals when financial fields change.
   - This reduces the risk of mismatched document totals versus ledger balances.

2. **Dependent-state edits fail closed**
   - Bills with payments and credit memos with applications now reject totals-affecting edits rather than trying to rewrite downstream allocations.
   - This is the safer default for accounting integrity and auditability.

3. **Closing-date enforcement remains active on repost paths**
   - The slice checks both the original posting date and any new posting date before allowing reversal/repost operations.
   - This preserves period-close protections on edit paths that were previously uncovered.

## Residual Risks
- Metadata-only edits remain allowed on paid bills and applied credit memos. That is intentional for this slice, but future audit-history UX may still want to expose those edits more explicitly.
- The repo still uses a broad trusted-admin model overall; this slice improves accounting integrity, not authentication/authorization.

## Conclusion
- No new CRITICAL/HIGH security issues identified in this slice.
- Residual risk is **LOW to MEDIUM** and is mostly tied to broader app trust boundaries rather than the posting lifecycle changes themselves.
