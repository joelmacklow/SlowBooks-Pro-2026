import os
import sys
import types
import unittest
from datetime import date
from decimal import Decimal
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class TrialBalanceReportTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401
        from app.models.accounts import Account, AccountType
        from app.models.transactions import Transaction, TransactionLine

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

        with self.Session() as db:
            bank = Account(name="Business Bank", account_number="090", account_type=AccountType.ASSET)
            gst = Account(name="GST", account_number="2200", account_type=AccountType.LIABILITY)
            sales = Account(name="Sales", account_number="200", account_type=AccountType.INCOME)
            office = Account(name="Office Supplies", account_number="610", account_type=AccountType.EXPENSE)
            db.add_all([bank, gst, sales, office])
            db.flush()

            april_invoice = Transaction(
                date=date(2026, 4, 1),
                reference="INV-1001",
                description="April sale",
                source_type="invoice",
                source_id=1,
                lines=[
                    TransactionLine(account_id=bank.id, debit=Decimal("115.00"), credit=Decimal("0.00")),
                    TransactionLine(account_id=sales.id, debit=Decimal("0.00"), credit=Decimal("100.00")),
                    TransactionLine(account_id=gst.id, debit=Decimal("0.00"), credit=Decimal("15.00")),
                ],
            )
            april_expense = Transaction(
                date=date(2026, 4, 15),
                reference="BILL-2001",
                description="Office supplies",
                source_type="bill",
                source_id=2,
                lines=[
                    TransactionLine(account_id=office.id, debit=Decimal("23.00"), credit=Decimal("0.00")),
                    TransactionLine(account_id=bank.id, debit=Decimal("0.00"), credit=Decimal("23.00")),
                ],
            )
            may_invoice = Transaction(
                date=date(2026, 5, 1),
                reference="INV-1002",
                description="May sale",
                source_type="invoice",
                source_id=3,
                lines=[
                    TransactionLine(account_id=bank.id, debit=Decimal("57.50"), credit=Decimal("0.00")),
                    TransactionLine(account_id=sales.id, debit=Decimal("0.00"), credit=Decimal("50.00")),
                    TransactionLine(account_id=gst.id, debit=Decimal("0.00"), credit=Decimal("7.50")),
                ],
            )
            db.add_all([april_invoice, april_expense, may_invoice])
            db.commit()

    def test_trial_balance_reports_balanced_debit_and_credit_columns(self):
        from app.routes.reports import trial_balance

        with self.Session() as db:
            report = trial_balance(as_of_date=date(2026, 4, 30), db=db, auth={"user_id": 1})

        self.assertEqual(report["as_of_date"], "2026-04-30")
        self.assertEqual(report["total_debit"], 115.0)
        self.assertEqual(report["total_credit"], 115.0)

        rows = {row["account_name"]: row for row in report["accounts"]}
        self.assertEqual([row["account_number"] for row in report["accounts"]], ["090", "200", "2200", "610"])
        self.assertEqual(rows["Business Bank"]["debit_balance"], 92.0)
        self.assertEqual(rows["Business Bank"]["credit_balance"], 0.0)
        self.assertEqual(rows["Sales"]["debit_balance"], 0.0)
        self.assertEqual(rows["Sales"]["credit_balance"], 100.0)
        self.assertEqual(rows["GST"]["credit_balance"], 15.0)
        self.assertEqual(rows["Office Supplies"]["debit_balance"], 23.0)

    def test_trial_balance_excludes_future_transactions_from_as_of_date(self):
        from app.routes.reports import trial_balance

        with self.Session() as db:
            april_report = trial_balance(as_of_date=date(2026, 4, 30), db=db, auth={"user_id": 1})
            may_report = trial_balance(as_of_date=date(2026, 5, 31), db=db, auth={"user_id": 1})

        april_rows = {row["account_name"]: row for row in april_report["accounts"]}
        may_rows = {row["account_name"]: row for row in may_report["accounts"]}

        self.assertEqual(april_rows["Business Bank"]["debit_balance"], 92.0)
        self.assertEqual(may_rows["Business Bank"]["debit_balance"], 149.5)
        self.assertEqual(april_rows["Sales"]["credit_balance"], 100.0)
        self.assertEqual(may_rows["Sales"]["credit_balance"], 150.0)
        self.assertEqual(may_report["total_debit"], 172.5)
        self.assertEqual(may_report["total_credit"], 172.5)

    def test_trial_balance_pdf_returns_inline_pdf(self):
        from app.routes import reports as reports_route

        with mock.patch.object(reports_route, "generate_report_pdf", return_value=b"%PDF-trial-balance"):
            with self.Session() as db:
                response = reports_route.trial_balance_pdf(
                    as_of_date=date(2026, 4, 30),
                    db=db,
                    auth={"user_id": 1},
                )

        self.assertEqual(response.media_type, "application/pdf")
        self.assertEqual(response.headers["Content-Disposition"], 'inline; filename="TrialBalance_2026-04-30.pdf"')


if __name__ == "__main__":
    unittest.main()
