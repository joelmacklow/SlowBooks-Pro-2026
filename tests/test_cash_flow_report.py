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


class CashFlowReportTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401
        from app.models.accounts import Account, AccountType
        from app.models.banking import BankAccount
        from app.models.transactions import Transaction, TransactionLine

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

        with self.Session() as db:
            bank = Account(name="Business Bank", account_number="090", account_type=AccountType.ASSET)
            sales = Account(name="Sales", account_number="200", account_type=AccountType.INCOME)
            savings = Account(name="Savings Account", account_number="091", account_type=AccountType.ASSET)
            equipment = Account(name="Plant and Equipment", account_number="708", account_type=AccountType.ASSET)
            loan = Account(name="Term Loan", account_number="850", account_type=AccountType.LIABILITY)
            db.add_all([bank, sales, savings, equipment, loan])
            db.flush()
            db.add_all([
                BankAccount(name="ANZ", account_id=bank.id, bank_name="ANZ", last_four="1208", balance=Decimal("0.00"), is_active=True),
                BankAccount(name="Saver", account_id=savings.id, bank_name="ANZ", last_four="7788", balance=Decimal("0.00"), is_active=True),
            ])
            db.flush()

            db.add_all([
                Transaction(
                    date=date(2026, 3, 31),
                    reference="OPEN",
                    description="Opening cash",
                    source_type="manual_journal",
                    lines=[
                        TransactionLine(account_id=bank.id, debit=Decimal("250.00"), credit=Decimal("0.00")),
                        TransactionLine(account_id=loan.id, debit=Decimal("0.00"), credit=Decimal("250.00")),
                    ],
                ),
                Transaction(
                    date=date(2026, 4, 1),
                    reference="INV-1001",
                    description="Customer receipt",
                    source_type="payment",
                    lines=[
                        TransactionLine(account_id=bank.id, debit=Decimal("115.00"), credit=Decimal("0.00")),
                        TransactionLine(account_id=sales.id, debit=Decimal("0.00"), credit=Decimal("115.00")),
                    ],
                ),
                Transaction(
                    date=date(2026, 4, 10),
                    reference="EQ-1",
                    description="Equipment purchase",
                    source_type="manual_journal",
                    lines=[
                        TransactionLine(account_id=equipment.id, debit=Decimal("500.00"), credit=Decimal("0.00")),
                        TransactionLine(account_id=bank.id, debit=Decimal("0.00"), credit=Decimal("500.00")),
                    ],
                ),
                Transaction(
                    date=date(2026, 4, 20),
                    reference="LOAN-1",
                    description="Loan proceeds",
                    source_type="manual_journal",
                    lines=[
                        TransactionLine(account_id=bank.id, debit=Decimal("1000.00"), credit=Decimal("0.00")),
                        TransactionLine(account_id=loan.id, debit=Decimal("0.00"), credit=Decimal("1000.00")),
                    ],
                ),
                Transaction(
                    date=date(2026, 4, 25),
                    reference="XFER-1",
                    description="Internal cash transfer",
                    source_type="manual_journal",
                    lines=[
                        TransactionLine(account_id=savings.id, debit=Decimal("100.00"), credit=Decimal("0.00")),
                        TransactionLine(account_id=bank.id, debit=Decimal("0.00"), credit=Decimal("100.00")),
                    ],
                ),
            ])
            db.commit()

    def test_cash_flow_groups_movements_by_activity(self):
        from app.routes.reports import cash_flow_report

        with self.Session() as db:
            report = cash_flow_report(start_date=date(2026, 4, 1), end_date=date(2026, 4, 30), db=db, auth={"user_id": 1})

        self.assertEqual(report["start_date"], "2026-04-01")
        self.assertEqual(report["end_date"], "2026-04-30")
        self.assertEqual(report["operating"]["total"], 115.0)
        self.assertEqual(report["investing"]["total"], -500.0)
        self.assertEqual(report["financing"]["total"], 1000.0)
        self.assertEqual(report["opening_cash"], 250.0)
        self.assertEqual(report["net_cash_change"], 615.0)
        self.assertEqual(report["closing_cash"], 865.0)
        self.assertEqual(len(report["operating"]["items"]), 1)
        self.assertEqual(len(report["investing"]["items"]), 1)
        self.assertEqual(len(report["financing"]["items"]), 1)

    def test_cash_flow_excludes_transactions_outside_period(self):
        from app.routes.reports import cash_flow_report

        with self.Session() as db:
            report = cash_flow_report(start_date=date(2026, 4, 15), end_date=date(2026, 4, 30), db=db, auth={"user_id": 1})

        self.assertEqual(report["operating"]["total"], 0.0)
        self.assertEqual(report["investing"]["total"], 0.0)
        self.assertEqual(report["financing"]["total"], 1000.0)
        self.assertEqual(report["opening_cash"], -135.0)
        self.assertEqual(report["closing_cash"], 865.0)

    def test_cash_flow_pdf_returns_inline_pdf(self):
        from app.routes import reports as reports_route

        with mock.patch.object(reports_route, "generate_report_pdf", return_value=b"%PDF-cash-flow") as generate_pdf:
            with self.Session() as db:
                response = reports_route.cash_flow_pdf(
                    start_date=date(2026, 4, 1),
                    end_date=date(2026, 4, 30),
                    db=db,
                    auth={"user_id": 1},
                )

        self.assertEqual(generate_pdf.call_args.kwargs["title"], "Cash Flow")
        self.assertEqual(response.media_type, "application/pdf")
        self.assertEqual(response.headers["Content-Disposition"], 'inline; filename="CashFlow_2026-04-01_2026-04-30.pdf"')

    def test_cash_flow_pdf_uses_narrowed_table_width(self):
        from app.routes import reports as reports_route

        with self.Session() as db:
            report = reports_route.cash_flow_report(
                start_date=date(2026, 4, 1),
                end_date=date(2026, 4, 30),
                db=db,
                auth={"user_id": 1},
            )

        tables = reports_route._report_tables_cash_flow(report, {"locale": "en-NZ", "currency": "NZD"})
        self.assertTrue(all(table.get("style") == "width: 92%;" for table in tables))
        self.assertEqual(tables[-1]["columns"], [
            {"label": "Measure", "width": "80%"},
            {"label": "Amount", "align": "right", "width": "20%"},
        ])


if __name__ == "__main__":
    unittest.main()
