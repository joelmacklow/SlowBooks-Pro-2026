import os
import sys
import types
import unittest
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class TimesheetAdminRouteTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        master_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        company_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=master_engine)
        Base.metadata.create_all(bind=company_engine)
        self.MasterSession = sessionmaker(bind=master_engine)
        self.CompanySession = sessionmaker(bind=company_engine)

    def _bootstrap_owner(self, master_db):
        from app.routes.auth import bootstrap_admin
        from app.schemas.auth import BootstrapAdminRequest
        from app.services.auth import require_permissions

        owner = bootstrap_admin(
            BootstrapAdminRequest(
                email="owner@example.com",
                password="supersecret",
                full_name="Owner User",
            ),
            db=master_db,
        )
        return owner, require_permissions("users.manage")(db=master_db, authorization=f"Bearer {owner.token}")

    def _create_user(self, master_db, owner_auth, *, email, role_key="payroll_admin"):
        from app.routes.auth import create_user
        from app.schemas.auth import UserCreateRequest

        return create_user(
            UserCreateRequest(
                email=email,
                password="admin123",
                full_name=email.split("@", 1)[0].title(),
                role_key=role_key,
                allow_permissions=[],
                deny_permissions=[],
            ),
            db=master_db,
            auth=owner_auth,
        )

    def _login(self, master_db, email, password="admin123"):
        from app.routes.auth import login
        from app.schemas.auth import LoginRequest

        return login(LoginRequest(email=email, password=password), db=master_db)

    def _permission_auth(self, master_db, token: str, permission: str):
        from app.services.auth import require_permissions

        return require_permissions(permission)(db=master_db, authorization=f"Bearer {token}")

    def _create_employee(self, company_db, *, first_name="Aroha", last_name="Ngata", active=True):
        from app.models.payroll import Employee

        employee = Employee(
            first_name=first_name,
            last_name=last_name,
            ird_number="123456789",
            pay_type="hourly",
            pay_rate=Decimal("35.00"),
            tax_code="M",
            kiwisaver_enrolled=False,
            kiwisaver_rate=Decimal("0.0350"),
            student_loan=False,
            child_support=False,
            child_support_amount=Decimal("0.00"),
            esct_rate=Decimal("0.0000"),
            pay_frequency="weekly",
            is_active=active,
        )
        company_db.add(employee)
        company_db.commit()
        company_db.refresh(employee)
        return employee

    def _create_pay_run(self, company_db, *, period_start=date(2026, 4, 1), period_end=date(2026, 4, 7), pay_date=date(2026, 4, 8)):
        from app.models.payroll import PayRun, PayRunStatus

        pay_run = PayRun(
            period_start=period_start,
            period_end=period_end,
            pay_date=pay_date,
            tax_year=2026,
            status=PayRunStatus.DRAFT,
        )
        company_db.add(pay_run)
        company_db.commit()
        company_db.refresh(pay_run)
        return pay_run

    def _create_timesheet(self, company_db, *, employee_id: int, hours: Decimal, work_date: date = date(2026, 4, 1)):
        from app.schemas.timesheets import TimesheetLineUpsert
        from app.services.timesheets import create_timesheet

        return create_timesheet(
            company_db,
            employee_id=employee_id,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 7),
            lines=[
                TimesheetLineUpsert(
                    work_date=work_date,
                    entry_mode="duration",
                    duration_hours=hours,
                    notes="=HYPERLINK('bad')",
                )
            ],
        )

    def _submitted_timesheet(self, company_db, *, employee_id: int, hours: Decimal = Decimal("8.00")):
        from app.services.timesheets import submit_timesheet

        timesheet = self._create_timesheet(company_db, employee_id=employee_id, hours=hours)
        return submit_timesheet(company_db, timesheet_id=timesheet.id, actor_user_id=1)

    def _approved_timesheet(self, company_db, *, employee_id: int, hours: Decimal = Decimal("8.00")):
        from app.services.timesheets import approve_timesheet, submit_timesheet

        timesheet = self._create_timesheet(company_db, employee_id=employee_id, hours=hours)
        submit_timesheet(company_db, timesheet_id=timesheet.id, actor_user_id=1)
        return approve_timesheet(company_db, timesheet_id=timesheet.id, actor_user_id=1)

    def _rejected_timesheet(self, company_db, *, employee_id: int, hours: Decimal = Decimal("8.00")):
        from app.services.timesheets import reject_timesheet, submit_timesheet

        timesheet = self._create_timesheet(company_db, employee_id=employee_id, hours=hours)
        submit_timesheet(company_db, timesheet_id=timesheet.id, actor_user_id=1)
        return reject_timesheet(company_db, timesheet_id=timesheet.id, reason="Missing sign-off", actor_user_id=1)

    def _locked_timesheet(self, company_db, *, employee_id: int, hours: Decimal = Decimal("8.00")):
        from app.services.timesheets import lock_timesheet

        timesheet = self._approved_timesheet(company_db, employee_id=employee_id, hours=hours)
        return lock_timesheet(company_db, timesheet_id=timesheet.id, actor_user_id=1)

    def test_admin_can_list_period_readiness_grouped_by_status(self):
        from app.routes.timesheets import get_timesheet_period_readiness

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            admin_user = self._create_user(master_db, owner_auth, email="admin@example.com", role_key="payroll_admin")
            admin_login = self._login(master_db, admin_user.email)
            admin_auth = self._permission_auth(master_db, admin_login.token, "timesheets.manage")

            draft_employee = self._create_employee(company_db, first_name="Draft")
            submitted_employee = self._create_employee(company_db, first_name="Submitted")
            approved_employee = self._create_employee(company_db, first_name="Approved")
            rejected_employee = self._create_employee(company_db, first_name="Rejected")
            locked_employee = self._create_employee(company_db, first_name="Locked")

            draft = self._create_timesheet(company_db, employee_id=draft_employee.id, hours=Decimal("7.50"))
            submitted = self._submitted_timesheet(company_db, employee_id=submitted_employee.id, hours=Decimal("8.00"))
            approved = self._approved_timesheet(company_db, employee_id=approved_employee.id, hours=Decimal("8.25"))
            rejected = self._rejected_timesheet(company_db, employee_id=rejected_employee.id, hours=Decimal("6.50"))
            locked = self._locked_timesheet(company_db, employee_id=locked_employee.id, hours=Decimal("5.00"))

            response = get_timesheet_period_readiness(
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 7),
                db=company_db,
                auth=admin_auth,
            )

        self.assertEqual(response.period_start, date(2026, 4, 1))
        self.assertEqual(response.period_end, date(2026, 4, 7))
        self.assertEqual([row.id for row in response.draft], [draft.id])
        self.assertEqual([row.id for row in response.submitted], [submitted.id])
        self.assertEqual([row.id for row in response.approved], [approved.id])
        self.assertEqual([row.id for row in response.rejected], [rejected.id])
        self.assertEqual([row.id for row in response.locked], [locked.id])

    def test_admin_can_list_pay_run_readiness_grouped_by_status(self):
        from app.routes.timesheets import get_timesheet_pay_run_readiness

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            admin_user = self._create_user(master_db, owner_auth, email="admin@example.com", role_key="payroll_admin")
            admin_login = self._login(master_db, admin_user.email)
            admin_auth = self._permission_auth(master_db, admin_login.token, "timesheets.manage")

            draft_employee = self._create_employee(company_db, first_name="Draft")
            submitted_employee = self._create_employee(company_db, first_name="Submitted")
            approved_employee = self._create_employee(company_db, first_name="Approved")
            self._create_timesheet(company_db, employee_id=draft_employee.id, hours=Decimal("7.50"))
            submitted = self._submitted_timesheet(company_db, employee_id=submitted_employee.id, hours=Decimal("8.00"))
            approved = self._approved_timesheet(company_db, employee_id=approved_employee.id, hours=Decimal("8.25"))
            pay_run = self._create_pay_run(company_db)

            response = get_timesheet_pay_run_readiness(pay_run.id, db=company_db, auth=admin_auth)

        self.assertEqual(response.pay_run_id, pay_run.id)
        self.assertEqual([row.id for row in response.submitted], [submitted.id])
        self.assertEqual([row.id for row in response.approved], [approved.id])
        self.assertEqual(len(response.draft), 1)

    def test_admin_can_view_timesheet_detail_and_audit(self):
        from app.routes.timesheets import get_timesheet, get_timesheet_audit

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            admin_user = self._create_user(master_db, owner_auth, email="admin@example.com", role_key="payroll_admin")
            admin_login = self._login(master_db, admin_user.email)
            admin_auth = self._permission_auth(master_db, admin_login.token, "timesheets.manage")

            employee = self._create_employee(company_db)
            submitted = self._submitted_timesheet(company_db, employee_id=employee.id, hours=Decimal("7.75"))

            detail = get_timesheet(submitted.id, db=company_db, auth=admin_auth)
            audit = get_timesheet_audit(submitted.id, db=company_db, auth=admin_auth)

        self.assertEqual(detail.id, submitted.id)
        self.assertEqual(detail.status, "submitted")
        self.assertGreaterEqual(len(detail.audit_events), 2)
        self.assertEqual([event.action for event in audit], ["create", "submit"])

    def test_admin_can_correct_submitted_timesheet_with_reason(self):
        from app.models.timesheets import TimesheetAuditEvent
        from app.routes.timesheets import correct_timesheet_route
        from app.schemas.timesheets import TimesheetCorrectionRequest

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            admin_user = self._create_user(master_db, owner_auth, email="admin@example.com", role_key="payroll_admin")
            admin_login = self._login(master_db, admin_user.email)
            admin_auth = self._permission_auth(master_db, admin_login.token, "timesheets.manage")

            employee = self._create_employee(company_db)
            submitted = self._submitted_timesheet(company_db, employee_id=employee.id, hours=Decimal("7.75"))

            corrected = correct_timesheet_route(
                submitted.id,
                TimesheetCorrectionRequest(
                    lines=[
                        {"work_date": date(2026, 4, 1), "entry_mode": "duration", "duration_hours": Decimal("8.50")}
                    ],
                    reason="Adjusted to match supervisor sign-off",
                ),
                db=company_db,
                auth=admin_auth,
            )
            events = (
                company_db.query(TimesheetAuditEvent)
                .filter(TimesheetAuditEvent.timesheet_id == submitted.id)
                .order_by(TimesheetAuditEvent.id.asc())
                .all()
            )

        self.assertEqual(corrected.status, "submitted")
        self.assertEqual(Decimal(str(corrected.total_hours)), Decimal("8.50"))
        self.assertEqual(corrected.audit_events[-1].action, "correct")
        self.assertEqual(corrected.audit_events[-1].reason, "Adjusted to match supervisor sign-off")
        self.assertEqual(events[-1].action, "correct")

    def test_admin_can_approve_reject_and_bulk_approve(self):
        from app.routes.timesheets import approve_timesheet_route, bulk_approve_timesheets_route, reject_timesheet_route
        from app.schemas.timesheets import TimesheetBulkApproveRequest, TimesheetStatusActionRequest

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            admin_user = self._create_user(master_db, owner_auth, email="admin@example.com", role_key="payroll_admin")
            admin_login = self._login(master_db, admin_user.email)
            admin_auth = self._permission_auth(master_db, admin_login.token, "timesheets.approve")

            approve_employee = self._create_employee(company_db, first_name="Approve")
            reject_employee = self._create_employee(company_db, first_name="Reject")
            bulk_employee_1 = self._create_employee(company_db, first_name="Bulk1")
            bulk_employee_2 = self._create_employee(company_db, first_name="Bulk2")

            approve_target = self._submitted_timesheet(company_db, employee_id=approve_employee.id, hours=Decimal("8.00"))
            reject_target = self._submitted_timesheet(company_db, employee_id=reject_employee.id, hours=Decimal("6.75"))
            bulk_one = self._submitted_timesheet(company_db, employee_id=bulk_employee_1.id, hours=Decimal("7.00"))
            bulk_two = self._submitted_timesheet(company_db, employee_id=bulk_employee_2.id, hours=Decimal("7.25"))

            approved = approve_timesheet_route(approve_target.id, db=company_db, auth=admin_auth)
            rejected = reject_timesheet_route(
                reject_target.id,
                TimesheetStatusActionRequest(reason="Incorrect period"),
                db=company_db,
                auth=admin_auth,
            )
            bulk_approved = bulk_approve_timesheets_route(
                TimesheetBulkApproveRequest(timesheet_ids=[bulk_one.id, bulk_two.id]),
                db=company_db,
                auth=admin_auth,
            )

        self.assertEqual(approved.status, "approved")
        self.assertEqual(rejected.status, "rejected")
        self.assertEqual(rejected.audit_events[-1].reason, "Incorrect period")
        self.assertEqual([row.status for row in bulk_approved], ["approved", "approved"])
        self.assertEqual([row.id for row in bulk_approved], [bulk_one.id, bulk_two.id])

    def test_admin_cannot_approve_locked_or_unsubmitted_timesheets(self):
        from app.routes.timesheets import approve_timesheet_route, bulk_approve_timesheets_route
        from app.schemas.timesheets import TimesheetBulkApproveRequest

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            admin_user = self._create_user(master_db, owner_auth, email="admin@example.com", role_key="payroll_admin")
            admin_login = self._login(master_db, admin_user.email)
            admin_auth = self._permission_auth(master_db, admin_login.token, "timesheets.approve")

            draft_employee = self._create_employee(company_db)
            locked_employee = self._create_employee(company_db, first_name="Locked")
            draft = self._create_timesheet(company_db, employee_id=draft_employee.id, hours=Decimal("8.00"))
            locked = self._locked_timesheet(company_db, employee_id=locked_employee.id, hours=Decimal("6.00"))

            with self.assertRaises(HTTPException) as approval_ctx:
                approve_timesheet_route(draft.id, db=company_db, auth=admin_auth)
            with self.assertRaises(HTTPException) as bulk_ctx:
                bulk_approve_timesheets_route(
                    TimesheetBulkApproveRequest(timesheet_ids=[locked.id]),
                    db=company_db,
                    auth=admin_auth,
                )

        self.assertEqual(approval_ctx.exception.status_code, 400)
        self.assertEqual(bulk_ctx.exception.status_code, 400)
        self.assertIn("submitted", bulk_ctx.exception.detail.lower())

    def test_viewer_role_cannot_approve_or_export_without_permission(self):
        from app.routes.auth import create_user
        from app.schemas.auth import UserCreateRequest
        from app.services.auth import require_permissions

        with self.MasterSession() as master_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            viewer = create_user(
                UserCreateRequest(
                    email="viewer@example.com",
                    password="viewer123",
                    full_name="Viewer User",
                    role_key="payroll_viewer",
                    allow_permissions=[],
                    deny_permissions=[],
                ),
                db=master_db,
                auth=owner_auth,
            )
            viewer_login = self._login(master_db, viewer.email, password="viewer123")

            with self.assertRaises(HTTPException) as approve_ctx:
                require_permissions("timesheets.approve")(db=master_db, authorization=f"Bearer {viewer_login.token}")
            with self.assertRaises(HTTPException) as export_ctx:
                require_permissions("timesheets.export")(db=master_db, authorization=f"Bearer {viewer_login.token}")

        self.assertEqual(approve_ctx.exception.status_code, 403)
        self.assertEqual(export_ctx.exception.status_code, 403)

    def test_admin_csv_export_is_scoped_and_filename_safe(self):
        from app.routes.timesheets import export_timesheets_csv_route

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            admin_user = self._create_user(master_db, owner_auth, email="admin@example.com", role_key="payroll_admin")
            admin_login = self._login(master_db, admin_user.email)
            admin_auth = self._permission_auth(master_db, admin_login.token, "timesheets.export")

            employee = self._create_employee(company_db)
            other_employee = self._create_employee(company_db, first_name="Other")
            submitted = self._submitted_timesheet(company_db, employee_id=employee.id, hours=Decimal("8.25"))
            self._create_timesheet(company_db, employee_id=other_employee.id, hours=Decimal("7.00"), work_date=date(2026, 4, 2))

            response = export_timesheets_csv_route(
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 7),
                status="submitted",
                db=company_db,
                auth=admin_auth,
            )
            csv_body = response.body.decode()

        self.assertEqual(response.media_type, "text/csv")
        self.assertEqual(
            response.headers["Content-Disposition"],
            'attachment; filename="Timesheets_2026-04-01_2026-04-07_submitted.csv"',
        )
        self.assertIn("timesheet_id,employee_id,period_start,period_end,status,work_date,entry_mode,duration_hours,start_time,end_time,break_minutes", csv_body)
        self.assertIn(str(submitted.id), csv_body)
        self.assertNotIn("ird_number", csv_body)
        self.assertNotIn("pay_rate", csv_body)
        self.assertNotIn("HYPERLINK", csv_body)


if __name__ == "__main__":
    unittest.main()
