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


class StatementOfChangesInEquityReportTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401
        from app.models.accounts import Account, AccountType
        from app.models.transactions import Transaction, TransactionLine

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

        with self.Session() as db:
            bank = Account(name="Business Bank", account_number="090", account_type=AccountType.ASSET)
            capital = Account(name="Share Capital", account_number="3000", account_type=AccountType.EQUITY)
            drawings = Account(name="Drawings", account_number="3100", account_type=AccountType.EQUITY)
            sales = Account(name="Sales", account_number="4000", account_type=AccountType.INCOME)
            rent = Account(name="Rent Expense", account_number="5000", account_type=AccountType.EXPENSE)
            db.add_all([bank, capital, drawings, sales, rent])
            db.flush()

            db.add(Transaction(
                date=date(2025, 12, 31),
                reference="OPEN-1",
                description="Opening capital",
                source_type="journal",
                source_id=1,
                lines=[
                    TransactionLine(account_id=bank.id, debit=Decimal("1000.00"), credit=Decimal("0.00")),
                    TransactionLine(account_id=capital.id, debit=Decimal("0.00"), credit=Decimal("1000.00")),
                ],
            ))
            db.add(Transaction(
                date=date(2026, 4, 10),
                reference="DRAW-1",
                description="Owner drawings",
                source_type="journal",
                source_id=2,
                lines=[
                    TransactionLine(account_id=drawings.id, debit=Decimal("200.00"), credit=Decimal("0.00")),
                    TransactionLine(account_id=bank.id, debit=Decimal("0.00"), credit=Decimal("200.00")),
                ],
            ))
            db.add(Transaction(
                date=date(2026, 4, 15),
                reference="SALE-1",
                description="April sale",
                source_type="invoice",
                source_id=3,
                lines=[
                    TransactionLine(account_id=bank.id, debit=Decimal("500.00"), credit=Decimal("0.00")),
                    TransactionLine(account_id=sales.id, debit=Decimal("0.00"), credit=Decimal("500.00")),
                ],
            ))
            db.add(Transaction(
                date=date(2026, 4, 20),
                reference="EXP-1",
                description="April rent",
                source_type="bill",
                source_id=4,
                lines=[
                    TransactionLine(account_id=rent.id, debit=Decimal("150.00"), credit=Decimal("0.00")),
                    TransactionLine(account_id=bank.id, debit=Decimal("0.00"), credit=Decimal("150.00")),
                ],
            ))
            db.commit()

    def test_statement_of_changes_in_equity_includes_profit_and_equity_movements(self):
        from app.routes.reports import statement_of_changes_in_equity

        with self.Session() as db:
            report = statement_of_changes_in_equity(
                start_date=date(2026, 4, 1),
                end_date=date(2026, 4, 30),
                db=db,
                auth={"user_id": 1},
            )

        self.assertEqual(report["start_date"], "2026-04-01")
        self.assertEqual(report["end_date"], "2026-04-30")
        self.assertEqual(report["opening_total"], 1000.0)
        self.assertEqual(report["direct_movements_total"], -200.0)
        self.assertEqual(report["current_period_profit"], 350.0)
        self.assertEqual(report["account_closing_total"], 800.0)
        self.assertEqual(report["closing_total"], 1150.0)
        self.assertEqual(report["difference"], 0.0)
        self.assertTrue(report["is_balanced"])

        rows = {row["account_name"]: row for row in report["equity_accounts"]}
        self.assertEqual([row["account_number"] for row in report["equity_accounts"]], ["3000", "3100"])
        self.assertEqual(rows["Share Capital"]["opening_balance"], 1000.0)
        self.assertEqual(rows["Share Capital"]["movement"], 0.0)
        self.assertEqual(rows["Share Capital"]["closing_balance"], 1000.0)
        self.assertEqual(rows["Drawings"]["opening_balance"], 0.0)
        self.assertEqual(rows["Drawings"]["movement"], -200.0)
        self.assertEqual(rows["Drawings"]["closing_balance"], -200.0)

    def test_statement_of_changes_in_equity_pdf_returns_inline_pdf(self):
        from app.routes import reports as reports_route

        with mock.patch.object(reports_route, "generate_report_pdf", return_value=b"%PDF-soce") as generate_pdf:
            with self.Session() as db:
                response = reports_route.statement_of_changes_in_equity_pdf(
                    start_date=date(2026, 4, 1),
                    end_date=date(2026, 4, 30),
                    db=db,
                    auth={"user_id": 1},
                )

        self.assertEqual(generate_pdf.call_args.kwargs["title"], "Statement of Changes in Equity")
        self.assertEqual(response.media_type, "application/pdf")
        self.assertEqual(
            response.headers["Content-Disposition"],
            'inline; filename="StatementOfChangesInEquity_2026-04-01_2026-04-30.pdf"',
        )


if __name__ == "__main__":
    unittest.main()
