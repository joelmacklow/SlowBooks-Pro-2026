# Posting Lifecycle Hardening Slice

## Summary
Finish the remaining posted-document lifecycle rules so bills and credit memos either reverse/repost correctly on financial edits or block ambiguous edits once payments or applications exist.

## Key Changes
- Add explicit update rules for posted bills and credit memos.
- Reverse and repost journals for eligible financial edits such as date or line changes.
- Allow non-financial metadata edits without rebuilding journals.
- Reject totals-affecting bill edits once payments exist, and reject totals-affecting credit memo edits once applications exist.
- Preserve closing-date protection for any reversal-producing change.

## Test Plan
- Add failing backend tests first for posted bill financial edits, posted bill metadata edits, paid bill edit rejection, unapplied credit memo reposting, applied credit memo edit rejection, and closing-date rejection.
- Run full Python/JS verification, syntax checks, and `git diff --check`.

## Defaults
- Metadata-only edits stay allowed.
- Financial edits on documents with dependent payment/application state are blocked instead of auto-rewriting downstream records.
