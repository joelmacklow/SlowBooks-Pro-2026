import os
import sys
import types
import unittest
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class FrozenDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 4, 21)


class DashboardSnapshotMetricsTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401
        from app.models.accounts import Account, AccountType
        from app.models.banking import BankAccount, BankTransaction, Reconciliation, ReconciliationStatus
        from app.models.contacts import Customer
        from app.models.invoices import Invoice, InvoiceStatus
        from app.models.payments import Payment
        from app.models.settings import Settings
        from app.services.accounting import create_journal_entry

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

        with self.Session() as db:
            customer = Customer(name="Acme Ltd", email="accounts@acme.test", is_active=True)
            bank = Account(name="Business Bank", account_number="090", account_type=AccountType.ASSET, is_active=True)
            sales = Account(name="Sales", account_number="200", account_type=AccountType.INCOME, is_active=True)
            hosting = Account(name="Hosting", account_number="610", account_type=AccountType.EXPENSE, is_active=True)
            wages = Account(name="Wages", account_number="620", account_type=AccountType.EXPENSE, is_active=True)
            purchases = Account(name="Purchases", account_number="500", account_type=AccountType.COGS, is_active=True)
            loan = Account(name="Term Loan", account_number="850", account_type=AccountType.LIABILITY, is_active=True)
            db.add_all([customer, bank, sales, hosting, wages, purchases, loan])
            db.flush()

            db.add(BankAccount(
                name="Main Bank",
                account_id=bank.id,
                bank_name="ANZ",
                last_four="1208",
                balance=Decimal("2140.00"),
                is_active=True,
            ))
            db.flush()

            db.add_all([
                Settings(key="financial_year_start", value="04-01"),
                Settings(key="financial_year_end", value="03-31"),
            ])

            create_journal_entry(db, date(2025, 11, 10), "November sale", [
                {"account_id": bank.id, "debit": Decimal("700.00"), "credit": Decimal("0.00")},
                {"account_id": sales.id, "debit": Decimal("0.00"), "credit": Decimal("700.00")},
            ])
            create_journal_entry(db, date(2025, 12, 10), "December hosting", [
                {"account_id": hosting.id, "debit": Decimal("100.00"), "credit": Decimal("0.00")},
                {"account_id": bank.id, "debit": Decimal("0.00"), "credit": Decimal("100.00")},
            ])
            create_journal_entry(db, date(2026, 1, 15), "January sale", [
                {"account_id": bank.id, "debit": Decimal("300.00"), "credit": Decimal("0.00")},
                {"account_id": sales.id, "debit": Decimal("0.00"), "credit": Decimal("300.00")},
            ])
            create_journal_entry(db, date(2026, 2, 20), "February purchases", [
                {"account_id": purchases.id, "debit": Decimal("250.00"), "credit": Decimal("0.00")},
                {"account_id": bank.id, "debit": Decimal("0.00"), "credit": Decimal("250.00")},
            ])
            create_journal_entry(db, date(2026, 3, 10), "March sale", [
                {"account_id": bank.id, "debit": Decimal("1000.00"), "credit": Decimal("0.00")},
                {"account_id": sales.id, "debit": Decimal("0.00"), "credit": Decimal("1000.00")},
            ])
            create_journal_entry(db, date(2026, 4, 5), "April sale", [
                {"account_id": bank.id, "debit": Decimal("200.00"), "credit": Decimal("0.00")},
                {"account_id": sales.id, "debit": Decimal("0.00"), "credit": Decimal("200.00")},
            ])
            create_journal_entry(db, date(2026, 4, 12), "April hosting", [
                {"account_id": hosting.id, "debit": Decimal("150.00"), "credit": Decimal("0.00")},
                {"account_id": bank.id, "debit": Decimal("0.00"), "credit": Decimal("150.00")},
            ])
            create_journal_entry(db, date(2026, 4, 18), "April wages", [
                {"account_id": wages.id, "debit": Decimal("80.00"), "credit": Decimal("0.00")},
                {"account_id": bank.id, "debit": Decimal("0.00"), "credit": Decimal("80.00")},
            ])

            db.add_all([
                Invoice(
                    invoice_number="INV-001",
                    customer_id=customer.id,
                    status=InvoiceStatus.SENT,
                    date=date(2026, 4, 1),
                    due_date=date(2026, 4, 10),
                    total=Decimal("300.00"),
                    balance_due=Decimal("300.00"),
                ),
                Invoice(
                    invoice_number="INV-002",
                    customer_id=customer.id,
                    status=InvoiceStatus.PARTIAL,
                    date=date(2026, 4, 5),
                    due_date=date(2026, 4, 30),
                    total=Decimal("500.00"),
                    amount_paid=Decimal("300.00"),
                    balance_due=Decimal("200.00"),
                ),
                Payment(
                    customer_id=customer.id,
                    date=date(2026, 4, 8),
                    amount=Decimal("300.00"),
                    method="Bank Transfer",
                ),
            ])
            db.flush()

            bank_account = db.query(BankAccount).first()
            db.add_all([
                BankTransaction(
                    bank_account_id=bank_account.id,
                    date=date(2026, 4, 20),
                    amount=Decimal("-53.91"),
                    payee="Hosting Supplier",
                    description="Pending hosting invoice",
                    reconciled=False,
                    match_status="unmatched",
                ),
                Reconciliation(
                    bank_account_id=bank_account.id,
                    statement_date=date(2026, 4, 20),
                    statement_balance=Decimal("2100.00"),
                    status=ReconciliationStatus.IN_PROGRESS,
                ),
            ])
            db.commit()

    def test_dashboard_returns_rich_summary_for_financial_viewers(self):
        from app.routes.dashboard import get_dashboard

        with mock.patch("app.routes.dashboard.date", FrozenDate), mock.patch("app.services.dashboard_metrics.date", FrozenDate):
            with self.Session() as db:
                payload = get_dashboard(
                    db=db,
                    auth=SimpleNamespace(permissions={"dashboard.financials.view"}),
                )

        self.assertTrue(payload["financial_overview_available"])
        self.assertEqual(payload["customer_count"], 1)
        self.assertEqual(payload["total_receivables"], 500.0)
        self.assertEqual(payload["invoice_summary"]["awaiting_payment_count"], 2)
        self.assertEqual(payload["invoice_summary"]["overdue_count"], 1)
        self.assertEqual(payload["invoice_summary"]["overdue_value"], 300.0)
        self.assertEqual(payload["bank_accounts"][0]["unreconciled_count"], 1)
        self.assertEqual(payload["bank_accounts"][0]["balance_difference"], 40.0)
        watchlist = {row["account_number"]: row for row in payload["watchlist"]}
        self.assertEqual(watchlist["200"]["this_month"], 200.0)
        self.assertEqual(watchlist["200"]["ytd"], 1500.0)
        self.assertEqual(watchlist["610"]["this_month"], 150.0)

    def test_dashboard_charts_return_profit_and_cash_flow_summaries(self):
        from app.routes.dashboard import get_dashboard_charts

        with mock.patch("app.routes.dashboard.date", FrozenDate), mock.patch("app.services.dashboard_metrics.date", FrozenDate):
            with self.Session() as db:
                payload = get_dashboard_charts(
                    db=db,
                    auth=SimpleNamespace(permissions={"dashboard.financials.view"}),
                )

        self.assertIn("profit_summary", payload)
        self.assertIn("cash_flow", payload)
        self.assertEqual(payload["profit_summary"]["period_label"], "1 Apr - 21 Apr 2026")
        self.assertEqual(payload["profit_summary"]["income"], 200.0)
        self.assertEqual(payload["profit_summary"]["expenses"], 230.0)
        self.assertEqual(payload["profit_summary"]["net_profit"], -30.0)
        self.assertEqual(payload["cash_flow"]["cash_in_total"], 2200.0)
        self.assertEqual(payload["cash_flow"]["cash_out_total"], 580.0)
        self.assertEqual(payload["cash_flow"]["net_total"], 1620.0)
        self.assertEqual(len(payload["cash_flow"]["months"]), 6)
        self.assertEqual(payload["cash_flow"]["months"][-1]["month"], "Apr")

    def test_dashboard_watchlist_prefers_favorite_accounts_and_keeps_zero_activity_rows(self):
        from app.models.accounts import Account
        from app.routes.dashboard import get_dashboard

        with self.Session() as db:
            bank = db.query(Account).filter(Account.account_number == "090").one()
            loan = db.query(Account).filter(Account.account_number == "850").one()
            bank.is_dashboard_favorite = True
            loan.is_dashboard_favorite = True
            db.commit()

        with mock.patch("app.routes.dashboard.date", FrozenDate), mock.patch("app.services.dashboard_metrics.date", FrozenDate):
            with self.Session() as db:
                payload = get_dashboard(
                    db=db,
                    auth=SimpleNamespace(permissions={"dashboard.financials.view"}),
                )

        self.assertEqual([row["account_number"] for row in payload["watchlist"]], ["090", "850"])
        bank_row = payload["watchlist"][0]
        loan_row = payload["watchlist"][1]
        self.assertEqual(bank_row["this_month"], -30.0)
        self.assertEqual(bank_row["ytd"], 1020.0)
        self.assertEqual(loan_row["this_month"], 0.0)
        self.assertEqual(loan_row["ytd"], 0.0)

    def test_dashboard_hides_financial_summary_without_permission(self):
        from app.routes.dashboard import get_dashboard

        with self.Session() as db:
            payload = get_dashboard(db=db, auth=SimpleNamespace(permissions=set()))

        self.assertFalse(payload["financial_overview_available"])
        self.assertEqual(payload["customer_count"], 1)
        self.assertNotIn("invoice_summary", payload)
        self.assertNotIn("bank_accounts", payload)


if __name__ == "__main__":
    unittest.main()
