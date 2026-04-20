import os
import sys
import types
import unittest
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

weasyprint_stub = types.ModuleType('weasyprint')
weasyprint_stub.HTML = object
sys.modules.setdefault('weasyprint', weasyprint_stub)

from app.database import Base


class BillPaymentUnallocatedAmountTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine(
            'sqlite:///:memory:',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_vendor_bill_payments_include_allocated_and_unallocated_amounts(self):
        from app.models.accounts import Account, AccountType
        from app.models.bills import Bill, BillPayment, BillPaymentAllocation, BillStatus
        from app.models.contacts import Vendor
        from app.routes.bill_payments import list_bill_payments

        with self.Session() as db:
            expense = Account(name='Expenses', account_number='6000', account_type=AccountType.EXPENSE)
            db.add(expense)
            db.commit()

            vendor = Vendor(name='Harbour Supplies', default_expense_account_id=expense.id)
            db.add(vendor)
            db.commit()

            bill = Bill(
                bill_number='B-001',
                vendor_id=vendor.id,
                status=BillStatus.UNPAID,
                date=date(2026, 4, 20),
                due_date=date(2026, 5, 20),
                terms='Net 30',
                subtotal=Decimal('100.00'),
                tax_rate=Decimal('0.1500'),
                tax_amount=Decimal('15.00'),
                total=Decimal('115.00'),
                amount_paid=Decimal('0.00'),
                balance_due=Decimal('115.00'),
            )
            db.add(bill)
            db.commit()

            payment = BillPayment(vendor_id=vendor.id, date=date(2026, 4, 21), amount=Decimal('200.00'), method='EFT')
            db.add(payment)
            db.flush()
            db.add(BillPaymentAllocation(bill_payment_id=payment.id, bill_id=bill.id, amount=Decimal('115.00')))
            db.commit()

            rows = list_bill_payments(vendor_id=vendor.id, db=db, auth=True)

        self.assertEqual(len(rows), 1)
        self.assertEqual(Decimal(str(rows[0].allocated_amount)), Decimal('115.00'))
        self.assertEqual(Decimal(str(rows[0].unallocated_amount)), Decimal('85.00'))


if __name__ == '__main__':
    unittest.main()
