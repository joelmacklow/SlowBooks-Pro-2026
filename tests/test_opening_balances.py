import os
import sys
import types
import unittest
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class OpeningBalancesTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_status_reports_not_ready_without_accounts_or_markers(self):
        from app.routes.opening_balances import get_opening_balance_status

        with self.Session() as db:
            result = get_opening_balance_status(db=db)

        self.assertFalse(result["is_ready"])
        self.assertIsNone(result["source"])

    def test_status_reports_legacy_ready_when_balance_sheet_accounts_exist(self):
        from app.models.accounts import Account, AccountType
        from app.routes.opening_balances import get_opening_balance_status

        with self.Session() as db:
            db.add(Account(name="Bank", account_number="090", account_type=AccountType.ASSET, is_active=True))
            db.commit()
            result = get_opening_balance_status(db=db)

        self.assertTrue(result["is_ready"])
        self.assertEqual(result["source"], "legacy_existing_accounts")

    def test_create_opening_balances_rejects_when_chart_not_ready(self):
        from app.routes.opening_balances import create_opening_balances
        from app.schemas.opening_balances import OpeningBalanceCreate, OpeningBalanceLineCreate

        with self.Session() as db:
            with self.assertRaises(HTTPException) as ctx:
                create_opening_balances(
                    OpeningBalanceCreate(
                        date=date(2026, 4, 1),
                        lines=[OpeningBalanceLineCreate(account_id=1, amount=Decimal("100"))],
                    ),
                    db=db,
                )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("chart of accounts", ctx.exception.detail.lower())

    def test_create_opening_balances_posts_balanced_manual_journal(self):
        from app.models.accounts import Account, AccountType
        from app.models.transactions import Transaction
        from app.routes.opening_balances import create_opening_balances
        from app.schemas.opening_balances import OpeningBalanceCreate, OpeningBalanceLineCreate
        from app.services.chart_setup_status import mark_chart_setup_ready

        with self.Session() as db:
            bank = Account(name="Bank", account_number="090", account_type=AccountType.ASSET, is_active=True)
            equity = Account(name="Owner Funds", account_number="970", account_type=AccountType.EQUITY, is_active=True)
            db.add_all([bank, equity])
            db.commit()
            mark_chart_setup_ready(db, "template:xero")
            db.commit()

            result = create_opening_balances(
                OpeningBalanceCreate(
                    date=date(2026, 4, 1),
                    description="Opening balances",
                    reference="OB-2026",
                    lines=[
                        OpeningBalanceLineCreate(account_id=bank.id, amount=Decimal("500.00")),
                        OpeningBalanceLineCreate(account_id=equity.id, amount=Decimal("500.00")),
                    ],
                ),
                db=db,
            )
            txns = db.query(Transaction).filter(Transaction.source_type == "manual_journal").all()
            db.refresh(bank)
            db.refresh(equity)

        self.assertEqual(len(txns), 1)
        self.assertEqual(result.journal.reference, "OB-2026")
        self.assertEqual(Decimal(str(bank.balance)), Decimal("500.00"))
        self.assertEqual(Decimal(str(equity.balance)), Decimal("500.00"))

    def test_create_opening_balances_can_auto_balance_to_equity(self):
        from app.models.accounts import Account, AccountType
        from app.routes.opening_balances import create_opening_balances
        from app.schemas.opening_balances import OpeningBalanceCreate, OpeningBalanceLineCreate
        from app.services.chart_setup_status import mark_chart_setup_ready

        with self.Session() as db:
            bank = Account(name="Bank", account_number="090", account_type=AccountType.ASSET, is_active=True)
            loan = Account(name="Loan", account_number="900", account_type=AccountType.LIABILITY, is_active=True)
            equity = Account(name="Historical Adjustment", account_number="840", account_type=AccountType.EQUITY, is_active=True)
            db.add_all([bank, loan, equity])
            db.commit()
            mark_chart_setup_ready(db, "xero_import")
            db.commit()

            result = create_opening_balances(
                OpeningBalanceCreate(
                    date=date(2026, 4, 1),
                    lines=[
                        OpeningBalanceLineCreate(account_id=bank.id, amount=Decimal("800.00")),
                        OpeningBalanceLineCreate(account_id=loan.id, amount=Decimal("300.00")),
                    ],
                    auto_balance_account_id=equity.id,
                ),
                db=db,
            )

        self.assertEqual(len(result.journal.lines), 3)
        auto_line = next(line for line in result.journal.lines if line.account_id == equity.id)
        self.assertEqual(Decimal(str(auto_line.credit)), Decimal("500.00"))

    def test_create_opening_balances_rejects_non_equity_auto_balance_account(self):
        from app.models.accounts import Account, AccountType
        from app.routes.opening_balances import create_opening_balances
        from app.schemas.opening_balances import OpeningBalanceCreate, OpeningBalanceLineCreate
        from app.services.chart_setup_status import mark_chart_setup_ready

        with self.Session() as db:
            bank = Account(name="Bank", account_number="090", account_type=AccountType.ASSET, is_active=True)
            liability = Account(name="Loan", account_number="900", account_type=AccountType.LIABILITY, is_active=True)
            db.add_all([bank, liability])
            db.commit()
            mark_chart_setup_ready(db, "template:mas")
            db.commit()

            with self.assertRaises(HTTPException) as ctx:
                create_opening_balances(
                    OpeningBalanceCreate(
                        date=date(2026, 4, 1),
                        lines=[OpeningBalanceLineCreate(account_id=bank.id, amount=Decimal("100.00"))],
                        auto_balance_account_id=liability.id,
                    ),
                    db=db,
                )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("equity", ctx.exception.detail.lower())


if __name__ == "__main__":
    unittest.main()
