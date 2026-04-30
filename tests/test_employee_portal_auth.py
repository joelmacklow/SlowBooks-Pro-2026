import os
import sys
import types
import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base
from app.models.auth import EmployeePortalLink
from app.models.payroll import Employee


class EmployeePortalAuthTests(unittest.TestCase):
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

    def _create_employee(self, company_db, *, active: bool = True, first_name: str = "Aroha", last_name: str = "Ngata"):
        employee = Employee(
            first_name=first_name,
            last_name=last_name,
            ird_number="123456789",
            pay_type="salary",
            pay_rate=85000,
            tax_code="M",
            kiwisaver_enrolled=True,
            pay_frequency="fortnightly",
            is_active=active,
        )
        company_db.add(employee)
        company_db.commit()
        company_db.refresh(employee)
        return employee

    def _create_employee_user(self, master_db, owner_auth, email: str = "employee@example.com"):
        from app.routes.auth import create_user
        from app.schemas.auth import UserCreateRequest

        return create_user(
            UserCreateRequest(
                email=email,
                password="employee123",
                full_name="Employee One",
                role_key="employee_self_service",
                allow_permissions=[],
                deny_permissions=[],
            ),
            db=master_db,
            auth=owner_auth,
        )

    def _login_employee(self, master_db, email: str):
        from app.routes.auth import login
        from app.schemas.auth import LoginRequest

        return login(LoginRequest(email=email, password="employee123"), db=master_db)

    def _link_employee(self, master_db, company_db, auth, user_id: int, employee_id: int):
        from app.routes.employee_portal import create_link
        from app.schemas.employee_portal import EmployeePortalLinkCreateRequest

        return create_link(
            EmployeePortalLinkCreateRequest(user_id=user_id, employee_id=employee_id),
            db=company_db,
            master_db=master_db,
            auth=auth,
        )

    def test_employee_self_service_role_is_least_privilege(self):
        from app.services.auth import ROLE_TEMPLATE_DEFINITIONS

        permissions = ROLE_TEMPLATE_DEFINITIONS["employee_self_service"]["permissions"]
        self.assertEqual(
            permissions,
            {
                "timesheets.self.view",
                "timesheets.self.create",
                "timesheets.self.submit",
                "payroll.self.payslips.view",
            },
        )
        for forbidden in (
            "employees.view_private",
            "employees.manage",
            "payroll.view",
            "payroll.create",
            "payroll.process",
            "payroll.payslips.view",
        ):
            self.assertNotIn(forbidden, permissions)

    def test_link_existing_user_to_employee_for_active_company_scope(self):
        from app.models.auth import EmployeePortalLink

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            employee_user = self._create_employee_user(master_db, owner_auth)
            employee = self._create_employee(company_db)

            response = self._link_employee(master_db, company_db, owner_auth, employee_user.id, employee.id)

            self.assertEqual(response.user.id, employee_user.id)
            self.assertEqual(response.employee.id, employee.id)
            self.assertEqual(response.company_scope, "__current__")
            self.assertTrue(response.is_active)
            self.assertNotIn("ird_number", response.employee.model_dump())
            self.assertNotIn("pay_rate", response.employee.model_dump())
            self.assertEqual(master_db.query(EmployeePortalLink).count(), 1)

    def test_link_creation_rejects_stale_employee_id(self):
        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            employee_user = self._create_employee_user(master_db, owner_auth)

            with self.assertRaises(HTTPException) as ctx:
                self._link_employee(master_db, company_db, owner_auth, employee_user.id, 999)

            self.assertEqual(ctx.exception.status_code, 404)
            self.assertEqual(master_db.query(EmployeePortalLink).count(), 0)

    def test_link_creation_rejects_inactive_employee(self):
        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            employee_user = self._create_employee_user(master_db, owner_auth)
            employee = self._create_employee(company_db, active=False)

            with self.assertRaises(HTTPException) as ctx:
                self._link_employee(master_db, company_db, owner_auth, employee_user.id, employee.id)

            self.assertEqual(ctx.exception.status_code, 404)
            self.assertEqual(master_db.query(EmployeePortalLink).count(), 0)

    def test_link_creation_rejects_user_without_active_membership_for_scope(self):
        from app.services.auth import update_user_account

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            employee_user = self._create_employee_user(master_db, owner_auth)
            update_user_account(master_db, employee_user.id, membership_active=False)
            employee = self._create_employee(company_db)

            with self.assertRaises(HTTPException) as ctx:
                self._link_employee(master_db, company_db, owner_auth, employee_user.id, employee.id)

            self.assertEqual(ctx.exception.status_code, 403)
            self.assertEqual(master_db.query(EmployeePortalLink).count(), 0)

    def test_duplicate_active_user_scope_link_is_rejected(self):
        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            employee_user = self._create_employee_user(master_db, owner_auth)
            first_employee = self._create_employee(company_db, first_name="Aroha")
            second_employee = self._create_employee(company_db, first_name="Moana")

            self._link_employee(master_db, company_db, owner_auth, employee_user.id, first_employee.id)

            with self.assertRaises(HTTPException) as ctx:
                self._link_employee(master_db, company_db, owner_auth, employee_user.id, second_employee.id)

            self.assertEqual(ctx.exception.status_code, 400)
            self.assertEqual(master_db.query(EmployeePortalLink).filter(EmployeePortalLink.is_active == True).count(), 1)  # noqa: E712

    def test_duplicate_active_employee_scope_link_is_rejected(self):
        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            first_user = self._create_employee_user(master_db, owner_auth, email="first@example.com")
            second_user = self._create_employee_user(master_db, owner_auth, email="second@example.com")
            employee = self._create_employee(company_db)

            self._link_employee(master_db, company_db, owner_auth, first_user.id, employee.id)

            with self.assertRaises(HTTPException) as ctx:
                self._link_employee(master_db, company_db, owner_auth, second_user.id, employee.id)

            self.assertEqual(ctx.exception.status_code, 400)
            self.assertEqual(master_db.query(EmployeePortalLink).filter(EmployeePortalLink.is_active == True).count(), 1)  # noqa: E712

    def test_inactive_historical_link_allows_relink(self):
        from app.routes.employee_portal import deactivate_link

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            employee_user = self._create_employee_user(master_db, owner_auth)
            employee = self._create_employee(company_db)

            first_link = self._link_employee(master_db, company_db, owner_auth, employee_user.id, employee.id)
            deactivate_link(first_link.id, db=company_db, master_db=master_db, auth=owner_auth)
            second_link = self._link_employee(master_db, company_db, owner_auth, employee_user.id, employee.id)

            links = master_db.query(EmployeePortalLink).filter(
                EmployeePortalLink.user_id == employee_user.id,
                EmployeePortalLink.employee_id == employee.id,
            ).all()
            self.assertEqual(len(links), 2)
            self.assertEqual(sum(1 for link in links if link.is_active), 1)
            self.assertTrue(second_link.is_active)

    def test_resolve_employee_link_returns_only_active_current_scope_link(self):
        from app.services.auth import require_permissions
        from app.services.employee_portal import resolve_employee_link

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            employee_user = self._create_employee_user(master_db, owner_auth)
            employee = self._create_employee(company_db)
            self._link_employee(master_db, company_db, owner_auth, employee_user.id, employee.id)

            login = self._login_employee(master_db, employee_user.email)
            self_auth = require_permissions("timesheets.self.view")(db=master_db, authorization=f"Bearer {login.token}")
            response = resolve_employee_link(master_db, company_db, self_auth)

            self.assertEqual(response.user.id, employee_user.id)
            self.assertEqual(response.employee.id, employee.id)
            self.assertFalse(hasattr(response.employee, "ird_number"))
            self.assertFalse(hasattr(response.employee, "pay_rate"))

    def test_resolve_employee_link_does_not_return_payroll_private_fields(self):
        from app.services.auth import require_permissions
        from app.services.employee_portal import resolve_employee_link

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            employee_user = self._create_employee_user(master_db, owner_auth)
            employee = self._create_employee(company_db)
            self._link_employee(master_db, company_db, owner_auth, employee_user.id, employee.id)

            login = self._login_employee(master_db, employee_user.email)
            self_auth = require_permissions("timesheets.self.view")(db=master_db, authorization=f"Bearer {login.token}")
            response = resolve_employee_link(master_db, company_db, self_auth)

            payload = response.model_dump()
            self.assertNotIn("ird_number", payload["employee"])
            self.assertNotIn("pay_rate", payload["employee"])
            self.assertNotIn("tax_code", payload["employee"])
            self.assertNotIn("notes", payload["employee"])

    def test_admin_can_list_links_for_active_scope(self):
        from app.routes.employee_portal import list_links

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            employee_user = self._create_employee_user(master_db, owner_auth)
            employee = self._create_employee(company_db)
            self._link_employee(master_db, company_db, owner_auth, employee_user.id, employee.id)

            listed = list_links(db=company_db, master_db=master_db, auth=owner_auth)
            self.assertEqual(len(listed), 1)
            self.assertEqual(listed[0].user.email, employee_user.email)
            self.assertEqual(listed[0].employee.id, employee.id)
            self.assertNotIn("ird_number", listed[0].employee.model_dump())

    def test_non_admin_cannot_link_or_unlink_employee_user(self):
        from app.routes.auth import create_user, login
        from app.schemas.auth import LoginRequest, UserCreateRequest
        from app.services.auth import require_permissions

        with self.MasterSession() as master_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            create_user(
                UserCreateRequest(
                    email="viewer@example.com",
                    password="viewersecret",
                    full_name="Viewer User",
                    role_key="payroll_viewer",
                    allow_permissions=[],
                    deny_permissions=[],
                ),
                db=master_db,
                auth=owner_auth,
            )
            viewer = login(LoginRequest(email="viewer@example.com", password="viewersecret"), db=master_db)
            with self.assertRaises(HTTPException) as ctx:
                require_permissions("users.manage")(db=master_db, authorization=f"Bearer {viewer.token}")
            self.assertEqual(ctx.exception.status_code, 403)

    def test_employee_can_resolve_self_context_but_not_admin_link_list(self):
        from app.routes.employee_portal import get_self
        from app.services.auth import require_permissions

        with self.MasterSession() as master_db, self.CompanySession() as company_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            employee_user = self._create_employee_user(master_db, owner_auth)
            employee = self._create_employee(company_db)
            self._link_employee(master_db, company_db, owner_auth, employee_user.id, employee.id)

            login = self._login_employee(master_db, employee_user.email)
            self_auth = require_permissions("timesheets.self.view")(db=master_db, authorization=f"Bearer {login.token}")

            self_response = get_self(db=company_db, master_db=master_db, auth=self_auth)
            self.assertEqual(self_response.employee.id, employee.id)
            self.assertEqual(self_response.user.email, employee_user.email)

            with self.assertRaises(HTTPException) as ctx:
                require_permissions("users.manage")(db=master_db, authorization=f"Bearer {login.token}")
            self.assertEqual(ctx.exception.status_code, 403)

    def test_cross_company_header_without_membership_is_rejected(self):
        from app.services.auth import require_permissions

        with self.MasterSession() as master_db:
            _owner, owner_auth = self._bootstrap_owner(master_db)
            employee_user = self._create_employee_user(master_db, owner_auth)

            login = self._login_employee(master_db, employee_user.email)
            with self.assertRaises(HTTPException) as ctx:
                require_permissions("timesheets.self.view")(
                    db=master_db,
                    authorization=f"Bearer {login.token}",
                    x_company_database="other_company",
                )
            self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
