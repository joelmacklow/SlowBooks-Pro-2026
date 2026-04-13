# NZ PAYE Core + Posting Slice

## Summary
Implement the first real NZ payroll execution slice by replacing the payroll placeholder with draft pay-run creation, NZ PAYE calculations, and accounting posting.

## Key Changes
- Replace US pay-stub tax fields with NZ payroll deduction fields.
- Use versioned NZ payroll rules by tax year for PAYE, ACC, and student loan calculations.
- Add child support amount capture to employee setup and apply protected-net deduction logic.
- Create/process payroll runs through `/api/payroll`, posting wages, PAYE, KiwiSaver, ESCT, child support, and payroll-clearing journals.
- Update the Payroll UI from placeholder copy to draft pay-run creation, review, and processing.

## Test Plan
- Backend tests for salary/hourly run creation, deduction calculations, posting, and re-process rejection.
- Frontend tests for the NZ payroll page and employee form updates.
- Full repo verification plus explicit payroll security review before commit/push.

## Defaults
- Scope includes draft runs plus journal posting, but not payslips or payday filing exports.
- NZ payroll accounts are seeded and also auto-created on demand during posting.
