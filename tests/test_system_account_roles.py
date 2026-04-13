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
from app.models.contacts import Customer, Vendor
from app.models.invoices import Invoice, InvoiceStatus
from app.models.bills import Bill, BillStatus
from app.models.settings import Settings


class SystemAccountRoleTests(unittest.TestCase):
    def setUp(self):
        from app.models.payments import Payment, PaymentAllocation  # noqa: F401
        from app.models.transactions import Transaction, TransactionLine  # noqa: F401
        from app.models.payroll import Employee, PayRun, PayStub  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def _set_role(self, db, key, account_id):
        db.add(Settings(key=key, value=str(account_id)))
        db.commit()

    def test_explicit_setting_mapping_overrides_legacy_account_number(self):
        from app.services.accounting import get_ar_account_id

        with self.Session() as db:
            legacy = Account(name="Accounts Receivable", account_number="1100", account_type=AccountType.ASSET)
            custom = Account(name="Trade Debtors", account_number="610", account_type=AccountType.ASSET)
            db.add_all([legacy, custom])
            db.commit()
            custom_id = custom.id
            self._set_role(db, "system_account_accounts_receivable_id", custom.id)

            resolved_id = get_ar_account_id(db)

        self.assertEqual(resolved_id, custom_id)

    def test_payment_route_uses_mapped_accounts_without_fixed_numbers(self):
        from app.routes.payments import create_payment
        from app.schemas.payments import PaymentAllocationCreate, PaymentCreate

        with self.Session() as db:
            customer = Customer(name="Aroha Ltd")
            ar = Account(name="Trade Debtors", account_number="610", account_type=AccountType.ASSET)
            clearing = Account(name="Receipt Clearing", account_number="615", account_type=AccountType.ASSET)
            db.add_all([customer, ar, clearing])
            db.commit()
            db.refresh(customer)
            db.refresh(ar)
            db.refresh(clearing)
            ar_id = ar.id
            clearing_id = clearing.id
            self._set_role(db, "system_account_accounts_receivable_id", ar.id)
            self._set_role(db, "system_account_undeposited_funds_id", clearing.id)

            invoice = Invoice(
                invoice_number="1001",
                customer_id=customer.id,
                date=date(2026, 4, 1),
                status=InvoiceStatus.SENT,
                subtotal=Decimal("100.00"),
                tax_rate=Decimal("0"),
                tax_amount=Decimal("0"),
                total=Decimal("100.00"),
                balance_due=Decimal("100.00"),
                amount_paid=Decimal("0.00"),
            )
            db.add(invoice)
            db.commit()
            db.refresh(invoice)

            payment = create_payment(PaymentCreate(
                customer_id=customer.id,
                date=date(2026, 4, 15),
                amount=Decimal("100.00"),
                allocations=[PaymentAllocationCreate(invoice_id=invoice.id, amount=Decimal("100.00"))],
            ), db=db)
            payment_row = db.query(__import__("app.models.payments", fromlist=["Payment"]).Payment).filter_by(id=payment.id).one()
            lines = payment_row.transaction.lines
            account_ids = {line.account_id for line in lines}

        self.assertEqual(account_ids, {ar_id, clearing_id})

    def test_bill_payment_route_uses_mapped_ap_and_default_bank_accounts(self):
        from app.routes.bill_payments import create_bill_payment
        from app.schemas.bills import BillPaymentAllocationCreate, BillPaymentCreate

        with self.Session() as db:
            vendor = Vendor(name="Harbour Supplies")
            ap = Account(name="Trade Creditors", account_number="810", account_type=AccountType.LIABILITY)
            bank = Account(name="Operating Account", account_number="090", account_type=AccountType.ASSET)
            db.add_all([vendor, ap, bank])
            db.commit()
            db.refresh(vendor)
            db.refresh(ap)
            db.refresh(bank)
            ap_id = ap.id
            bank_id = bank.id
            self._set_role(db, "system_account_accounts_payable_id", ap.id)
            self._set_role(db, "system_account_default_bank_id", bank.id)

            bill = Bill(
                bill_number="B-1",
                vendor_id=vendor.id,
                date=date(2026, 4, 1),
                status=BillStatus.UNPAID,
                subtotal=Decimal("100.00"),
                tax_rate=Decimal("0"),
                tax_amount=Decimal("0"),
                total=Decimal("100.00"),
                balance_due=Decimal("100.00"),
                amount_paid=Decimal("0.00"),
            )
            db.add(bill)
            db.commit()
            db.refresh(bill)

            payment = create_bill_payment(BillPaymentCreate(
                vendor_id=vendor.id,
                date=date(2026, 4, 15),
                amount=Decimal("100.00"),
                allocations=[BillPaymentAllocationCreate(bill_id=bill.id, amount=Decimal("100.00"))],
            ), db=db)
            payment_row = db.query(__import__("app.models.bills", fromlist=["BillPayment"]).BillPayment).filter_by(id=payment.id).one()
            lines = payment_row.transaction.lines
            account_ids = {line.account_id for line in lines}

        self.assertEqual(account_ids, {ap_id, bank_id})

    def test_payroll_process_uses_mapped_roles_without_default_numbers(self):
        from app.routes.employees import create_employee
        from app.routes.payroll import create_pay_run, process_pay_run
        from app.schemas.payroll import EmployeeCreate, PayRunCreate, PayStubInput

        with self.Session() as db:
            wages = Account(name="Salaries", account_number="477", account_type=AccountType.EXPENSE)
            employer_ks = Account(name="KiwiSaver Employer Contributions", account_number="478", account_type=AccountType.EXPENSE)
            paye = Account(name="PAYE Liability", account_number="820", account_type=AccountType.LIABILITY)
            ks = Account(name="KiwiSaver Liability", account_number="821", account_type=AccountType.LIABILITY)
            esct = Account(name="ESCT Liability", account_number="822", account_type=AccountType.LIABILITY)
            child_support = Account(name="Child Support Liability", account_number="823", account_type=AccountType.LIABILITY)
            clearing = Account(name="Net Wages Clearing", account_number="824", account_type=AccountType.LIABILITY)
            db.add_all([wages, employer_ks, paye, ks, esct, child_support, clearing])
            db.commit()
            wages_id = wages.id
            employer_ks_id = employer_ks.id
            paye_id = paye.id
            ks_id = ks.id
            esct_id = esct.id
            clearing_id = clearing.id
            for key, account in {
                "system_account_wages_expense_id": wages,
                "system_account_employer_kiwisaver_expense_id": employer_ks,
                "system_account_paye_payable_id": paye,
                "system_account_kiwisaver_payable_id": ks,
                "system_account_esct_payable_id": esct,
                "system_account_child_support_payable_id": child_support,
                "system_account_payroll_clearing_id": clearing,
            }.items():
                self._set_role(db, key, account.id)

            employee = create_employee(EmployeeCreate(
                first_name="Aroha",
                last_name="Ngata",
                pay_type="salary",
                pay_rate=78000,
                tax_code="M",
                kiwisaver_enrolled=True,
                kiwisaver_rate="0.0350",
                pay_frequency="fortnightly",
                start_date=date(2026, 4, 1),
            ), db=db)
            draft = create_pay_run(PayRunCreate(
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 14),
                pay_date=date(2026, 4, 15),
                stubs=[PayStubInput(employee_id=employee.id)],
            ), db=db)
            processed = process_pay_run(draft.id, db=db)
            pay_run_row = db.query(__import__("app.models.payroll", fromlist=["PayRun"]).PayRun).filter_by(id=processed.id).one()
            account_ids = {line.account_id for line in pay_run_row.transaction.lines}

        self.assertTrue({wages_id, employer_ks_id, paye_id, ks_id, esct_id, clearing_id}.issubset(account_ids))


if __name__ == "__main__":
    unittest.main()
