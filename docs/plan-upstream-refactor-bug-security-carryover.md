# Plan: carry over upstream bug/security fixes relevant to SlowBooks NZ

## Summary
Apply the NZ-relevant subset of upstream commit `eabec2a1db5f944f4975f897e12381aa496f89b2`: small bug/security fixes plus container/backup hardening, while explicitly excluding US payroll changes and broad schema/performance churn.

## Key Changes
- Harden email delivery against header injection and SMTP connection leaks.
- Replace closing-date password equality with timing-safe comparison.
- Tighten logo upload types and preserve current RBAC behavior.
- Fix shared frontend helpers (`escapeHtml`, `todayISO`) and the topbar search keydown bug.
- Add explicit journal-line validation and make the statement PDF balance expression unambiguous.
- Harden container/runtime shell assets where they are still weaker than upstream (`Dockerfile`, `scripts/backup.sh`).

## Test Plan
- Add/extend regression tests for email sanitization/cleanup, upload MIME restrictions, helper/date behavior, journal validation, and statement PDF totals.
- Re-run targeted tests, full Python unittest discover, JS tests, syntax checks, shell checks, and `git diff --check`.
- Write a security review artifact because this slice includes email/upload/input hardening.

## Constraints
- Reuse the branch’s existing NZ-specific logic and existing hardening work.
- Do not pull in US payroll logic, broad FK/index migrations, or multi-company header behavior in this slice.
- No new dependencies.
