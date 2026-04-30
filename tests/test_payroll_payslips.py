import os
import sys
import types
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class PayrollPayslipRouteTests(unittest.TestCase):
    def setUp(self):
        from app.models.accounts import Account  # noqa: F401
        from app.models.payroll import Employee, PayRun, PayStub  # noqa: F401
        from app.models.settings import Settings  # noqa: F401
        from app.models.transactions import Transaction  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def _create_employee(self, db, **overrides):
        from app.routes.employees import create_employee
        from app.schemas.payroll import EmployeeCreate

        data = {
            "first_name": "Aroha",
            "last_name": "Ngata",
            "pay_type": "salary",
            "pay_rate": 78000,
            "tax_code": "M",
            "kiwisaver_enrolled": True,
            "kiwisaver_rate": "0.0350",
            "student_loan": False,
            "child_support": False,
            "child_support_amount": "0.00",
            "esct_rate": "0.1750",
            "pay_frequency": "fortnightly",
            "start_date": date(2026, 4, 1),
        }
        data.update(overrides)
        return create_employee(EmployeeCreate(**data), db=db)

    def _seed_company(self, db):
        from app.models.settings import Settings

        db.add_all([
            Settings(key="company_name", value="SlowBooks NZ"),
            Settings(key="company_address1", value="123 Harbour Street"),
            Settings(key="company_city", value="Auckland"),
            Settings(key="company_state", value="Auckland"),
            Settings(key="company_zip", value="1010"),
            Settings(key="ird_number", value="123-456-789"),
        ])
        db.commit()

    def _processed_run(self, db):
        from app.routes.payroll import create_pay_run, process_pay_run
        from app.schemas.payroll import PayRunCreate, PayStubInput

        employee = self._create_employee(db)
        draft = create_pay_run(PayRunCreate(
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 14),
            pay_date=date(2026, 4, 15),
            stubs=[PayStubInput(employee_id=employee.id)],
        ), db=db)
        processed = process_pay_run(draft.id, db=db)
        return employee, processed

    @staticmethod
    def _fake_payslip_pdf(pay_run, stub, employee, company_settings):
        return (
            f"Payslip\n"
            f"{employee.first_name} {employee.last_name}\n"
            f"{pay_run.pay_date.strftime('%d %b %Y')}\n"
            f"PAYE\n"
            f"Net Pay\n"
        ).encode("utf-8")

    def test_processed_pay_run_returns_payslip_pdf(self):
        from app.routes.payroll import payroll_payslip_pdf

        with self.Session() as db:
            self._seed_company(db)
            employee, processed = self._processed_run(db)
            with patch("app.routes.payroll.generate_payroll_payslip_pdf", side_effect=self._fake_payslip_pdf):
                response = payroll_payslip_pdf(processed.id, employee.id, db=db)

        self.assertEqual(response.media_type, "application/pdf")
        self.assertIn(f"PaySlip_{processed.id}_{employee.id}.pdf", response.headers["Content-Disposition"])
        body = response.body.decode()
        self.assertIn("Payslip", body)
        self.assertIn("Aroha Ngata", body)
        self.assertIn("15 Apr 2026", body)
        self.assertIn("PAYE", body)
        self.assertIn("Net Pay", body)

    def test_draft_pay_run_payslip_is_rejected(self):
        from fastapi import HTTPException

        from app.routes.payroll import create_pay_run, payroll_payslip_pdf
        from app.schemas.payroll import PayRunCreate, PayStubInput

        with self.Session() as db:
            self._seed_company(db)
            employee = self._create_employee(db)
            draft = create_pay_run(PayRunCreate(
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 14),
                pay_date=date(2026, 4, 15),
                stubs=[PayStubInput(employee_id=employee.id)],
            ), db=db)
            with self.assertRaises(HTTPException) as ctx:
                with patch("app.routes.payroll.generate_payroll_payslip_pdf", side_effect=self._fake_payslip_pdf):
                    payroll_payslip_pdf(draft.id, employee.id, db=db)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("processed", ctx.exception.detail.lower())

    def test_employee_not_in_run_is_rejected(self):
        from fastapi import HTTPException

        from app.routes.payroll import payroll_payslip_pdf

        with self.Session() as db:
            self._seed_company(db)
            employee, processed = self._processed_run(db)
            outsider = self._create_employee(db, first_name="Wiremu", last_name="Kingi", pay_type="hourly", pay_rate=30)
            with self.assertRaises(HTTPException) as ctx:
                with patch("app.routes.payroll.generate_payroll_payslip_pdf", side_effect=self._fake_payslip_pdf):
                    payroll_payslip_pdf(processed.id, outsider.id, db=db)

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.detail.lower())


