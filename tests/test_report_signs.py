import os
import sys
import types
import unittest
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base
from app.models.accounts import Account, AccountType


class ReportSignTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_profit_and_loss_rows_use_natural_positive_signs(self):
        from app.routes.reports import profit_loss
        from app.services.accounting import create_journal_entry

        with self.Session() as db:
            bank = Account(name="Business Bank", account_number="090", account_type=AccountType.ASSET, is_active=True)
            sales = Account(name="Sales", account_number="4000", account_type=AccountType.INCOME, is_active=True)
            cogs = Account(name="Purchases", account_number="5000", account_type=AccountType.COGS, is_active=True)
            expense = Account(name="Office Expenses", account_number="6000", account_type=AccountType.EXPENSE, is_active=True)
            db.add_all([bank, sales, cogs, expense])
            db.commit()

            create_journal_entry(db, date(2026, 4, 1), "sale", [
                {"account_id": bank.id, "debit": Decimal("230.00"), "credit": Decimal("0.00")},
                {"account_id": sales.id, "debit": Decimal("0.00"), "credit": Decimal("230.00")},
            ])
            create_journal_entry(db, date(2026, 4, 2), "cogs", [
                {"account_id": cogs.id, "debit": Decimal("80.00"), "credit": Decimal("0.00")},
                {"account_id": bank.id, "debit": Decimal("0.00"), "credit": Decimal("80.00")},
            ])
            create_journal_entry(db, date(2026, 4, 3), "expense", [
                {"account_id": expense.id, "debit": Decimal("25.00"), "credit": Decimal("0.00")},
                {"account_id": bank.id, "debit": Decimal("0.00"), "credit": Decimal("25.00")},
            ])
            db.commit()

            report = profit_loss(
                start_date=date(2026, 4, 1),
                end_date=date(2026, 4, 30),
                db=db,
                auth={"user_id": 1},
            )

        self.assertEqual(report["income"][0]["amount"], 230.0)
        self.assertEqual(report["cogs"][0]["amount"], 80.0)
        self.assertEqual(report["expenses"][0]["amount"], 25.0)
        self.assertEqual(report["total_income"], 230.0)
        self.assertEqual(report["total_cogs"], 80.0)
        self.assertEqual(report["total_expenses"], 25.0)
        self.assertEqual(report["net_income"], 125.0)

    def test_balance_sheet_rows_use_natural_positive_signs(self):
        from app.routes.reports import balance_sheet
        from app.services.accounting import create_journal_entry

        with self.Session() as db:
            bank = Account(name="Business Bank", account_number="090", account_type=AccountType.ASSET, is_active=True)
            gst = Account(name="GST", account_number="2200", account_type=AccountType.LIABILITY, is_active=True)
            equity = Account(name="Owner Funds", account_number="9000", account_type=AccountType.EQUITY, is_active=True)
            db.add_all([bank, gst, equity])
            db.commit()

            create_journal_entry(db, date(2026, 4, 1), "capital", [
                {"account_id": bank.id, "debit": Decimal("50.00"), "credit": Decimal("0.00")},
                {"account_id": equity.id, "debit": Decimal("0.00"), "credit": Decimal("50.00")},
            ])
            create_journal_entry(db, date(2026, 4, 2), "gst sale", [
                {"account_id": bank.id, "debit": Decimal("15.00"), "credit": Decimal("0.00")},
                {"account_id": gst.id, "debit": Decimal("0.00"), "credit": Decimal("15.00")},
            ])
            db.commit()

            report = balance_sheet(
                as_of_date=date(2026, 4, 30),
                db=db,
                auth={"user_id": 1},
            )

        asset_amounts = {row["account_number"]: row["amount"] for row in report["assets"]}
        liability_amounts = {row["account_number"]: row["amount"] for row in report["liabilities"]}
        equity_amounts = {row["account_number"]: row["amount"] for row in report["equity"]}

        self.assertEqual(asset_amounts["090"], 65.0)
        self.assertEqual(liability_amounts["2200"], 15.0)
        self.assertEqual(equity_amounts["9000"], 50.0)
        self.assertEqual(report["total_assets"], 65.0)
        self.assertEqual(report["total_liabilities"], 15.0)
        self.assertEqual(report["total_equity"], 50.0)
        self.assertEqual(report["current_earnings"], 0.0)
        self.assertEqual(report["total_liabilities_and_equity"], 65.0)
        self.assertEqual(report["balance_difference"], 0.0)
        self.assertTrue(report["is_balanced"])

    def test_balance_sheet_includes_unclosed_earnings_in_equity_total(self):
        from app.routes.reports import balance_sheet
        from app.services.accounting import create_journal_entry

        with self.Session() as db:
            bank = Account(name="Business Bank", account_number="090", account_type=AccountType.ASSET, is_active=True)
            sales = Account(name="Sales", account_number="4000", account_type=AccountType.INCOME, is_active=True)
            db.add_all([bank, sales])
            db.commit()

            create_journal_entry(db, date(2026, 4, 1), "sale", [
                {"account_id": bank.id, "debit": Decimal("100.00"), "credit": Decimal("0.00")},
                {"account_id": sales.id, "debit": Decimal("0.00"), "credit": Decimal("100.00")},
            ])
            db.commit()

            report = balance_sheet(
                as_of_date=date(2026, 4, 30),
                db=db,
                auth={"user_id": 1},
            )

        self.assertEqual(report["total_assets"], 100.0)
        self.assertEqual(report["total_liabilities"], 0.0)
        self.assertEqual(report["current_earnings"], 100.0)
        self.assertEqual(report["total_equity"], 100.0)
        self.assertEqual(report["total_liabilities_and_equity"], 100.0)
        self.assertEqual(report["balance_difference"], 0.0)
        self.assertTrue(report["is_balanced"])


if __name__ == "__main__":
    unittest.main()
