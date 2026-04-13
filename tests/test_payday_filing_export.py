import os
import sys
import types
import unittest
from datetime import date

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class PaydayFilingExportTests(unittest.TestCase):
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
            "ird_number": "123456789",
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

    def _seed_settings(self, db, missing_contact=False):
        from app.models.settings import Settings

        rows = [
            Settings(key="company_name", value="SlowBooks NZ"),
            Settings(key="company_phone", value="" if missing_contact else "0211234567"),
            Settings(key="company_email", value="" if missing_contact else "payroll@slowbooks.nz"),
            Settings(key="ird_number", value="987654321"),
        ]
        if not missing_contact:
            rows.extend([
                Settings(key="payroll_contact_name", value="Bill Smith"),
                Settings(key="payroll_contact_phone", value="041234567"),
                Settings(key="payroll_contact_email", value="payroll@email.com"),
            ])
        db.add_all(rows)
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

    def test_processed_run_exports_employment_information_file(self):
        from app.routes.payroll import export_employment_information

        with self.Session() as db:
            self._seed_settings(db)
            _employee, processed = self._processed_run(db)
            response = export_employment_information(processed.id, db=db)

        self.assertEqual(response.media_type, "text/csv")
        self.assertIn("EmploymentInformation_2026-04-15_run-1.csv", response.headers["Content-Disposition"])
        content = response.body.decode()
        self.assertIn("HEI2,987654321,20260415", content)
        self.assertIn("Bill Smith", content)
        self.assertIn("payroll@email.com", content)
        self.assertIn("DEI,123456789,Aroha Ngata,M", content)
        self.assertIn(",FT,", content)
        self.assertIn("SlowBooksNZ_nz-localization_v1", content)

    def test_draft_run_export_is_rejected(self):
        from app.routes.payroll import create_pay_run, export_employment_information
        from app.schemas.payroll import PayRunCreate, PayStubInput

        with self.Session() as db:
            self._seed_settings(db)
            employee = self._create_employee(db)
            draft = create_pay_run(PayRunCreate(
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 14),
                pay_date=date(2026, 4, 15),
                stubs=[PayStubInput(employee_id=employee.id)],
            ), db=db)
            with self.assertRaises(HTTPException) as ctx:
                export_employment_information(draft.id, db=db)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("processed", ctx.exception.detail.lower())

    def test_missing_required_contact_data_is_rejected(self):
        from app.routes.payroll import export_employment_information

        with self.Session() as db:
            self._seed_settings(db, missing_contact=True)
            _employee, processed = self._processed_run(db)
            with self.assertRaises(HTTPException) as ctx:
                export_employment_information(processed.id, db=db)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("contact", ctx.exception.detail.lower())


if __name__ == "__main__":
    unittest.main()
