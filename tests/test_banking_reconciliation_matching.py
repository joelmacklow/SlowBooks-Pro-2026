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


class BankingReconciliationMatchingTests(unittest.TestCase):
    def setUp(self):
        from app.models import (  # noqa: F401
            Account, BankAccount, BankTransaction, Bill, BillLine, BillPayment, BillPaymentAllocation,
            CreditApplication, CreditMemo, CreditMemoLine,
            Customer, Invoice, InvoiceLine, Payment, PaymentAllocation, Settings, Transaction, TransactionLine, Vendor,
        )

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def _set_role(self, db, key, account_id):
        from app.models.settings import Settings
        db.add(Settings(key=key, value=str(account_id)))
        db.commit()

    def test_suggestions_prefer_reference_match_over_amount_only(self):
        from app.models.accounts import Account, AccountType
        from app.models.banking import BankAccount, BankTransaction
        from app.models.contacts import Customer
        from app.models.invoices import Invoice, InvoiceStatus
        from app.services.reconciliation_matching import suggestion_candidates

        with self.Session() as db:
            asset = Account(name='Operating', account_number='090', account_type=AccountType.ASSET, is_active=True)
            db.add(asset)
            db.commit()
            bank_account = BankAccount(name='ANZ', account_id=asset.id, bank_name='ANZ', last_four='1208', balance=Decimal('0'), is_active=True)
            db.add(bank_account)
            db.commit()

            customer_a = Customer(name='Learn Innovations Limited')
            customer_b = Customer(name='Other Client')
            db.add_all([customer_a, customer_b])
            db.commit()

            invoice_a = Invoice(invoice_number='INV-8746', customer_id=customer_a.id, status=InvoiceStatus.SENT, date=date(2026, 4, 2), subtotal=Decimal('53.91'), tax_rate=Decimal('0'), tax_amount=Decimal('0'), total=Decimal('53.91'), amount_paid=Decimal('0'), balance_due=Decimal('53.91'))
            invoice_b = Invoice(invoice_number='INV-9999', customer_id=customer_b.id, status=InvoiceStatus.SENT, date=date(2026, 4, 2), subtotal=Decimal('53.91'), tax_rate=Decimal('0'), tax_amount=Decimal('0'), total=Decimal('53.91'), amount_paid=Decimal('0'), balance_due=Decimal('53.91'))
            db.add_all([invoice_a, invoice_b])
            db.commit()

            statement_line = BankTransaction(bank_account_id=bank_account.id, date=date(2026, 4, 16), amount=Decimal('53.91'), payee='Learn Innovatio', description='Learning Inn', reference='Inv 8746', code=None, reconciled=False, match_status='unmatched')
            db.add(statement_line)
            db.commit()

            suggestions = suggestion_candidates(db, statement_line)

        self.assertEqual(suggestions[0]['target_id'], invoice_a.id)
        self.assertEqual(suggestions[0]['kind'], 'invoice')
        self.assertIn('reference/number match', suggestions[0]['reasons'])

    def test_invoice_and_bill_matching_and_direct_coding_workflows(self):
        from app.models.accounts import Account, AccountType
        from app.models.banking import BankAccount, BankTransaction
        from app.models.bills import Bill, BillStatus
        from app.models.contacts import Customer, Vendor
        from app.models.invoices import Invoice, InvoiceStatus
        from app.models.payments import Payment
        from app.models.bills import BillPayment
        from app.models.transactions import Transaction
        from app.routes.banking import (
            approve_bank_transaction_match,
            code_bank_transaction,
            search_bank_transaction_matches,
        )
        from app.schemas.banking import BankTransactionCodeApproval, BankTransactionMatchApproval

        with self.Session() as db:
            bank_gl = Account(name='Business Bank Account', account_number='090', account_type=AccountType.ASSET, is_active=True)
            ar = Account(name='Accounts Receivable', account_number='610', account_type=AccountType.ASSET, is_active=True)
            ap = Account(name='Accounts Payable', account_number='800', account_type=AccountType.LIABILITY, is_active=True)
            wages = Account(name='Wages Expense', account_number='477', account_type=AccountType.EXPENSE, is_active=True)
            db.add_all([bank_gl, ar, ap, wages])
            db.commit()
            self._set_role(db, 'system_account_accounts_receivable_id', ar.id)
            self._set_role(db, 'system_account_accounts_payable_id', ap.id)

            bank_gl_id = bank_gl.id
            wages_id = wages.id
            bank_account = BankAccount(name='ANZ', account_id=bank_gl_id, bank_name='ANZ', last_four='1208', balance=Decimal('0'), is_active=True)
            db.add(bank_account)
            db.commit()

            customer = Customer(name='Learn Innovations Limited')
            vendor = Vendor(name='PowerDirect', default_expense_account_id=wages.id)
            db.add_all([customer, vendor])
            db.commit()

            invoice = Invoice(invoice_number='INV-8746', customer_id=customer.id, status=InvoiceStatus.SENT, date=date(2026, 4, 2), subtotal=Decimal('53.91'), tax_rate=Decimal('0'), tax_amount=Decimal('0'), total=Decimal('53.91'), amount_paid=Decimal('0'), balance_due=Decimal('53.91'))
            bill = Bill(bill_number='B-3001', vendor_id=vendor.id, status=BillStatus.UNPAID, date=date(2026, 4, 3), due_date=date(2026, 5, 3), terms='Net 30', subtotal=Decimal('186.30'), tax_rate=Decimal('0'), tax_amount=Decimal('0'), total=Decimal('186.30'), amount_paid=Decimal('0'), balance_due=Decimal('186.30'))
            db.add_all([invoice, bill])
            db.commit()

            inflow = BankTransaction(bank_account_id=bank_account.id, date=date(2026, 4, 16), amount=Decimal('53.91'), payee='Learn Innovatio', description='Learning Inn', reference='Inv 8746', code=None, reconciled=False, match_status='unmatched')
            outflow = BankTransaction(bank_account_id=bank_account.id, date=date(2026, 4, 17), amount=Decimal('-186.30'), payee='PowerDirect', description='Electricity account', reference='B-3001', code='Power', reconciled=False, match_status='unmatched')
            uncoded = BankTransaction(bank_account_id=bank_account.id, date=date(2026, 4, 18), amount=Decimal('-73.57'), payee='Caleb Macklow', description='Wages', reference=None, code='Wages', reconciled=False, match_status='unmatched')
            db.add_all([inflow, outflow, uncoded])
            db.commit()

            invoice_search = search_bank_transaction_matches(inflow.id, query='8746', db=db, auth=None)
            bill_search = search_bank_transaction_matches(outflow.id, query='3001', db=db, auth=None)
            self.assertTrue(all(candidate['kind'] == 'invoice' for candidate in invoice_search['candidates']))
            self.assertTrue(all(candidate['kind'] == 'bill' for candidate in bill_search['candidates']))

            approve_bank_transaction_match(inflow.id, BankTransactionMatchApproval(match_kind='invoice', target_id=invoice.id), db=db, auth=None)
            approve_bank_transaction_match(outflow.id, BankTransactionMatchApproval(match_kind='bill', target_id=bill.id), db=db, auth=None)
            code_bank_transaction(uncoded.id, BankTransactionCodeApproval(account_id=wages.id, description='Weekly wages'), db=db, auth=None)

            payment = db.query(Payment).one()
            bill_payment = db.query(BillPayment).one()
            inflow_txn = db.query(BankTransaction).filter(BankTransaction.id == inflow.id).one()
            outflow_txn = db.query(BankTransaction).filter(BankTransaction.id == outflow.id).one()
            coded_txn = db.query(BankTransaction).filter(BankTransaction.id == uncoded.id).one()
            invoice_row = db.query(Invoice).filter(Invoice.id == invoice.id).one()
            bill_row = db.query(Bill).filter(Bill.id == bill.id).one()
            journal = db.query(Transaction).filter(Transaction.id == coded_txn.transaction_id).one()
            journal_account_ids = {line.account_id for line in journal.lines}

        self.assertEqual(payment.reference, 'Inv 8746')
        self.assertEqual(bill_payment.check_number, 'B-3001')
        self.assertEqual(Decimal(str(invoice_row.balance_due)), Decimal('0.00'))
        self.assertEqual(Decimal(str(bill_row.balance_due)), Decimal('0.00'))
        self.assertTrue(inflow_txn.reconciled)
        self.assertTrue(outflow_txn.reconciled)
        self.assertEqual(coded_txn.match_status, 'coded')
        self.assertTrue(coded_txn.reconciled)
        self.assertEqual(coded_txn.category_account_id, wages_id)
        self.assertEqual(journal_account_ids, {bank_gl_id, wages_id})

    def test_invoice_overpayment_creates_credit_note_for_excess(self):
        from app.models.accounts import Account, AccountType
        from app.models.banking import BankAccount, BankTransaction
        from app.models.contacts import Customer
        from app.models.credit_memos import CreditMemo, CreditMemoStatus
        from app.models.invoices import Invoice, InvoiceStatus
        from app.models.payments import Payment
        from app.routes.banking import approve_bank_transaction_match
        from app.schemas.banking import BankTransactionMatchApproval

        with self.Session() as db:
            bank_gl = Account(name='Business Bank Account', account_number='090', account_type=AccountType.ASSET, is_active=True)
            ar = Account(name='Accounts Receivable', account_number='610', account_type=AccountType.ASSET, is_active=True)
            db.add_all([bank_gl, ar])
            db.commit()
            self._set_role(db, 'system_account_accounts_receivable_id', ar.id)

            bank_account = BankAccount(name='ANZ', account_id=bank_gl.id, bank_name='ANZ', last_four='1208', balance=Decimal('0'), is_active=True)
            db.add(bank_account)
            db.commit()

            customer = Customer(name='Aroha Ltd')
            db.add(customer)
            db.commit()
            customer_id = customer.id

            invoice = Invoice(
                invoice_number='INV-5001',
                customer_id=customer_id,
                status=InvoiceStatus.SENT,
                date=date(2026, 4, 2),
                subtotal=Decimal('100.00'),
                tax_rate=Decimal('0'),
                tax_amount=Decimal('0'),
                total=Decimal('100.00'),
                amount_paid=Decimal('0'),
                balance_due=Decimal('100.00'),
            )
            db.add(invoice)
            db.commit()
            invoice_id = invoice.id

            inflow = BankTransaction(
                bank_account_id=bank_account.id,
                date=date(2026, 4, 16),
                amount=Decimal('150.00'),
                payee='Aroha Ltd',
                description='Invoice overpayment',
                reference='INV-5001',
                code='Aroha',
                reconciled=False,
                match_status='unmatched',
            )
            db.add(inflow)
            db.commit()

            result = approve_bank_transaction_match(
                inflow.id,
                BankTransactionMatchApproval(match_kind='invoice', target_id=invoice_id),
                db=db,
                auth=None,
            )

            payment = db.query(Payment).one()
            allocation_amounts = [Decimal(str(allocation.amount)) for allocation in payment.allocations]
            credit_memo = db.query(CreditMemo).one()
            invoice_row = db.query(Invoice).filter(Invoice.id == invoice.id).one()
            inflow_txn = db.query(BankTransaction).filter(BankTransaction.id == inflow.id).one()

        self.assertEqual(payment.amount, Decimal('150.00'))
        self.assertEqual(len(allocation_amounts), 1)
        self.assertEqual(allocation_amounts[0], Decimal('100.00'))
        self.assertEqual(Decimal(str(invoice_row.balance_due)), Decimal('0.00'))
        self.assertEqual(credit_memo.customer_id, customer_id)
        self.assertEqual(credit_memo.original_invoice_id, invoice_id)
        self.assertEqual(credit_memo.status, CreditMemoStatus.ISSUED)
        self.assertEqual(Decimal(str(credit_memo.total)), Decimal('50.00'))
        self.assertEqual(Decimal(str(credit_memo.balance_remaining)), Decimal('50.00'))
        self.assertIsNone(credit_memo.transaction_id)
        self.assertTrue(inflow_txn.reconciled)
        self.assertIn('Credit Note', result['matched_label'])


if __name__ == '__main__':
    unittest.main()