class PayrollSelfPayslipRouteTests(unittest.TestCase):
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

    def _seed_company(self, db):
        from app.models.settings import Settings

        db.add_all([
            Settings(key="company_name", value="SlowBooks NZ"),
            Settings(key="company_address1", value="123 Harbour Street"),
            Settings(key="company_city", value="Auckland"),
            Settings(key="company_state", value="Auckland"),
            Settings(key="company_zip", value="1010"),
            Settings(key="ird_number", value="123-456-789"),
        ])
        db.commit()

    def _bootstrap_owner(self, master_db):
        from app.routes.auth import bootstrap_admin
        from app.schemas.auth import BootstrapAdminRequest
        from app.services.auth import require_permissions

        owner = bootstrap_admin(
            BootstrapAdminRequest(email="owner@example.com", password="supersecret", full_name="Owner User"),
            db=master_db,
        )
        auth = require_permissions("users.manage")(db=master_db, authorization=f"Bearer {owner.token}")
        return owner, auth

    def _create_employee(self, db, **overrides):
        from app.routes.employees import create_employee
        from app.schemas.payroll import EmployeeCreate

        data = {
            "first_name": "Aroha",
            "last_name": "Ngata",
            "pay_type": "salary",
            "pay_rate": 78000,
            "tax_code": "M",
            "kiwisaver_enrolled": True,
            "kiwisaver_rate": "0.0350",
            "student_loan": False,
            "child_support": False,
            "child_support_amount": "0.00",
            "esct_rate": "0.1750",
            "pay_frequency": "fortnightly",
            "start_date": date(2026, 4, 1),
        }
        data.update(overrides)
        return create_employee(EmployeeCreate(**data), db=db)

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

    def _build_runs_with_two_employees(self, db):
        from app.routes.payroll import create_pay_run, process_pay_run
        from app.schemas.payroll import PayRunCreate, PayStubInput

        employee_a = self._create_employee(db, first_name="Aroha", last_name="Ngata")
        employee_b = self._create_employee(db, first_name="Wiremu", last_name="Kingi", pay_type="hourly", pay_rate=30)

        run_ab = create_pay_run(PayRunCreate(
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 14),
            pay_date=date(2026, 4, 15),
            stubs=[PayStubInput(employee_id=employee_a.id), PayStubInput(employee_id=employee_b.id, hours=40)],
        ), db=db)
        processed_ab = process_pay_run(run_ab.id, db=db)

        run_b_only = create_pay_run(PayRunCreate(
            period_start=date(2026, 4, 15),
            period_end=date(2026, 4, 28),
            pay_date=date(2026, 4, 29),
            stubs=[PayStubInput(employee_id=employee_b.id, hours=40)],
        ), db=db)
        processed_b_only = process_pay_run(run_b_only.id, db=db)
        return employee_a, employee_b, processed_ab, processed_b_only

    @staticmethod
    def _fake_payslip_pdf(pay_run, stub, employee, company_settings):
        return (
            f"Payslip\n{employee.first_name} {employee.last_name}\n{pay_run.pay_date.strftime('%d %b %Y')}\nPAYE\nNet Pay\n"
        ).encode("utf-8")

    def test_employee_can_list_own_processed_payslips(self):
        from app.routes.payroll import list_self_payslips

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            self._seed_company(company_db)
            _owner, owner_auth = self._bootstrap_owner(master_db)
            user = self._create_user(master_db, owner_auth, email="employee@example.com")
            employee_a, employee_b, processed_ab, processed_b_only = self._build_runs_with_two_employees(company_db)
            self._link_employee(master_db, company_db, owner_auth, user_id=user.id, employee_id=employee_a.id)
            login = self._login(master_db, user.email)
            self_auth = self._permission_auth(master_db, login.token, "payroll.self.payslips.view")

            rows = list_self_payslips(db=company_db, master_db=master_db, auth=self_auth)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].pay_run_id, processed_ab.id)
        self.assertNotEqual(rows[0].pay_run_id, processed_b_only.id)
        self.assertTrue(rows[0].gross_pay >= 0)
        self.assertFalse(hasattr(rows[0], "tax_code"))
        self.assertFalse(hasattr(rows[0], "ird_number"))

    def test_employee_can_download_own_processed_payslip_pdf(self):
        from app.routes.payroll import self_payroll_payslip_pdf

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            self._seed_company(company_db)
            _owner, owner_auth = self._bootstrap_owner(master_db)
            user = self._create_user(master_db, owner_auth, email="employee@example.com")
            employee_a, _employee_b, processed_ab, _processed_b_only = self._build_runs_with_two_employees(company_db)
            self._link_employee(master_db, company_db, owner_auth, user_id=user.id, employee_id=employee_a.id)
            login = self._login(master_db, user.email)
            self_auth = self._permission_auth(master_db, login.token, "payroll.self.payslips.view")

            with patch("app.routes.payroll.generate_payroll_payslip_pdf", side_effect=self._fake_payslip_pdf):
                response = self_payroll_payslip_pdf(processed_ab.id, db=company_db, master_db=master_db, auth=self_auth)

        self.assertEqual(response.media_type, "application/pdf")
        self.assertIn("PaySlip_", response.headers["Content-Disposition"])
        body = response.body.decode()
        self.assertIn("Aroha Ngata", body)
        self.assertNotIn("Wiremu Kingi", body)

    def test_employee_cannot_download_other_employee_payslip(self):
        from app.routes.payroll import self_payroll_payslip_pdf

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            self._seed_company(company_db)
            _owner, owner_auth = self._bootstrap_owner(master_db)
            user = self._create_user(master_db, owner_auth, email="employee@example.com")
            employee_a, _employee_b, _processed_ab, processed_b_only = self._build_runs_with_two_employees(company_db)
            self._link_employee(master_db, company_db, owner_auth, user_id=user.id, employee_id=employee_a.id)
            login = self._login(master_db, user.email)
            self_auth = self._permission_auth(master_db, login.token, "payroll.self.payslips.view")

            with self.assertRaises(HTTPException) as ctx:
                with patch("app.routes.payroll.generate_payroll_payslip_pdf", side_effect=self._fake_payslip_pdf):
                    self_payroll_payslip_pdf(processed_b_only.id, db=company_db, master_db=master_db, auth=self_auth)

        self.assertEqual(ctx.exception.status_code, 404)

    def test_draft_pay_run_self_payslip_is_rejected(self):
        from app.routes.payroll import create_pay_run, self_payroll_payslip_pdf
        from app.schemas.payroll import PayRunCreate, PayStubInput

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            self._seed_company(company_db)
            _owner, owner_auth = self._bootstrap_owner(master_db)
            user = self._create_user(master_db, owner_auth, email="employee@example.com")
            employee = self._create_employee(company_db)
            self._link_employee(master_db, company_db, owner_auth, user_id=user.id, employee_id=employee.id)
            draft = create_pay_run(PayRunCreate(
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 14),
                pay_date=date(2026, 4, 15),
                stubs=[PayStubInput(employee_id=employee.id)],
            ), db=company_db)
            login = self._login(master_db, user.email)
            self_auth = self._permission_auth(master_db, login.token, "payroll.self.payslips.view")

            with self.assertRaises(HTTPException) as ctx:
                with patch("app.routes.payroll.generate_payroll_payslip_pdf", side_effect=self._fake_payslip_pdf):
                    self_payroll_payslip_pdf(draft.id, db=company_db, master_db=master_db, auth=self_auth)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("processed", ctx.exception.detail.lower())

    def test_broad_admin_payslip_route_still_requires_admin_permission(self):
        from app.services.auth import require_permissions

        with self.MasterSession() as master_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            user = self._create_user(master_db, owner_auth, email="employee@example.com", role_key="employee_self_service")
            login = self._login(master_db, user.email)

            with self.assertRaises(HTTPException) as admin_ctx:
                require_permissions("payroll.payslips.view")(db=master_db, authorization=f"Bearer {login.token}")
            self_auth = require_permissions("payroll.self.payslips.view")(db=master_db, authorization=f"Bearer {login.token}")

        self.assertEqual(admin_ctx.exception.status_code, 403)
        self.assertIn("payroll.self.payslips.view", self_auth.permissions)


if __name__ == "__main__":
    unittest.main()
