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


class GstReturnsOverviewTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def _seed(self, db, gst_period="six-monthly"):
        from app.models.accounts import Account, AccountType
        from app.models.banking import BankAccount
        from app.models.contacts import Customer, Vendor
        from app.models.settings import Settings

        customer = Customer(name="Aroha Ltd")
        vendor = Vendor(name="Harbour Supplies")
        db.add_all([
            customer,
            vendor,
            Account(name="Business Bank Account", account_number="090", account_type=AccountType.ASSET),
            Account(name="Accounts Receivable", account_number="1100", account_type=AccountType.ASSET),
            Account(name="Accounts Payable", account_number="2000", account_type=AccountType.LIABILITY),
            Account(name="GST", account_number="2200", account_type=AccountType.LIABILITY),
            Account(name="Sales", account_number="4000", account_type=AccountType.INCOME),
            Account(name="Expenses", account_number="6000", account_type=AccountType.EXPENSE),
            Settings(key="gst_basis", value="invoice"),
            Settings(key="gst_period", value=gst_period),
            Settings(key="gst_number", value="123-456-789"),
            Settings(key="company_name", value="SlowBooks NZ"),
        ])
        db.commit()
        bank_account = BankAccount(
            name="Operating Account",
            account_id=db.query(Account).filter(Account.account_number == "090").one().id,
            bank_name="ASB",
            last_four="1234",
            balance=Decimal("0.00"),
        )
        db.add(bank_account)
        db.commit()
        return customer, vendor, bank_account


    def _confirm_return_only(self, db, customer, start_date: date, end_date: date, box9_adjustments=Decimal("5.00"), box13_adjustments=Decimal("2.00")):
        from app.routes.invoices import create_invoice
        from app.routes.reports import GstReturnConfirmRequest, confirm_gst_return
        from app.schemas.invoices import InvoiceCreate, InvoiceLineCreate

        create_invoice(InvoiceCreate(
            customer_id=customer.id,
            date=start_date,
            lines=[InvoiceLineCreate(description="Standard sale", quantity=1, rate=Decimal("100"), gst_code="GST15")],
        ), db=db)
        return confirm_gst_return(GstReturnConfirmRequest(
            start_date=start_date,
            end_date=end_date,
            box9_adjustments=box9_adjustments,
            box13_adjustments=box13_adjustments,
        ), db=db, auth={'user_id': 1})

    def _confirm_period(self, db, customer, bank_account, start_date: date, end_date: date, settlement_date: date):
        from app.models.banking import BankTransaction
        from app.routes.invoices import create_invoice
        from app.routes.reports import GstSettlementConfirmRequest, confirm_gst_settlement
        from app.schemas.invoices import InvoiceCreate, InvoiceLineCreate

        create_invoice(InvoiceCreate(
            customer_id=customer.id,
            date=start_date,
            lines=[InvoiceLineCreate(description="Standard sale", quantity=1, rate=Decimal("100"), gst_code="GST15")],
        ), db=db)
        bank_txn = BankTransaction(
            bank_account_id=bank_account.id,
            date=settlement_date,
            amount=Decimal("-15.00"),
            payee="Inland Revenue",
            description="GST payment",
            reconciled=True,
        )
        db.add(bank_txn)
        db.commit()
        from app.routes.reports import GstReturnConfirmRequest, confirm_gst_return
        confirm_gst_return(GstReturnConfirmRequest(
            start_date=start_date,
            end_date=end_date,
            box9_adjustments=Decimal("0.00"),
            box13_adjustments=Decimal("0.00"),
        ), db=db, auth={'user_id': 1})
        confirm_gst_settlement(GstSettlementConfirmRequest(
            start_date=start_date,
            end_date=end_date,
            bank_transaction_id=bank_txn.id,
        ), db=db)

    def test_overview_returns_open_periods_and_confirmed_history_groups(self):
        from app.routes.reports import gst_returns_overview

        with self.Session() as db:
            customer, _vendor, bank_account = self._seed(db, gst_period="six-monthly")
            self._confirm_period(
                db,
                customer,
                bank_account,
                start_date=date(2025, 10, 1),
                end_date=date(2026, 3, 31),
                settlement_date=date(2026, 5, 7),
            )

            overview = gst_returns_overview(as_of_date=date(2026, 10, 10), db=db, auth={'user_id': 1})

        self.assertEqual(len(overview["open_periods"]), 2)
        self.assertEqual(overview["open_periods"][0]["period_label"], "1 Apr 2026 - 30 Sep 2026")
        self.assertEqual(overview["open_periods"][0]["status"], "due")
        self.assertEqual(overview["open_periods"][0]["due_date"], "2026-10-28")
        self.assertEqual(overview["open_periods"][1]["status"], "current_period")
        self.assertEqual(overview["open_periods"][1]["period_label"], "1 Oct 2026 - 31 Mar 2027")

        self.assertEqual(len(overview["historical_groups"]), 1)
        self.assertEqual(overview["historical_groups"][0]["label"], "2026 financial year")
        self.assertEqual(overview["historical_groups"][0]["returns"][0]["period_label"], "1 Oct 2025 - 31 Mar 2026")
        self.assertEqual(overview["historical_groups"][0]["returns"][0]["status"], "confirmed")
        self.assertEqual(overview["historical_groups"][0]["returns"][0]["net_gst"], 15.0)

    def test_transactions_endpoint_paginates_source_items(self):
        from app.routes.invoices import create_invoice
        from app.routes.reports import gst_return_transactions
        from app.schemas.invoices import InvoiceCreate, InvoiceLineCreate

        with self.Session() as db:
            customer, _vendor, _bank_account = self._seed(db, gst_period="two-monthly")
            create_invoice(InvoiceCreate(
                customer_id=customer.id,
                date=date(2026, 4, 1),
                lines=[InvoiceLineCreate(description="First sale", quantity=1, rate=Decimal("100"), gst_code="GST15")],
            ), db=db)
            create_invoice(InvoiceCreate(
                customer_id=customer.id,
                date=date(2026, 4, 2),
                lines=[InvoiceLineCreate(description="Second sale", quantity=1, rate=Decimal("200"), gst_code="GST15")],
            ), db=db)

            response = gst_return_transactions(
                start_date=date(2026, 4, 1),
                end_date=date(2026, 4, 30),
                page=2,
                page_size=1,
                db=db,
                auth={'user_id': 1},
            )

        self.assertEqual(response["page"], 2)
        self.assertEqual(response["page_size"], 1)
        self.assertEqual(response["total_count"], 2)
        self.assertEqual(response["total_pages"], 2)
        self.assertEqual(len(response["items"]), 1)
        self.assertEqual(response["items"][0]["number"], "1002")

    def test_confirmed_return_without_settlement_moves_to_history_and_keeps_adjustments(self):
        from app.routes.reports import gst_returns_overview

        with self.Session() as db:
            customer, _vendor, _bank_account = self._seed(db, gst_period="six-monthly")
            self._confirm_return_only(
                db,
                customer,
                start_date=date(2026, 4, 1),
                end_date=date(2026, 9, 30),
                box9_adjustments=Decimal("5.00"),
                box13_adjustments=Decimal("2.00"),
            )

            overview = gst_returns_overview(as_of_date=date(2026, 10, 10), db=db, auth={'user_id': 1})

        self.assertEqual(len(overview["open_periods"]), 1)
        self.assertEqual(overview["open_periods"][0]["period_label"], "1 Oct 2026 - 31 Mar 2027")
        historical = overview["historical_groups"][0]["returns"][0]
        self.assertEqual(historical["period_label"], "1 Apr 2026 - 30 Sep 2026")
        self.assertEqual(historical["box9_adjustments"], "5.00")
        self.assertEqual(historical["box13_adjustments"], "2.00")
        self.assertEqual(historical["status"], "confirmed")


if __name__ == "__main__":
    unittest.main()
