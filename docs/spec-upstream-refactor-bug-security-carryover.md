# Spec: carry over upstream bug/security fixes relevant to SlowBooks NZ

## Goal
Bring over the upstream fixes that improve security, correctness, and runtime robustness for the NZ branch without importing unrelated US-domain behavior or broad schema churn.

## Required Behavior
- Email sending must strip CR/LF from recipient and subject headers and close SMTP connections on failure as well as success.
- Closing-date password checks must use a timing-safe comparison.
- Logo uploads must reject SVG and continue allowing the safe raster image types already used by the product.
- `escapeHtml()` must escape single quotes, and `todayISO()` must return the local calendar date rather than UTC-truncated ISO output.
- The topbar search Escape handler must clear results only on Escape, not every keypress.
- Journal creation must reject negative amounts and lines with both debit and credit populated.
- Statement PDF balance-due rendering must use explicit arithmetic grouping.
- Container/runtime hardening must add a non-root runtime user and `pipefail` to the backup shell script.

## Verification
- Targeted backend/frontend regressions for each changed behavior.
- Full Python unittest discover suite.
- JS test suite.
- `py_compile`, shell syntax checks, and `git diff --check`.

## Assumptions
- The current DB-wait entrypoint already has a bounded timeout/failure path, so no entrypoint behavior change is required unless tests show a gap.
- Attachments hardening stays deferred until that feature exists on this branch.
