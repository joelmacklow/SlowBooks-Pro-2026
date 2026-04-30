import os
import sys
import types
import unittest
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class TimesheetSelfServiceRouteTests(unittest.TestCase):
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

    def _create_user(self, master_db, owner_auth, *, email, role_key="employee_self_service"):
        from app.routes.auth import create_user
        from app.schemas.auth import UserCreateRequest

        return create_user(
            UserCreateRequest(
                email=email,
                password="employee123",
                full_name=email.split("@", 1)[0].title(),
                role_key=role_key,
                allow_permissions=[],
                deny_permissions=[],
            ),
            db=master_db,
            auth=owner_auth,
        )

    def _login(self, master_db, email):
        from app.routes.auth import login
        from app.schemas.auth import LoginRequest

        return login(LoginRequest(email=email, password="employee123"), db=master_db)

    def _permission_auth(self, master_db, token: str, permission: str):
        from app.services.auth import require_permissions

        return require_permissions(permission)(db=master_db, authorization=f"Bearer {token}")

    def _link_employee(self, master_db, company_db, owner_auth, *, user_id: int, employee_id: int):
        from app.routes.employee_portal import create_link
        from app.schemas.employee_portal import EmployeePortalLinkCreateRequest

        return create_link(
            EmployeePortalLinkCreateRequest(user_id=user_id, employee_id=employee_id),
            db=company_db,
            master_db=master_db,
            auth=owner_auth,
        )

    def _create_draft_timesheet(self, company_db, *, employee_id: int):
        from app.schemas.timesheets import TimesheetLineUpsert
        from app.services.timesheets import create_timesheet

        return create_timesheet(
            company_db,
            employee_id=employee_id,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 7),
            lines=[TimesheetLineUpsert(work_date=date(2026, 4, 1), entry_mode="duration", duration_hours=Decimal("8.00"))],
        )

    def test_employee_can_create_own_draft_timesheet_without_employee_id(self):
        from app.models.timesheets import TimesheetAuditEvent
        from app.routes.timesheets import create_self_timesheet
        from app.schemas.timesheets import TimesheetSelfCreateRequest

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            employee_user = self._create_user(master_db, owner_auth, email="employee@example.com")
            employee = self._create_employee(company_db)
            employee_id = employee.id
            self._link_employee(master_db, company_db, owner_auth, user_id=employee_user.id, employee_id=employee.id)
            login = self._login(master_db, employee_user.email)
            self_auth = self._permission_auth(master_db, login.token, "timesheets.self.create")

            created = create_self_timesheet(
                TimesheetSelfCreateRequest(
                    period_start=date(2026, 4, 1),
                    period_end=date(2026, 4, 7),
                    lines=[{"work_date": date(2026, 4, 1), "entry_mode": "duration", "duration_hours": Decimal("7.50")}],
                ),
                db=company_db,
                master_db=master_db,
                auth=self_auth,
            )
            events = (
                company_db.query(TimesheetAuditEvent)
                .filter(TimesheetAuditEvent.timesheet_id == created.id)
                .order_by(TimesheetAuditEvent.id.asc())
                .all()
            )

        self.assertEqual(created.employee_id, employee_id)
        self.assertEqual(created.status, "draft")
        self.assertEqual(Decimal(str(created.total_hours)), Decimal("7.50"))
        self.assertEqual(events[-1].action, "create")
        self.assertEqual(events[-1].actor_user_id, self_auth.user.id)
        self.assertNotIn("tax_code", created.model_dump())
        self.assertNotIn("pay_rate", created.model_dump())

    def test_self_list_returns_only_linked_employee_timesheets(self):
        from app.routes.timesheets import list_self_timesheets

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            employee_user = self._create_user(master_db, owner_auth, email="employee@example.com")
            linked_employee = self._create_employee(company_db, first_name="Linked")
            other_employee = self._create_employee(company_db, first_name="Other")
            self._link_employee(master_db, company_db, owner_auth, user_id=employee_user.id, employee_id=linked_employee.id)
            own = self._create_draft_timesheet(company_db, employee_id=linked_employee.id)
            self._create_draft_timesheet(company_db, employee_id=other_employee.id)
            login = self._login(master_db, employee_user.email)
            self_auth = self._permission_auth(master_db, login.token, "timesheets.self.view")

            listed = list_self_timesheets(db=company_db, master_db=master_db, auth=self_auth)

        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0].id, own.id)
        self.assertEqual(listed[0].employee_id, linked_employee.id)

    def test_self_detail_denies_other_employee_timesheet(self):
        from app.routes.timesheets import get_self_timesheet

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            employee_user = self._create_user(master_db, owner_auth, email="employee@example.com")
            linked_employee = self._create_employee(company_db, first_name="Linked")
            other_employee = self._create_employee(company_db, first_name="Other")
            self._link_employee(master_db, company_db, owner_auth, user_id=employee_user.id, employee_id=linked_employee.id)
            foreign = self._create_draft_timesheet(company_db, employee_id=other_employee.id)
            login = self._login(master_db, employee_user.email)
            self_auth = self._permission_auth(master_db, login.token, "timesheets.self.view")

            with self.assertRaises(HTTPException) as ctx:
                get_self_timesheet(foreign.id, db=company_db, master_db=master_db, auth=self_auth)

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.detail.lower())

    def test_self_create_rejects_spoofed_employee_id(self):
        from app.schemas.timesheets import TimesheetSelfCreateRequest

        with self.assertRaises(ValidationError):
            TimesheetSelfCreateRequest.model_validate({
                "employee_id": 999,
                "period_start": date(2026, 4, 1),
                "period_end": date(2026, 4, 7),
                "lines": [{"work_date": date(2026, 4, 1), "entry_mode": "duration", "duration_hours": "8.00"}],
            })

    def test_self_update_own_draft_replaces_lines_and_audits(self):
        from app.models.timesheets import TimesheetAuditEvent
        from app.routes.timesheets import update_self_timesheet
        from app.schemas.timesheets import TimesheetUpdateRequest

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            employee_user = self._create_user(master_db, owner_auth, email="employee@example.com")
            employee = self._create_employee(company_db)
            self._link_employee(master_db, company_db, owner_auth, user_id=employee_user.id, employee_id=employee.id)
            own = self._create_draft_timesheet(company_db, employee_id=employee.id)
            login = self._login(master_db, employee_user.email)
            self_auth = self._permission_auth(master_db, login.token, "timesheets.self.create")

            updated = update_self_timesheet(
                own.id,
                TimesheetUpdateRequest(
                    lines=[
                        {"work_date": date(2026, 4, 2), "entry_mode": "duration", "duration_hours": Decimal("6.00")},
                        {"work_date": date(2026, 4, 3), "entry_mode": "duration", "duration_hours": Decimal("2.50")},
                    ]
                ),
                db=company_db,
                master_db=master_db,
                auth=self_auth,
            )
            events = (
                company_db.query(TimesheetAuditEvent)
                .filter(TimesheetAuditEvent.timesheet_id == own.id)
                .order_by(TimesheetAuditEvent.id.asc())
                .all()
            )

        self.assertEqual(Decimal(str(updated.total_hours)), Decimal("8.50"))
        self.assertEqual(events[-1].action, "update")
        self.assertEqual(events[-1].actor_user_id, self_auth.user.id)

    def test_self_update_denies_other_employee_even_if_draft(self):
        from app.routes.timesheets import update_self_timesheet
        from app.schemas.timesheets import TimesheetUpdateRequest

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            employee_user = self._create_user(master_db, owner_auth, email="employee@example.com")
            linked_employee = self._create_employee(company_db)
            other_employee = self._create_employee(company_db, first_name="Other")
            self._link_employee(master_db, company_db, owner_auth, user_id=employee_user.id, employee_id=linked_employee.id)
            foreign = self._create_draft_timesheet(company_db, employee_id=other_employee.id)
            login = self._login(master_db, employee_user.email)
            self_auth = self._permission_auth(master_db, login.token, "timesheets.self.create")

            with self.assertRaises(HTTPException) as ctx:
                update_self_timesheet(
                    foreign.id,
                    TimesheetUpdateRequest(lines=[{"work_date": date(2026, 4, 2), "entry_mode": "duration", "duration_hours": Decimal("3.00")}]),
                    db=company_db,
                    master_db=master_db,
                    auth=self_auth,
                )

        self.assertEqual(ctx.exception.status_code, 404)

    def test_self_submit_own_draft_records_actor(self):
        from app.models.timesheets import TimesheetAuditEvent
        from app.routes.timesheets import submit_self_timesheet

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            employee_user = self._create_user(master_db, owner_auth, email="employee@example.com")
            employee = self._create_employee(company_db)
            self._link_employee(master_db, company_db, owner_auth, user_id=employee_user.id, employee_id=employee.id)
            own = self._create_draft_timesheet(company_db, employee_id=employee.id)
            login = self._login(master_db, employee_user.email)
            self_auth = self._permission_auth(master_db, login.token, "timesheets.self.submit")

            submitted = submit_self_timesheet(own.id, db=company_db, master_db=master_db, auth=self_auth)
            events = (
                company_db.query(TimesheetAuditEvent)
                .filter(TimesheetAuditEvent.timesheet_id == own.id)
                .order_by(TimesheetAuditEvent.id.asc())
                .all()
            )

        self.assertEqual(submitted.status, "submitted")
        self.assertIsNotNone(submitted.submitted_at)
        self.assertEqual(events[-1].action, "submit")
        self.assertEqual(events[-1].actor_user_id, self_auth.user.id)

    def test_self_cannot_edit_submitted_approved_or_locked_timesheet(self):
        from app.routes.timesheets import submit_self_timesheet, update_self_timesheet
        from app.schemas.timesheets import TimesheetUpdateRequest
        from app.services.timesheets import approve_timesheet, lock_timesheet

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            employee_user = self._create_user(master_db, owner_auth, email="employee@example.com")
            employee = self._create_employee(company_db)
            self._link_employee(master_db, company_db, owner_auth, user_id=employee_user.id, employee_id=employee.id)
            own = self._create_draft_timesheet(company_db, employee_id=employee.id)
            login = self._login(master_db, employee_user.email)
            submit_auth = self._permission_auth(master_db, login.token, "timesheets.self.submit")
            update_auth = self._permission_auth(master_db, login.token, "timesheets.self.create")

            submit_self_timesheet(own.id, db=company_db, master_db=master_db, auth=submit_auth)
            with self.assertRaises(HTTPException) as submitted_ctx:
                update_self_timesheet(
                    own.id,
                    TimesheetUpdateRequest(lines=[{"work_date": date(2026, 4, 2), "entry_mode": "duration", "duration_hours": Decimal("8.00")}]),
                    db=company_db,
                    master_db=master_db,
                    auth=update_auth,
                )
            approve_timesheet(company_db, timesheet_id=own.id, actor_user_id=owner_auth.user.id)
            with self.assertRaises(HTTPException):
                update_self_timesheet(
                    own.id,
                    TimesheetUpdateRequest(lines=[{"work_date": date(2026, 4, 3), "entry_mode": "duration", "duration_hours": Decimal("8.00")}]),
                    db=company_db,
                    master_db=master_db,
                    auth=update_auth,
                )
            lock_timesheet(company_db, timesheet_id=own.id, actor_user_id=owner_auth.user.id)
            with self.assertRaises(HTTPException):
                update_self_timesheet(
                    own.id,
                    TimesheetUpdateRequest(lines=[{"work_date": date(2026, 4, 4), "entry_mode": "duration", "duration_hours": Decimal("8.00")}]),
                    db=company_db,
                    master_db=master_db,
                    auth=update_auth,
                )

        self.assertEqual(submitted_ctx.exception.status_code, 400)
        self.assertIn("draft or rejected", submitted_ctx.exception.detail.lower())

    def test_self_missing_or_inactive_link_is_rejected(self):
        from app.routes.employee_portal import deactivate_link
        from app.routes.timesheets import list_self_timesheets

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            user = self._create_user(master_db, owner_auth, email="employee@example.com")
            employee = self._create_employee(company_db)
            link = self._link_employee(master_db, company_db, owner_auth, user_id=user.id, employee_id=employee.id)
            login = self._login(master_db, user.email)
            self_auth = self._permission_auth(master_db, login.token, "timesheets.self.view")

            deactivate_link(link.id, db=company_db, master_db=master_db, auth=owner_auth)
            with self.assertRaises(HTTPException) as inactive_ctx:
                list_self_timesheets(db=company_db, master_db=master_db, auth=self_auth)

            user2 = self._create_user(master_db, owner_auth, email="employee2@example.com")
            login2 = self._login(master_db, user2.email)
            self_auth2 = self._permission_auth(master_db, login2.token, "timesheets.self.view")
            with self.assertRaises(HTTPException) as missing_ctx:
                list_self_timesheets(db=company_db, master_db=master_db, auth=self_auth2)

        self.assertEqual(inactive_ctx.exception.status_code, 404)
        self.assertEqual(missing_ctx.exception.status_code, 404)

    def test_self_wrong_permission_cannot_create_or_submit(self):
        from app.services.auth import require_permissions

        with self.MasterSession() as master_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            viewer = self._create_user(master_db, owner_auth, email="viewer@example.com", role_key="payroll_viewer")
            viewer_login = self._login(master_db, viewer.email)

            with self.assertRaises(HTTPException) as create_ctx:
                require_permissions("timesheets.self.create")(db=master_db, authorization=f"Bearer {viewer_login.token}")
            with self.assertRaises(HTTPException) as submit_ctx:
                require_permissions("timesheets.self.submit")(db=master_db, authorization=f"Bearer {viewer_login.token}")

        self.assertEqual(create_ctx.exception.status_code, 403)
        self.assertEqual(submit_ctx.exception.status_code, 403)

    def test_self_csv_export_is_owned_and_safe(self):
        from app.routes.timesheets import export_self_timesheet_csv
        from app.schemas.timesheets import TimesheetLineUpsert
        from app.services.timesheets import create_timesheet

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            user = self._create_user(master_db, owner_auth, email="employee@example.com")
            employee = self._create_employee(company_db)
            self._link_employee(master_db, company_db, owner_auth, user_id=user.id, employee_id=employee.id)
            timesheet = create_timesheet(
                company_db,
                employee_id=employee.id,
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 7),
                lines=[
                    TimesheetLineUpsert(
                        work_date=date(2026, 4, 1),
                        entry_mode="duration",
                        duration_hours=Decimal("8.25"),
                        notes="=HYPERLINK('bad')",
                    )
                ],
            )
            login = self._login(master_db, user.email)
            self_auth = self._permission_auth(master_db, login.token, "timesheets.self.view")

            response = export_self_timesheet_csv(timesheet.id, db=company_db, master_db=master_db, auth=self_auth)

        self.assertEqual(response.media_type, "text/csv")
        self.assertIn("attachment;", response.headers["Content-Disposition"])
        self.assertIn(f"Timesheet_{timesheet.id}_", response.headers["Content-Disposition"])
        csv_body = response.body.decode()
        self.assertIn("timesheet_id,period_start,period_end,status,work_date,entry_mode,duration_hours,start_time,end_time,break_minutes", csv_body)
        self.assertIn("8.25", csv_body)
        self.assertNotIn("ird_number", csv_body)
        self.assertNotIn("tax_code", csv_body)
        self.assertNotIn("HYPERLINK", csv_body)

    def test_self_csv_export_denies_other_employee_timesheet(self):
        from app.routes.timesheets import export_self_timesheet_csv

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            user = self._create_user(master_db, owner_auth, email="employee@example.com")
            linked_employee = self._create_employee(company_db, first_name="Linked")
            other_employee = self._create_employee(company_db, first_name="Other")
            self._link_employee(master_db, company_db, owner_auth, user_id=user.id, employee_id=linked_employee.id)
            foreign = self._create_draft_timesheet(company_db, employee_id=other_employee.id)
            login = self._login(master_db, user.email)
            self_auth = self._permission_auth(master_db, login.token, "timesheets.self.view")

            with self.assertRaises(HTTPException) as ctx:
                export_self_timesheet_csv(foreign.id, db=company_db, master_db=master_db, auth=self_auth)

        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
