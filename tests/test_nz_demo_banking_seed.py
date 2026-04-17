import os
import sys
import types
import unittest
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class NzDemoBankingSeedTests(unittest.TestCase):
    def setUp(self):
        from app.models import (  # noqa: F401
            Account, Customer, Vendor, Item, Invoice, InvoiceLine,
            Payment, PaymentAllocation, Estimate, EstimateLine, Transaction,
            TransactionLine, Settings, GstCode, BankAccount, Reconciliation,
            BankTransaction, Company, PayRun, PayStub, Employee,
        )

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_demo_seed_adds_anz_bank_account_with_customer_and_vendor_transactions(self):
        import scripts.seed_database as seed_database
        import scripts.seed_irs_mock_data as seed_demo
        from app.models.accounts import Account
        from app.models.banking import BankAccount, BankTransaction

        seed_database.SessionLocal = self.Session
        seed_demo.SessionLocal = self.Session

        seed_database.seed()
        seed_demo.seed()

        with self.Session() as db:
            bank_account = db.query(BankAccount).one()
            account_090 = db.query(Account).filter(Account.account_number == "090").one()
            transactions = db.query(BankTransaction).filter(BankTransaction.bank_account_id == bank_account.id).order_by(BankTransaction.date.asc(), BankTransaction.id.asc()).all()

        self.assertEqual(bank_account.name, "ANZ Business Account")
        self.assertEqual(bank_account.bank_name, "ANZ")
        self.assertEqual(bank_account.last_four, "1208")
        self.assertTrue(bank_account.is_active)
        self.assertEqual(bank_account.account_id, account_090.id)
        self.assertGreaterEqual(len(transactions), 6)
        self.assertTrue(any(Decimal(str(txn.amount)) > 0 for txn in transactions))
        self.assertTrue(any(Decimal(str(txn.amount)) < 0 for txn in transactions))

        payees = {txn.payee for txn in transactions}
        self.assertIn("Basket Case", payees)
        self.assertIn("Ridgeway University", payees)
        self.assertIn("ABC Furniture", payees)
        self.assertIn("PowerDirect", payees)

        seeded_total = sum(Decimal(str(txn.amount)) for txn in transactions)
        self.assertEqual(Decimal(str(bank_account.balance)), seeded_total)


if __name__ == "__main__":
    unittest.main()
