import os
import sys
import types
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class NZReceiptsCleanupTests(unittest.TestCase):
    def setUp(self):
        from app.models import (  # noqa: F401
            Account, Customer, Invoice, Payment, PaymentAllocation, Settings, Transaction, TransactionLine,
        )

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def _set_role(self, db, key, account_id):
        from app.models.settings import Settings

        db.add(Settings(key=key, value=str(account_id)))
        db.commit()

    def _base_setup(self, db):
        from app.models.accounts import Account, AccountType
        from app.models.contacts import Customer
        from app.models.invoices import Invoice, InvoiceStatus

        customer = Customer(name="Aroha Ltd")
        ar = Account(name="Trade Debtors", account_number="610", account_type=AccountType.ASSET, is_active=True)
        clearing = Account(name="Undeposited Funds / Receipt Clearing", account_number="615", account_type=AccountType.ASSET, is_active=True)
        bank = Account(name="Operating Account", account_number="090", account_type=AccountType.ASSET, is_active=True)
        db.add_all([customer, ar, clearing, bank])
        db.commit()

        self._set_role(db, "system_account_accounts_receivable_id", ar.id)
        self._set_role(db, "system_account_undeposited_funds_id", clearing.id)

        invoice = Invoice(
            invoice_number="INV-1001",
            customer_id=customer.id,
            status=InvoiceStatus.SENT,
            date=date(2026, 4, 1),
            subtotal=Decimal("100.00"),
            tax_rate=Decimal("0"),
            tax_amount=Decimal("0"),
            total=Decimal("100.00"),
            amount_paid=Decimal("0"),
            balance_due=Decimal("100.00"),
        )
        db.add(invoice)
        db.commit()
        return customer, invoice, clearing, bank

    def test_cash_receipts_stay_in_receipt_clearing_and_show_in_pending_deposits(self):
        from app.models.transactions import Transaction
        from app.models.payments import Payment
        from app.routes.deposits import list_pending_deposits
        from app.routes.payments import create_payment
        from app.schemas.payments import PaymentAllocationCreate, PaymentCreate

        with self.Session() as db:
            customer, invoice, clearing, _bank = self._base_setup(db)
            with patch("app.routes.payments.check_closing_date", lambda *_args, **_kwargs: None):
                payment = create_payment(
                    PaymentCreate(
                        customer_id=customer.id,
                        date=date(2026, 4, 10),
                        amount=Decimal("100.00"),
                        method="Cash",
                        allocations=[PaymentAllocationCreate(invoice_id=invoice.id, amount=Decimal("100.00"))],
                    ),
                    db=db,
                    auth=None,
                )
            pending = list_pending_deposits(db=db, auth=None)
            payment_row = db.query(Payment).filter(Payment.id == payment.id).one()
            txn = db.query(Transaction).filter(Transaction.id == payment_row.transaction_id).one()
            debit_line = next(line for line in txn.lines if Decimal(str(line.debit or 0)) > 0)

        self.assertEqual(debit_line.account_id, clearing.id)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].payment_id, payment.id)
        self.assertEqual(pending[0].method, "Cash")

    def test_eft_receipts_require_a_bank_account_when_recorded_manually(self):
        from app.routes.payments import create_payment
        from app.schemas.payments import PaymentAllocationCreate, PaymentCreate

        with self.Session() as db:
            customer, invoice, _clearing, _bank = self._base_setup(db)
            with patch("app.routes.payments.check_closing_date", lambda *_args, **_kwargs: None):
                with self.assertRaises(HTTPException) as ctx:
                    create_payment(
                        PaymentCreate(
                            customer_id=customer.id,
                            date=date(2026, 4, 10),
                            amount=Decimal("100.00"),
                            method="EFT",
                            allocations=[PaymentAllocationCreate(invoice_id=invoice.id, amount=Decimal("100.00"))],
                        ),
                        db=db,
                        auth=None,
                    )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("bank account", ctx.exception.detail.lower())

    def test_direct_bank_eftpos_receipts_do_not_appear_in_pending_deposits(self):
        from app.routes.deposits import list_pending_deposits
        from app.routes.payments import create_payment
        from app.schemas.payments import PaymentAllocationCreate, PaymentCreate

        with self.Session() as db:
            customer, invoice, _clearing, bank = self._base_setup(db)
            with patch("app.routes.payments.check_closing_date", lambda *_args, **_kwargs: None):
                create_payment(
                    PaymentCreate(
                        customer_id=customer.id,
                        date=date(2026, 4, 10),
                        amount=Decimal("100.00"),
                        method="EFTPOS/Card",
                        deposit_to_account_id=bank.id,
                        allocations=[PaymentAllocationCreate(invoice_id=invoice.id, amount=Decimal("100.00"))],
                    ),
                    db=db,
                    auth=None,
                )
            pending = list_pending_deposits(db=db, auth=None)

        self.assertEqual(pending, [])

    def test_bulk_receipt_allocation_requires_bank_for_electronic_methods(self):
        from app.routes.batch_payments import create_batch_payment
        from app.schemas.batch_payments import BatchPaymentAllocationCreate, BatchPaymentCreate

        with self.Session() as db:
            customer, invoice, _clearing, _bank = self._base_setup(db)
            with patch("app.routes.batch_payments.check_closing_date", lambda *_args, **_kwargs: None):
                with self.assertRaises(HTTPException) as ctx:
                    create_batch_payment(
                        BatchPaymentCreate(
                            date=date(2026, 4, 12),
                            method="EFT",
                            allocations=[
                                BatchPaymentAllocationCreate(
                                    customer_id=customer.id,
                                    invoice_id=invoice.id,
                                    amount=Decimal("100.00"),
                                )
                            ],
                        ),
                        db=db,
                        auth=None,
                    )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("bank account", ctx.exception.detail.lower())


if __name__ == "__main__":
    unittest.main()
