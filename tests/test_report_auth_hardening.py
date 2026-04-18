import inspect
import os
import sys
import types
import unittest
from datetime import date
from decimal import Decimal
from unittest import mock

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class ReportAuthHardeningTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401
        from app.models.contacts import Customer
        from app.models.invoices import Invoice, InvoiceStatus
        from app.models.settings import Settings
        from app.routes import reports as reports_route
        from app.routes.auth import bootstrap_admin, create_user, login
        from app.schemas.auth import BootstrapAdminRequest, LoginRequest, UserCreateRequest
        from app.services.auth import require_permissions

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)
        self.reports_route = reports_route

        with self.Session() as db:
            owner = bootstrap_admin(
                BootstrapAdminRequest(
                    email="owner@example.com",
                    password="supersecret",
                    full_name="Owner User",
                ),
                db=db,
            )
            owner_auth = require_permissions("users.manage")(db=db, authorization=f"Bearer {owner.token}")
            create_user(
                UserCreateRequest(
                    email="staff@example.com",
                    password="staffsecret",
                    full_name="Staff User",
                    role_key="staff",
                    allow_permissions=["accounts.view"],
                    deny_permissions=[],
                ),
                db=db,
                auth=owner_auth,
            )
            staff = login(LoginRequest(email="staff@example.com", password="staffsecret"), db=db)
            for key, value in {
                "company_name": "SlowBooks NZ",
                "company_email": "accounts@example.com",
                "locale": "en-NZ",
                "currency": "NZD",
                "gst_basis": "invoice",
                "gst_period": "two-monthly",
                "gst_number": "123-456-789",
            }.items():
                db.add(Settings(key=key, value=value))
            customer = Customer(name="Aroha Ltd", email="customer@example.com")
            db.add(customer)
            db.flush()
            db.add(Invoice(
                invoice_number="INV-1001",
                customer_id=customer.id,
                status=InvoiceStatus.SENT,
                date=date(2026, 4, 1),
                due_date=date(2026, 4, 15),
                total=Decimal("115.00"),
                balance_due=Decimal("115.00"),
            ))
            db.commit()

            self.owner_token = owner.token
            self.staff_token = staff.token
            self.customer_id = customer.id

    def _auth_dependency(self, func):
        parameter = inspect.signature(func).parameters.get("auth")
        self.assertIsNotNone(parameter, f"{func.__name__} is missing auth parameter")
        dependency = getattr(parameter.default, "dependency", None)
        self.assertIsNotNone(dependency, f"{func.__name__} auth parameter is not a FastAPI dependency")
        return dependency

    def _assert_accounts_manage_gate(self, func):
        dependency = self._auth_dependency(func)
        with self.Session() as db:
            with self.assertRaises(HTTPException) as unauth_ctx:
                dependency(db=db, authorization=None)
            self.assertEqual(unauth_ctx.exception.status_code, 401, func.__name__)

            with self.assertRaises(HTTPException) as staff_ctx:
                dependency(db=db, authorization=f"Bearer {self.staff_token}")
            self.assertEqual(staff_ctx.exception.status_code, 403, func.__name__)

            owner_auth = dependency(db=db, authorization=f"Bearer {self.owner_token}")
        return owner_auth

    def test_core_report_routes_require_accounts_manage(self):
        route_calls = [
            (self.reports_route.profit_loss, {"start_date": date(2026, 4, 1), "end_date": date(2026, 4, 30)}),
            (self.reports_route.balance_sheet, {"as_of_date": date(2026, 4, 30)}),
            (self.reports_route.trial_balance, {"as_of_date": date(2026, 4, 30)}),
            (self.reports_route.cash_flow_report, {"start_date": date(2026, 4, 1), "end_date": date(2026, 4, 30)}),
            (self.reports_route.ar_aging, {"as_of_date": date(2026, 4, 30)}),
            (self.reports_route.ap_aging, {"as_of_date": date(2026, 4, 30)}),
            (self.reports_route.general_ledger, {"start_date": date(2026, 4, 1), "end_date": date(2026, 4, 30), "account_id": None}),
            (self.reports_route.income_by_customer, {"start_date": date(2026, 4, 1), "end_date": date(2026, 4, 30)}),
            (self.reports_route.gst_return_report, {"start_date": date(2026, 4, 1), "end_date": date(2026, 4, 30)}),
            (self.reports_route.gst_returns_overview, {"as_of_date": date(2026, 4, 30)}),
            (self.reports_route.gst_return_transactions, {"start_date": date(2026, 4, 1), "end_date": date(2026, 4, 30), "page": 1, "page_size": 10}),
            (self.reports_route.sales_tax_report, {"start_date": date(2026, 4, 1), "end_date": date(2026, 4, 30)}),
            (self.reports_route.overdue_statement_candidates, {"as_of_date": date(2026, 4, 30)}),
        ]

        for func, kwargs in route_calls:
            owner_auth = self._assert_accounts_manage_gate(func)
            with self.Session() as db:
                result = func(db=db, auth=owner_auth, **kwargs)
            self.assertIsNotNone(result, func.__name__)

    def test_pdf_and_customer_statement_routes_require_accounts_manage(self):
        for func in [
            self.reports_route.profit_loss_pdf,
            self.reports_route.balance_sheet_pdf,
            self.reports_route.trial_balance_pdf,
            self.reports_route.cash_flow_pdf,
            self.reports_route.ar_aging_pdf,
            self.reports_route.ap_aging_pdf,
            self.reports_route.gst_return_pdf,
            self.reports_route.general_ledger_pdf,
            self.reports_route.income_by_customer_pdf,
            self.reports_route.customer_statement_pdf,
            self.reports_route.email_customer_statement,
            self.reports_route.send_overdue_statements,
        ]:
            self._assert_accounts_manage_gate(func)

        with mock.patch.object(self.reports_route, "generate_gst101a_pdf", return_value=b"%PDF-gst"), \
             mock.patch.object(self.reports_route, "generate_report_pdf", return_value=b"%PDF-report"), \
             mock.patch.object(self.reports_route, "generate_statement_pdf", return_value=b"%PDF-statement"), \
             mock.patch.object(self.reports_route, "send_document_email", return_value=None):
            with self.Session() as db:
                profit_loss_pdf_auth = self._auth_dependency(self.reports_route.profit_loss_pdf)(
                    db=db, authorization=f"Bearer {self.owner_token}"
                )
                balance_sheet_pdf_auth = self._auth_dependency(self.reports_route.balance_sheet_pdf)(
                    db=db, authorization=f"Bearer {self.owner_token}"
                )
                trial_balance_pdf_auth = self._auth_dependency(self.reports_route.trial_balance_pdf)(
                    db=db, authorization=f"Bearer {self.owner_token}"
                )
                cash_flow_pdf_auth = self._auth_dependency(self.reports_route.cash_flow_pdf)(
                    db=db, authorization=f"Bearer {self.owner_token}"
                )
                ar_pdf_auth = self._auth_dependency(self.reports_route.ar_aging_pdf)(
                    db=db, authorization=f"Bearer {self.owner_token}"
                )
                ap_pdf_auth = self._auth_dependency(self.reports_route.ap_aging_pdf)(
                    db=db, authorization=f"Bearer {self.owner_token}"
                )
                gst_auth = self._auth_dependency(self.reports_route.gst_return_pdf)(
                    db=db, authorization=f"Bearer {self.owner_token}"
                )
                gl_pdf_auth = self._auth_dependency(self.reports_route.general_ledger_pdf)(
                    db=db, authorization=f"Bearer {self.owner_token}"
                )
                ibc_pdf_auth = self._auth_dependency(self.reports_route.income_by_customer_pdf)(
                    db=db, authorization=f"Bearer {self.owner_token}"
                )
                stmt_pdf_auth = self._auth_dependency(self.reports_route.customer_statement_pdf)(
                    db=db, authorization=f"Bearer {self.owner_token}"
                )
                stmt_email_auth = self._auth_dependency(self.reports_route.email_customer_statement)(
                    db=db, authorization=f"Bearer {self.owner_token}"
                )
                batch_stmt_auth = self._auth_dependency(self.reports_route.send_overdue_statements)(
                    db=db, authorization=f"Bearer {self.owner_token}"
                )

                gst_pdf = self.reports_route.gst_return_pdf(
                    start_date=date(2026, 4, 1),
                    end_date=date(2026, 4, 30),
                    db=db,
                    auth=gst_auth,
                )
                profit_loss_pdf = self.reports_route.profit_loss_pdf(
                    start_date=date(2026, 4, 1),
                    end_date=date(2026, 4, 30),
                    db=db,
                    auth=profit_loss_pdf_auth,
                )
                balance_sheet_pdf = self.reports_route.balance_sheet_pdf(
                    as_of_date=date(2026, 4, 30),
                    db=db,
                    auth=balance_sheet_pdf_auth,
                )
                trial_balance_pdf = self.reports_route.trial_balance_pdf(
                    as_of_date=date(2026, 4, 30),
                    db=db,
                    auth=trial_balance_pdf_auth,
                )
                cash_flow_pdf = self.reports_route.cash_flow_pdf(
                    start_date=date(2026, 4, 1),
                    end_date=date(2026, 4, 30),
                    db=db,
                    auth=cash_flow_pdf_auth,
                )
                ar_pdf = self.reports_route.ar_aging_pdf(
                    as_of_date=date(2026, 4, 30),
                    db=db,
                    auth=ar_pdf_auth,
                )
                ap_pdf = self.reports_route.ap_aging_pdf(
                    as_of_date=date(2026, 4, 30),
                    db=db,
                    auth=ap_pdf_auth,
                )
                gl_pdf = self.reports_route.general_ledger_pdf(
                    start_date=date(2026, 4, 1),
                    end_date=date(2026, 4, 30),
                    account_id=None,
                    db=db,
                    auth=gl_pdf_auth,
                )
                ibc_pdf = self.reports_route.income_by_customer_pdf(
                    start_date=date(2026, 4, 1),
                    end_date=date(2026, 4, 30),
                    db=db,
                    auth=ibc_pdf_auth,
                )
                stmt_pdf = self.reports_route.customer_statement_pdf(
                    self.customer_id,
                    as_of_date=date(2026, 4, 30),
                    db=db,
                    auth=stmt_pdf_auth,
                )
                stmt_email = self.reports_route.email_customer_statement(
                    self.customer_id,
                    self.reports_route.StatementEmailRequest(
                        recipient="customer@example.com",
                        as_of_date=date(2026, 4, 30),
                    ),
                    db=db,
                    auth=stmt_email_auth,
                )
                batch_stmt = self.reports_route.send_overdue_statements(
                    self.reports_route.BatchOverdueStatementRequest(
                        as_of_date=date(2026, 4, 30),
                        recipients=[
                            self.reports_route.OverdueStatementRecipient(
                                customer_id=self.customer_id,
                                recipient="customer@example.com",
                            )
                        ],
                    ),
                    db=db,
                    auth=batch_stmt_auth,
                    request=None,
                )

        self.assertEqual(profit_loss_pdf.media_type, "application/pdf")
        self.assertEqual(balance_sheet_pdf.media_type, "application/pdf")
        self.assertEqual(trial_balance_pdf.media_type, "application/pdf")
        self.assertEqual(cash_flow_pdf.media_type, "application/pdf")
        self.assertEqual(ar_pdf.media_type, "application/pdf")
        self.assertEqual(ap_pdf.media_type, "application/pdf")
        self.assertEqual(gst_pdf.media_type, "application/pdf")
        self.assertEqual(gl_pdf.media_type, "application/pdf")
        self.assertEqual(ibc_pdf.media_type, "application/pdf")
        self.assertEqual(stmt_pdf.media_type, "application/pdf")
        self.assertEqual(stmt_email["status"], "sent")
        self.assertEqual(batch_stmt["sent_count"], 1)


if __name__ == "__main__":
    unittest.main()
