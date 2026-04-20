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


class BankRulesTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def _set_role(self, db, key, account_id):
        from app.models.settings import Settings
        db.add(Settings(key=key, value=str(account_id)))
        db.commit()

    def _seed_banking_core(self, db):
        from app.models.accounts import Account, AccountType
        from app.models.banking import BankAccount

        bank_gl = Account(name="Business Bank Account", account_number="090", account_type=AccountType.ASSET, is_active=True)
        wages = Account(name="Wages Expense", account_number="477", account_type=AccountType.EXPENSE, is_active=True)
        utilities = Account(name="Utilities Expense", account_number="478", account_type=AccountType.EXPENSE, is_active=True)
        ar = Account(name="Accounts Receivable", account_number="610", account_type=AccountType.ASSET, is_active=True)
        db.add_all([bank_gl, wages, utilities, ar])
        db.commit()
        self._set_role(db, "system_account_accounts_receivable_id", ar.id)

        bank_account = BankAccount(name="ANZ", account_id=bank_gl.id, bank_name="ANZ", last_four="1208", balance=Decimal("0"), is_active=True)
        db.add(bank_account)
        db.commit()
        return bank_account, bank_gl, wages, utilities

    def test_find_matching_rule_is_priority_ordered_and_direction_scoped(self):
        from app.models.banking import BankRule, BankRuleDirection, BankTransaction
        from app.services.bank_rules import find_matching_bank_rule

        with self.Session() as db:
            bank_account, _bank_gl, wages, utilities = self._seed_banking_core(db)
            lower_priority = BankRule(
                name="Generic power",
                priority=20,
                direction=BankRuleDirection.OUTFLOW,
                payee_contains="power",
                target_account_id=utilities.id,
            )
            higher_priority = BankRule(
                name="Specific code",
                priority=10,
                direction=BankRuleDirection.OUTFLOW,
                payee_contains="power",
                code_equals="power",
                target_account_id=wages.id,
            )
            inflow_only = BankRule(
                name="Inflow only",
                priority=1,
                direction=BankRuleDirection.INFLOW,
                payee_contains="power",
                target_account_id=utilities.id,
            )
            db.add_all([lower_priority, higher_priority, inflow_only])
            db.commit()

            txn = BankTransaction(
                bank_account_id=bank_account.id,
                date=date(2026, 4, 21),
                amount=Decimal("-73.57"),
                payee="PowerDirect",
                description="Monthly electricity",
                reference="APR",
                code="Power",
                reconciled=False,
                match_status="unmatched",
            )
            db.add(txn)
            db.commit()

            rule, reasons = find_matching_bank_rule(db, txn)

        self.assertEqual(rule.name, "Specific code")
        self.assertIn("payee contains", reasons[0])
        self.assertTrue(any("code equals" in reason for reason in reasons))

    def test_import_transactions_stamps_suggested_rule_metadata(self):
        from app.models.banking import BankRule, BankRuleDirection, BankTransaction
        from app.services.ofx_import import import_transactions

        with self.Session() as db:
            bank_account, _bank_gl, wages, _utilities = self._seed_banking_core(db)
            rule = BankRule(
                name="Weekly wages",
                priority=5,
                direction=BankRuleDirection.OUTFLOW,
                payee_contains="caleb",
                code_equals="wages",
                target_account_id=wages.id,
                default_description="Weekly wages",
            )
            db.add(rule)
            db.commit()
            rule_id = rule.id
            wages_id = wages.id

            result = import_transactions(db, bank_account.id, [{
                "date": date(2026, 4, 21),
                "amount": Decimal("-73.57"),
                "payee": "Caleb Macklow",
                "description": "Wages",
                "reference": None,
                "code": "Wages",
                "import_id": "bank-rule-test-1",
            }], import_source="csv")
            txn = db.query(BankTransaction).one()

        self.assertEqual(result["imported"], 1)
        self.assertEqual(txn.suggested_rule_id, rule_id)
        self.assertEqual(txn.suggested_account_id, wages_id)
        self.assertIn("code equals", txn.rule_match_reason)

    def test_apply_rule_reuses_existing_coding_flow(self):
        from app.models.banking import BankRule, BankRuleDirection, BankTransaction
        from app.models.transactions import Transaction
        from app.routes.banking import apply_bank_transaction_rule
        from app.schemas.banking import BankTransactionRuleApproval

        with self.Session() as db:
            bank_account, bank_gl, wages, _utilities = self._seed_banking_core(db)
            rule = BankRule(
                name="Weekly wages",
                priority=5,
                direction=BankRuleDirection.OUTFLOW,
                payee_contains="caleb",
                target_account_id=wages.id,
                default_description="Weekly wages",
            )
            db.add(rule)
            db.commit()
            rule_id = rule.id
            wages_id = wages.id
            bank_gl_id = bank_gl.id

            txn = BankTransaction(
                bank_account_id=bank_account.id,
                date=date(2026, 4, 21),
                amount=Decimal("-73.57"),
                payee="Caleb Macklow",
                description="Wages",
                reference=None,
                code="Wages",
                reconciled=False,
                match_status="unmatched",
            )
            db.add(txn)
            db.commit()

            result = apply_bank_transaction_rule(txn.id, BankTransactionRuleApproval(rule_id=rule.id), db=db, auth=True)
            stored_txn = db.query(BankTransaction).filter(BankTransaction.id == txn.id).one()
            journal = db.query(Transaction).filter(Transaction.id == stored_txn.transaction_id).one()
            journal_accounts = {line.account_id for line in journal.lines}

        self.assertEqual(result["status"], "coded")
        self.assertEqual(result["rule_id"], rule_id)
        self.assertEqual(stored_txn.match_status, "coded")
        self.assertTrue(stored_txn.reconciled)
        self.assertEqual(stored_txn.category_account_id, wages_id)
        self.assertEqual(stored_txn.suggested_rule_id, rule_id)
        self.assertEqual(journal_accounts, {bank_gl_id, wages_id})

    def test_suggestions_endpoint_keeps_document_matches_and_rule_suggestion(self):
        from app.models.banking import BankRule, BankRuleDirection, BankTransaction
        from app.models.contacts import Customer
        from app.models.invoices import Invoice, InvoiceStatus
        from app.routes.banking import get_bank_transaction_suggestions

        with self.Session() as db:
            bank_account, _bank_gl, wages, _utilities = self._seed_banking_core(db)
            customer = Customer(name="Learn Innovations Limited")
            db.add(customer)
            db.commit()
            invoice = Invoice(
                invoice_number="INV-8746",
                customer_id=customer.id,
                status=InvoiceStatus.SENT,
                date=date(2026, 4, 2),
                subtotal=Decimal("53.91"),
                tax_rate=Decimal("0"),
                tax_amount=Decimal("0"),
                total=Decimal("53.91"),
                amount_paid=Decimal("0"),
                balance_due=Decimal("53.91"),
            )
            db.add(invoice)
            rule = BankRule(
                name="Learning income catch-all",
                priority=20,
                direction=BankRuleDirection.INFLOW,
                payee_contains="learn",
                target_account_id=wages.id,
            )
            db.add(rule)
            db.commit()

            txn = BankTransaction(
                bank_account_id=bank_account.id,
                date=date(2026, 4, 16),
                amount=Decimal("53.91"),
                payee="Learn Innovatio",
                description="Learning Inn",
                reference="Inv 8746",
                code=None,
                reconciled=False,
                match_status="unmatched",
            )
            db.add(txn)
            db.commit()

            result = get_bank_transaction_suggestions(txn.id, db=db, auth=None)

        self.assertEqual(result["suggestions"][0]["kind"], "invoice")
        self.assertIsNotNone(result["rule_suggestion"])
        self.assertEqual(result["rule_suggestion"]["name"], "Learning income catch-all")


if __name__ == "__main__":
    unittest.main()
