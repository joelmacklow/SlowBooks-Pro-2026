# System Account Decoupling Slice

## Summary
Decouple runtime system-account selection from hardcoded account numbers by introducing settings-backed account-role mappings with legacy fallback.

## Key Changes
- Add explicit system-account roles for core posting/default-selection flows.
- Resolve roles from settings first, then fall back to legacy account discovery.
- Replace current hardcoded account-number selection hotspots in runtime code and key UI defaults.
- Defer default chart replacement until after this foundation exists.

## Test Plan
- Add tests for explicit role mapping, legacy fallback, and runtime flow compatibility.
- Run full repo verification and explicit accounting/runtime safety review.

## Defaults
- Settings-backed roles are preferred.
- Legacy heuristics remain as fallback in this slice.
