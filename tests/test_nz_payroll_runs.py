import os
import unittest
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.database import Base
from app.models.transactions import TransactionLine


class NzPayrollRunTests(unittest.TestCase):
    def setUp(self):
        from app.models.accounts import Account  # noqa: F401
        from app.models.payroll import Employee, PayRun, PayStub  # noqa: F401
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

    def test_create_pay_run_calculates_nz_deductions_for_salary_and_hourly_staff(self):
        from app.routes.payroll import create_pay_run
        from app.schemas.payroll import PayRunCreate, PayStubInput

        with self.Session() as db:
            salary_employee = self._create_employee(db)
            hourly_employee = self._create_employee(
                db,
                first_name="Wiremu",
                last_name="Kingi",
                pay_type="hourly",
                pay_rate=30,
                tax_code="M SL",
                kiwisaver_enrolled=False,
                student_loan=True,
                child_support=True,
                child_support_amount="200.00",
                esct_rate="0.0000",
                pay_frequency="weekly",
            )

            pay_run = create_pay_run(PayRunCreate(
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 14),
                pay_date=date(2026, 4, 15),
                stubs=[
                    PayStubInput(employee_id=salary_employee.id),
                    PayStubInput(employee_id=hourly_employee.id, hours=40),
                ],
            ), db=db)

        self.assertEqual(pay_run.status, "draft")
        self.assertEqual(pay_run.tax_year, 2027)
        self.assertEqual(Decimal(str(pay_run.total_gross)), Decimal("4200.00"))
        self.assertEqual(Decimal(str(pay_run.total_net)), Decimal("2922.01"))
        self.assertEqual(Decimal(str(pay_run.total_taxes)), Decimal("1277.99"))

        salary_stub = next(stub for stub in pay_run.stubs if stub.employee_id == salary_employee.id)
        hourly_stub = next(stub for stub in pay_run.stubs if stub.employee_id == hourly_employee.id)

        self.assertEqual(Decimal(str(salary_stub.gross_pay)), Decimal("3000.00"))
        self.assertEqual(Decimal(str(salary_stub.paye)), Decimal("600.78"))
        self.assertEqual(Decimal(str(salary_stub.acc_earners_levy)), Decimal("52.50"))
        self.assertEqual(Decimal(str(salary_stub.kiwisaver_employee_deduction)), Decimal("105.00"))
        self.assertEqual(Decimal(str(salary_stub.employer_kiwisaver_contribution)), Decimal("105.00"))
        self.assertEqual(Decimal(str(salary_stub.esct)), Decimal("18.37"))
        self.assertEqual(Decimal(str(salary_stub.net_pay)), Decimal("2241.72"))

        self.assertEqual(Decimal(str(hourly_stub.gross_pay)), Decimal("1200.00"))
        self.assertEqual(Decimal(str(hourly_stub.paye)), Decimal("210.39"))
        self.assertEqual(Decimal(str(hourly_stub.acc_earners_levy)), Decimal("21.00"))
        self.assertEqual(Decimal(str(hourly_stub.student_loan_deduction)), Decimal("88.32"))
        self.assertEqual(Decimal(str(hourly_stub.child_support_deduction)), Decimal("200.00"))
        self.assertEqual(Decimal(str(hourly_stub.net_pay)), Decimal("680.29"))

    def test_process_pay_run_posts_balanced_nz_payroll_journal_and_blocks_repeat_processing(self):
        from app.models.accounts import Account
        from app.routes.payroll import create_pay_run, process_pay_run
        from app.schemas.payroll import PayRunCreate, PayStubInput

        with self.Session() as db:
            salary_employee = self._create_employee(db)
            hourly_employee = self._create_employee(
                db,
                first_name="Wiremu",
                last_name="Kingi",
                pay_type="hourly",
                pay_rate=30,
                tax_code="M SL",
                kiwisaver_enrolled=False,
                student_loan=True,
                child_support=True,
                child_support_amount="200.00",
                esct_rate="0.0000",
                pay_frequency="weekly",
            )

            pay_run = create_pay_run(PayRunCreate(
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 14),
                pay_date=date(2026, 4, 15),
                stubs=[
                    PayStubInput(employee_id=salary_employee.id),
                    PayStubInput(employee_id=hourly_employee.id, hours=40),
                ],
            ), db=db)
            processed = process_pay_run(pay_run.id, db=db)
            lines = db.query(TransactionLine).filter(TransactionLine.transaction_id == processed.transaction_id).all()
            accounts = {account.account_number: account.name for account in db.query(Account).all()}

            with self.assertRaises(HTTPException) as ctx:
                process_pay_run(pay_run.id, db=db)

        self.assertEqual(processed.status, "processed")
        self.assertEqual(sum(line.debit for line in lines), Decimal("4305.00"))
        self.assertEqual(sum(line.credit for line in lines), Decimal("4305.00"))
        self.assertIn("2310", accounts)
        self.assertIn("2315", accounts)
        self.assertIn("2320", accounts)
        self.assertIn("2325", accounts)
        self.assertIn("2330", accounts)
        self.assertIn("7000", accounts)
        self.assertIn("7010", accounts)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("already processed", ctx.exception.detail)
