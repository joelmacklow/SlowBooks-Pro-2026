import os
import unittest
from datetime import date, time
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.database import Base


class TimesheetServiceTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def _employee(self, db, **overrides):
        from app.models.payroll import Employee

        payload = {
            "first_name": "Aroha",
            "last_name": "Ngata",
            "ird_number": "123456789",
            "pay_type": "hourly",
            "pay_rate": Decimal("30.00"),
            "tax_code": "M",
            "kiwisaver_enrolled": False,
            "kiwisaver_rate": Decimal("0.0350"),
            "student_loan": False,
            "child_support": False,
            "child_support_amount": Decimal("0.00"),
            "esct_rate": Decimal("0.0000"),
            "pay_frequency": "weekly",
            "is_active": True,
        }
        payload.update(overrides)
        employee = Employee(**payload)
        db.add(employee)
        db.commit()
        db.refresh(employee)
        return employee

    @staticmethod
    def _duration_line(work_date: date, hours: str):
        from app.schemas.timesheets import TimesheetLineUpsert

        return TimesheetLineUpsert(work_date=work_date, entry_mode="duration", duration_hours=Decimal(hours))

    @staticmethod
    def _start_end_line(work_date: date, start: time, end: time, break_minutes: int = 0):
        from app.schemas.timesheets import TimesheetLineUpsert

        return TimesheetLineUpsert(
            work_date=work_date,
            entry_mode="start_end",
            start_time=start,
            end_time=end,
            break_minutes=break_minutes,
        )

    def test_create_draft_timesheet_with_duration_lines_calculates_total(self):
        from app.models.timesheets import TimesheetAuditEvent
        from app.services.timesheets import create_timesheet

        with self.Session() as db:
            employee = self._employee(db)
            timesheet = create_timesheet(
                db,
                employee_id=employee.id,
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 7),
                lines=[
                    self._duration_line(date(2026, 4, 1), "7.25"),
                    self._duration_line(date(2026, 4, 2), "8.00"),
                ],
                actor_user_id=10,
            )
            events = db.query(TimesheetAuditEvent).filter(TimesheetAuditEvent.timesheet_id == timesheet.id).all()
            line_count = len(timesheet.lines)

        self.assertEqual(timesheet.status.value, "draft")
        self.assertEqual(Decimal(str(timesheet.total_hours)), Decimal("15.25"))
        self.assertEqual(line_count, 2)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].action, "create")
        self.assertEqual(events[0].actor_user_id, 10)

    def test_create_draft_timesheet_with_start_end_break_calculates_total(self):
        from app.services.timesheets import create_timesheet

        with self.Session() as db:
            employee = self._employee(db)
            timesheet = create_timesheet(
                db,
                employee_id=employee.id,
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 7),
                lines=[self._start_end_line(date(2026, 4, 2), time(9, 0), time(17, 0), break_minutes=30)],
            )
            first_line_duration = Decimal(str(timesheet.lines[0].duration_hours))

        self.assertEqual(Decimal(str(timesheet.total_hours)), Decimal("7.50"))
        self.assertEqual(first_line_duration, Decimal("7.50"))

    def test_duplicate_employee_period_is_rejected(self):
        from app.models.timesheets import Timesheet
        from app.services.timesheets import create_timesheet

        with self.Session() as db:
            employee = self._employee(db)
            create_timesheet(
                db,
                employee_id=employee.id,
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 7),
                lines=[self._duration_line(date(2026, 4, 1), "8.00")],
            )
            with self.assertRaises(ValueError):
                create_timesheet(
                    db,
                    employee_id=employee.id,
                    period_start=date(2026, 4, 1),
                    period_end=date(2026, 4, 7),
                    lines=[self._duration_line(date(2026, 4, 2), "8.00")],
                )
            count = db.query(Timesheet).count()

        self.assertEqual(count, 1)

    def test_invalid_period_and_out_of_period_work_date_are_rejected(self):
        from app.services.timesheets import create_timesheet

        with self.Session() as db:
            employee = self._employee(db)
            with self.assertRaises(ValueError):
                create_timesheet(
                    db,
                    employee_id=employee.id,
                    period_start=date(2026, 4, 8),
                    period_end=date(2026, 4, 7),
                    lines=[self._duration_line(date(2026, 4, 7), "8.00")],
                )
            with self.assertRaises(ValueError):
                create_timesheet(
                    db,
                    employee_id=employee.id,
                    period_start=date(2026, 4, 1),
                    period_end=date(2026, 4, 7),
                    lines=[self._duration_line(date(2026, 4, 8), "8.00")],
                )

    def test_invalid_duration_values_are_rejected(self):
        from app.services.timesheets import create_timesheet

        with self.Session() as db:
            employee = self._employee(db)
            with self.assertRaises(ValueError):
                create_timesheet(
                    db,
                    employee_id=employee.id,
                    period_start=date(2026, 4, 1),
                    period_end=date(2026, 4, 7),
                    lines=[self._duration_line(date(2026, 4, 1), "-1.00")],
                )
            with self.assertRaises(ValueError):
                create_timesheet(
                    db,
                    employee_id=employee.id,
                    period_start=date(2026, 4, 1),
                    period_end=date(2026, 4, 7),
                    lines=[self._duration_line(date(2026, 4, 1), "0.00")],
                )
            with self.assertRaises(ValueError):
                create_timesheet(
                    db,
                    employee_id=employee.id,
                    period_start=date(2026, 4, 1),
                    period_end=date(2026, 4, 7),
                    lines=[self._duration_line(date(2026, 4, 1), "24.01")],
                )

    def test_invalid_start_end_values_are_rejected(self):
        from app.schemas.timesheets import TimesheetLineUpsert
        from app.services.timesheets import create_timesheet

        with self.Session() as db:
            employee = self._employee(db)
            with self.assertRaises(ValueError):
                create_timesheet(
                    db,
                    employee_id=employee.id,
                    period_start=date(2026, 4, 1),
                    period_end=date(2026, 4, 7),
                    lines=[TimesheetLineUpsert(work_date=date(2026, 4, 1), entry_mode="start_end")],
                )
            with self.assertRaises(ValueError):
                create_timesheet(
                    db,
                    employee_id=employee.id,
                    period_start=date(2026, 4, 1),
                    period_end=date(2026, 4, 7),
                    lines=[self._start_end_line(date(2026, 4, 1), time(9, 0), time(9, 0), break_minutes=0)],
                )
            with self.assertRaises(ValueError):
                create_timesheet(
                    db,
                    employee_id=employee.id,
                    period_start=date(2026, 4, 1),
                    period_end=date(2026, 4, 7),
                    lines=[self._start_end_line(date(2026, 4, 1), time(9, 0), time(17, 0), break_minutes=480)],
                )
            with self.assertRaises(ValueError):
                create_timesheet(
                    db,
                    employee_id=employee.id,
                    period_start=date(2026, 4, 1),
                    period_end=date(2026, 4, 7),
                    lines=[self._start_end_line(date(2026, 4, 1), time(22, 0), time(6, 0), break_minutes=0)],
                )

    def test_update_draft_replaces_lines_recalculates_total_and_audits(self):
        from app.models.timesheets import TimesheetAuditEvent
        from app.services.timesheets import create_timesheet, update_timesheet

        with self.Session() as db:
            employee = self._employee(db)
            timesheet = create_timesheet(
                db,
                employee_id=employee.id,
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 7),
                lines=[self._duration_line(date(2026, 4, 1), "8.00")],
            )
            updated = update_timesheet(
                db,
                timesheet_id=timesheet.id,
                lines=[self._duration_line(date(2026, 4, 2), "6.50"), self._duration_line(date(2026, 4, 3), "7.00")],
                actor_user_id=33,
            )
            events = db.query(TimesheetAuditEvent).filter(TimesheetAuditEvent.timesheet_id == timesheet.id).order_by(TimesheetAuditEvent.id.asc()).all()
            updated_line_count = len(updated.lines)

        self.assertEqual(updated_line_count, 2)
        self.assertEqual(Decimal(str(updated.total_hours)), Decimal("13.50"))
        self.assertEqual(events[-1].action, "update")
        self.assertEqual(events[-1].actor_user_id, 33)

    def test_submitted_approved_and_locked_timesheets_cannot_be_edited(self):
        from app.services.timesheets import approve_timesheet, create_timesheet, lock_timesheet, submit_timesheet, update_timesheet

        with self.Session() as db:
            employee = self._employee(db)
            timesheet = create_timesheet(
                db,
                employee_id=employee.id,
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 7),
                lines=[self._duration_line(date(2026, 4, 1), "8.00")],
            )
            submitted = submit_timesheet(db, timesheet_id=timesheet.id, actor_user_id=2)
            submitted_status = submitted.status.value
            with self.assertRaises(ValueError):
                update_timesheet(db, timesheet_id=timesheet.id, lines=[self._duration_line(date(2026, 4, 2), "8.00")])
            approved = approve_timesheet(db, timesheet_id=timesheet.id, actor_user_id=2)
            approved_status = approved.status.value
            with self.assertRaises(ValueError):
                update_timesheet(db, timesheet_id=timesheet.id, lines=[self._duration_line(date(2026, 4, 2), "8.00")])
            locked = lock_timesheet(db, timesheet_id=timesheet.id, actor_user_id=2)
            locked_status = locked.status.value
            with self.assertRaises(ValueError):
                update_timesheet(db, timesheet_id=timesheet.id, lines=[self._duration_line(date(2026, 4, 2), "8.00")])

        self.assertEqual(submitted_status, "submitted")
        self.assertEqual(approved_status, "approved")
        self.assertEqual(locked_status, "locked")

    def test_lifecycle_transitions_require_valid_source_state(self):
        from app.services.timesheets import approve_timesheet, create_timesheet, lock_timesheet, reject_timesheet, submit_timesheet

        with self.Session() as db:
            employee = self._employee(db)
            timesheet = create_timesheet(
                db,
                employee_id=employee.id,
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 7),
                lines=[self._duration_line(date(2026, 4, 1), "8.00")],
            )
            submit_timesheet(db, timesheet_id=timesheet.id)
            with self.assertRaises(ValueError):
                submit_timesheet(db, timesheet_id=timesheet.id)
            approve_timesheet(db, timesheet_id=timesheet.id)
            with self.assertRaises(ValueError):
                approve_timesheet(db, timesheet_id=timesheet.id)
            with self.assertRaises(ValueError):
                reject_timesheet(db, timesheet_id=timesheet.id, reason="Too late")
            lock_timesheet(db, timesheet_id=timesheet.id)
            with self.assertRaises(ValueError):
                lock_timesheet(db, timesheet_id=timesheet.id)

    def test_reject_requires_reason_and_records_reason_in_audit(self):
        from app.models.timesheets import TimesheetAuditEvent
        from app.services.timesheets import create_timesheet, reject_timesheet, submit_timesheet

        with self.Session() as db:
            employee = self._employee(db)
            timesheet = create_timesheet(
                db,
                employee_id=employee.id,
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 7),
                lines=[self._duration_line(date(2026, 4, 1), "8.00")],
            )
            submit_timesheet(db, timesheet_id=timesheet.id)
            with self.assertRaises(ValueError):
                reject_timesheet(db, timesheet_id=timesheet.id, reason="")
            rejected = reject_timesheet(db, timesheet_id=timesheet.id, reason="Missing sign-off", actor_user_id=77)
            latest = (
                db.query(TimesheetAuditEvent)
                .filter(TimesheetAuditEvent.timesheet_id == timesheet.id)
                .order_by(TimesheetAuditEvent.id.desc())
                .first()
            )

        self.assertEqual(rejected.status.value, "rejected")
        self.assertEqual(latest.action, "reject")
        self.assertEqual(latest.reason, "Missing sign-off")
        self.assertEqual(latest.actor_user_id, 77)

    def test_rejected_timesheet_can_be_corrected_and_resubmitted(self):
        from app.services.timesheets import create_timesheet, reject_timesheet, submit_timesheet, update_timesheet

        with self.Session() as db:
            employee = self._employee(db)
            timesheet = create_timesheet(
                db,
                employee_id=employee.id,
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 7),
                lines=[self._duration_line(date(2026, 4, 1), "8.00")],
            )
            submit_timesheet(db, timesheet_id=timesheet.id)
            reject_timesheet(db, timesheet_id=timesheet.id, reason="Fix hours")
            corrected = update_timesheet(
                db,
                timesheet_id=timesheet.id,
                lines=[self._duration_line(date(2026, 4, 1), "7.50"), self._duration_line(date(2026, 4, 2), "8.00")],
            )
            corrected_status = corrected.status.value
            corrected_total = Decimal(str(corrected.total_hours))
            resubmitted = submit_timesheet(db, timesheet_id=timesheet.id)
            resubmitted_status = resubmitted.status.value

        self.assertEqual(corrected_status, "draft")
        self.assertEqual(corrected_total, Decimal("15.50"))
        self.assertEqual(resubmitted_status, "submitted")

    def test_lock_records_actor_and_prevents_later_mutation(self):
        from app.models.timesheets import TimesheetAuditEvent
        from app.services.timesheets import approve_timesheet, create_timesheet, lock_timesheet, reject_timesheet, submit_timesheet

        with self.Session() as db:
            employee = self._employee(db)
            timesheet = create_timesheet(
                db,
                employee_id=employee.id,
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 7),
                lines=[self._duration_line(date(2026, 4, 1), "8.00")],
            )
            submit_timesheet(db, timesheet_id=timesheet.id)
            approve_timesheet(db, timesheet_id=timesheet.id)
            locked = lock_timesheet(db, timesheet_id=timesheet.id, actor_user_id=9001)
            with self.assertRaises(ValueError):
                approve_timesheet(db, timesheet_id=timesheet.id)
            with self.assertRaises(ValueError):
                reject_timesheet(db, timesheet_id=timesheet.id, reason="Nope")
            latest = (
                db.query(TimesheetAuditEvent)
                .filter(TimesheetAuditEvent.timesheet_id == timesheet.id)
                .order_by(TimesheetAuditEvent.id.desc())
                .first()
            )

        self.assertIsNotNone(locked.locked_at)
        self.assertEqual(locked.status.value, "locked")
        self.assertEqual(latest.action, "lock")
        self.assertEqual(latest.actor_user_id, 9001)

    def test_response_schema_excludes_employee_payroll_private_fields(self):
        from app.schemas.timesheets import TimesheetDetailResponse, TimesheetListResponse
        from app.services.timesheets import create_timesheet

        with self.Session() as db:
            employee = self._employee(db)
            timesheet = create_timesheet(
                db,
                employee_id=employee.id,
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 7),
                lines=[self._duration_line(date(2026, 4, 1), "8.00")],
            )
            detail = TimesheetDetailResponse.model_validate(timesheet).model_dump()
            listing = TimesheetListResponse.model_validate(timesheet).model_dump()

        for hidden_field in (
            "ird_number",
            "pay_rate",
            "tax_code",
            "kiwisaver_enrolled",
            "kiwisaver_rate",
            "student_loan",
            "child_support",
            "child_support_amount",
        ):
            self.assertNotIn(hidden_field, detail)
            self.assertNotIn(hidden_field, listing)

    def test_timesheet_enum_sql_values_match_lowercase_migration_contract(self):
        from app.models.timesheets import TIMESHEET_ENTRY_MODE_ENUM, TIMESHEET_STATUS_ENUM

        self.assertEqual(TIMESHEET_STATUS_ENUM.enums, ["draft", "submitted", "approved", "rejected", "locked"])
        self.assertEqual(TIMESHEET_ENTRY_MODE_ENUM.enums, ["duration", "start_end"])

    def test_audit_events_are_written_for_each_mutation_in_order(self):
        from app.models.timesheets import TimesheetAuditEvent
        from app.services.timesheets import approve_timesheet, create_timesheet, lock_timesheet, submit_timesheet, update_timesheet

        with self.Session() as db:
            employee = self._employee(db)
            timesheet = create_timesheet(
                db,
                employee_id=employee.id,
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 7),
                lines=[self._duration_line(date(2026, 4, 1), "8.00")],
                actor_user_id=1,
            )
            update_timesheet(db, timesheet_id=timesheet.id, lines=[self._duration_line(date(2026, 4, 2), "8.50")], actor_user_id=2)
            submit_timesheet(db, timesheet_id=timesheet.id, actor_user_id=3)
            approve_timesheet(db, timesheet_id=timesheet.id, actor_user_id=4)
            lock_timesheet(db, timesheet_id=timesheet.id, actor_user_id=5)
            events = (
                db.query(TimesheetAuditEvent)
                .filter(TimesheetAuditEvent.timesheet_id == timesheet.id)
                .order_by(TimesheetAuditEvent.id.asc())
                .all()
            )

        self.assertEqual([event.action for event in events], ["create", "update", "submit", "approve", "lock"])
        self.assertEqual(events[0].status_to.value, "draft")
        self.assertEqual(events[2].status_from.value, "draft")
        self.assertEqual(events[2].status_to.value, "submitted")
        self.assertEqual(events[-1].status_to.value, "locked")

    def test_payroll_run_behavior_unchanged_by_timesheet_models(self):
        from app.services.nz_payroll import calculate_period_gross

        with self.Session() as db:
            employee = self._employee(db, pay_type="hourly", pay_rate=Decimal("30.00"))
            gross = calculate_period_gross(employee, Decimal("40.00"))

        self.assertEqual(gross, Decimal("1200.00"))


if __name__ == "__main__":
    unittest.main()
