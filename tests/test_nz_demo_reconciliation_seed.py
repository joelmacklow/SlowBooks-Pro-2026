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


class NzDemoReconciliationSeedTests(unittest.TestCase):
    def setUp(self):
        from app.models import (  # noqa: F401
            Account, Customer, Vendor, Item, Invoice, InvoiceLine,
            Payment, PaymentAllocation, Estimate, EstimateLine, Transaction,
            TransactionLine, Settings, GstCode, BankAccount, Reconciliation,
            BankTransaction, Company, PayRun, PayStub, Employee,
            Bill, BillLine, BillPayment, BillPaymentAllocation,
        )

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_demo_seed_creates_reconciliation_ready_ar_and_ap_cash_activity(self):
        import scripts.seed_database as seed_database
        import scripts.seed_irs_mock_data as seed_demo
        from app.models.bills import Bill, BillPayment
        from app.models.banking import BankAccount, BankTransaction
        from app.models.payments import Payment
        from app.routes.banking import (
            complete_reconciliation,
            create_reconciliation,
            get_reconciliation_transactions,
            toggle_cleared,
        )
        from app.schemas.banking import ReconciliationCreate

        seed_database.SessionLocal = self.Session
        seed_demo.SessionLocal = self.Session

        seed_database.seed()
        seed_demo.seed()

        with self.Session() as db:
            bills = db.query(Bill).order_by(Bill.bill_number).all()
            bill_payments = db.query(BillPayment).order_by(BillPayment.id).all()
            customer_payments = db.query(Payment).order_by(Payment.id).all()
            bank_account = db.query(BankAccount).filter(BankAccount.name == 'ANZ Business Account').one()
            bank_txns = db.query(BankTransaction).filter(BankTransaction.bank_account_id == bank_account.id).order_by(BankTransaction.date.asc(), BankTransaction.id.asc()).all()

            self.assertEqual(len(bills), 3)
            self.assertEqual(len(bill_payments), 3)
            self.assertEqual(len(customer_payments), 5)
            self.assertEqual(len(bank_txns), len(customer_payments) + len(bill_payments))
            positive_txns = [txn for txn in bank_txns if Decimal(str(txn.amount)) > 0]
            negative_txns = [txn for txn in bank_txns if Decimal(str(txn.amount)) < 0]
            reconciled_txns = [txn for txn in bank_txns if txn.reconciled]
            unreconciled_txns = [txn for txn in bank_txns if not txn.reconciled]
            self.assertEqual(len(positive_txns), len(customer_payments))
            self.assertEqual(len(negative_txns), len(bill_payments))
            self.assertEqual({txn.payee for txn in negative_txns}, {'ABC Furniture', 'PowerDirect', 'Net Connect'})
            self.assertTrue(reconciled_txns)
            self.assertTrue(unreconciled_txns)

            recon = create_reconciliation(
                ReconciliationCreate(
                    bank_account_id=bank_account.id,
                    statement_date=bank_txns[-1].date,
                    statement_balance=bank_account.balance,
                ),
                db=db,
            )
            initial = get_reconciliation_transactions(recon.id, db=db)
            self.assertEqual(len(initial['transactions']), len(bank_txns))
            self.assertGreater(initial['cleared_total'], 0)
            self.assertGreater(initial['difference'], 0)

            for txn in unreconciled_txns:
                toggle_cleared(recon.id, txn.id, db=db)

            refreshed = get_reconciliation_transactions(recon.id, db=db)
            self.assertAlmostEqual(refreshed['difference'], 0.0, places=2)

            result = complete_reconciliation(recon.id, db=db)
            self.assertEqual(result['status'], 'completed')

    def test_demo_seed_rerun_does_not_duplicate_reconciliation_seed_records(self):
        import scripts.seed_database as seed_database
        import scripts.seed_irs_mock_data as seed_demo
        from app.models.bills import Bill, BillPayment
        from app.models.banking import BankAccount, BankTransaction
        from app.models.invoices import Invoice
        from app.models.payments import Payment

        seed_database.SessionLocal = self.Session
        seed_demo.SessionLocal = self.Session

        seed_database.seed()
        seed_demo.seed()
        seed_demo.seed()

        with self.Session() as db:
            self.assertEqual(db.query(Invoice).count(), 10)
            self.assertEqual(db.query(Payment).count(), 5)
            self.assertEqual(db.query(Bill).count(), 3)
            self.assertEqual(db.query(BillPayment).count(), 3)
            self.assertEqual(db.query(BankAccount).count(), 1)
            self.assertEqual(db.query(BankTransaction).count(), 8)


if __name__ == '__main__':
    unittest.main()
