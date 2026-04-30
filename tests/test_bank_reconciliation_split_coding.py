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


class BankReconciliationSplitCodingTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def _seed_banking(self, db):
        from app.models.accounts import Account, AccountType
        from app.models.banking import BankAccount

        bank_gl = Account(name="Business Bank Account", account_number="090", account_type=AccountType.ASSET, is_active=True)
        expense_a = Account(name="Office Expense", account_number="600", account_type=AccountType.EXPENSE, is_active=True)
        expense_b = Account(name="Travel Expense", account_number="610", account_type=AccountType.EXPENSE, is_active=True)
        db.add_all([bank_gl, expense_a, expense_b])
        db.commit()

        bank_account = BankAccount(name="ANZ", account_id=bank_gl.id, bank_name="ANZ", last_four="1208", balance=Decimal("0"), is_active=True)
        db.add(bank_account)
        db.commit()
        return bank_account, bank_gl, expense_a, expense_b

    def test_import_does_not_change_bank_balance_until_reconciliation_completes(self):
        from app.routes.banking import complete_reconciliation, create_reconciliation, toggle_cleared
        from app.schemas.banking import ReconciliationCreate
        from app.services.ofx_import import import_transactions

        with self.Session() as db:
            bank_account, _bank_gl, _expense_a, _expense_b = self._seed_banking(db)
            result = import_transactions(db, bank_account.id, [{
                "import_id": "split-balance-1",
                "date": date(2026, 4, 20),
                "amount": Decimal("-100.00"),
                "payee": "Stationery World",
                "description": "Supplies",
                "reference": "INV-1",
                "code": "SUPPLIES",
            }], import_source="csv")
            db.refresh(bank_account)
            self.assertEqual(Decimal(str(bank_account.balance)), Decimal("0.00"))

            recon = create_reconciliation(
                ReconciliationCreate(
                    bank_account_id=bank_account.id,
                    statement_date=date(2026, 4, 20),
                    statement_balance=Decimal("-100.00"),
                    import_batch_id=result["import_batch_id"],
                ),
                db=db,
                auth=True,
            )
            db.refresh(bank_account)
            self.assertEqual(Decimal(str(bank_account.balance)), Decimal("0.00"))

            txn = bank_account.transactions[0]
            toggle_cleared(recon.id, txn.id, db=db, auth=True)
            complete_reconciliation(recon.id, db=db, auth=True)
            db.refresh(bank_account)

        self.assertEqual(Decimal(str(bank_account.balance)), Decimal("-100.00"))

    def test_failed_reconciliation_leaves_balance_unchanged(self):
        from app.routes.banking import complete_reconciliation, create_reconciliation
        from app.schemas.banking import ReconciliationCreate
        from app.services.ofx_import import import_transactions

        with self.Session() as db:
            bank_account, _bank_gl, _expense_a, _expense_b = self._seed_banking(db)
            result = import_transactions(db, bank_account.id, [{
                "import_id": "split-balance-2",
                "date": date(2026, 4, 20),
                "amount": Decimal("-100.00"),
                "payee": "Stationery World",
                "description": "Supplies",
                "reference": "INV-2",
                "code": "SUPPLIES",
            }], import_source="csv")
            recon = create_reconciliation(
                ReconciliationCreate(
                    bank_account_id=bank_account.id,
                    statement_date=date(2026, 4, 20),
                    statement_balance=Decimal("-100.00"),
                    import_batch_id=result["import_batch_id"],
                ),
                db=db,
                auth=True,
            )

            with self.assertRaises(HTTPException):
                complete_reconciliation(recon.id, db=db, auth=True)
            db.refresh(bank_account)

        self.assertEqual(Decimal(str(bank_account.balance)), Decimal("0.00"))

    def test_cancelling_import_backed_reconciliation_removes_staged_transactions(self):
        from app.models.banking import BankTransaction, Reconciliation
        from app.routes.banking import cancel_reconciliation, create_reconciliation
        from app.schemas.banking import ReconciliationCreate
        from app.services.ofx_import import import_transactions

        with self.Session() as db:
            bank_account, _bank_gl, _expense_a, _expense_b = self._seed_banking(db)
            result = import_transactions(db, bank_account.id, [{
                "import_id": "split-balance-3",
                "date": date(2026, 4, 20),
                "amount": Decimal("-100.00"),
                "payee": "Stationery World",
                "description": "Supplies",
                "reference": "INV-3",
                "code": "SUPPLIES",
            }], import_source="csv")
            recon = create_reconciliation(
                ReconciliationCreate(
                    bank_account_id=bank_account.id,
                    statement_date=date(2026, 4, 20),
                    statement_balance=Decimal("-100.00"),
                    import_batch_id=result["import_batch_id"],
                ),
                db=db,
                auth=True,
            )
            self.assertEqual(db.query(BankTransaction).count(), 1)

            cancelled = cancel_reconciliation(recon.id, db=db, auth=True)

        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(cancelled["removed_transactions"], 1)
        with self.Session() as db:
            self.assertEqual(db.query(BankTransaction).count(), 0)
            self.assertEqual(db.query(Reconciliation).count(), 0)

    def test_duplicate_reimport_reuses_untouched_import_batch(self):
        from app.routes.banking import create_reconciliation
        from app.schemas.banking import ReconciliationCreate
        from app.services.ofx_import import import_transactions

        transactions = [{
            "import_id": "split-balance-4",
            "date": date(2026, 4, 20),
            "amount": Decimal("-100.00"),
            "payee": "Stationery World",
            "description": "Supplies",
            "reference": "INV-4",
            "code": "SUPPLIES",
        }]

        with self.Session() as db:
            bank_account, _bank_gl, _expense_a, _expense_b = self._seed_banking(db)
            first = import_transactions(db, bank_account.id, transactions, import_source="csv")
            create_reconciliation(
                ReconciliationCreate(
                    bank_account_id=bank_account.id,
                    statement_date=date(2026, 4, 20),
                    statement_balance=Decimal("-100.00"),
                    import_batch_id=first["import_batch_id"],
                ),
                db=db,
                auth=True,
            )

            second = import_transactions(db, bank_account.id, transactions, import_source="csv")

        self.assertEqual(second["imported"], 0)
        self.assertEqual(second["skipped"], 1)
        self.assertEqual(second["import_batch_id"], first["import_batch_id"])

    def test_split_coding_posts_balanced_journal_and_marks_transaction(self):
        from app.models.banking import BankTransaction
        from app.models.transactions import Transaction
        from app.routes.banking import split_code_bank_transaction
        from app.schemas.banking import BankTransactionSplitCodeApproval, BankTransactionSplitLine

        with self.Session() as db:
            bank_account, bank_gl, expense_a, expense_b = self._seed_banking(db)
            bank_txn = BankTransaction(
                bank_account_id=bank_account.id,
                date=date(2026, 4, 20),
                amount=Decimal("-100.00"),
                payee="Mixed expense vendor",
                description="Split expense",
                reference="SPLIT-1",
                code="MIXED",
                reconciled=False,
                match_status="unmatched",
            )
            db.add(bank_txn)
            db.commit()

            result = split_code_bank_transaction(
                bank_txn.id,
                BankTransactionSplitCodeApproval(
                    splits=[
                        BankTransactionSplitLine(account_id=expense_a.id, amount=Decimal("60.00"), description="Office"),
                        BankTransactionSplitLine(account_id=expense_b.id, amount=Decimal("40.00"), description="Travel"),
                    ]
                ),
                db=db,
                auth=True,
            )

            stored_txn = db.query(BankTransaction).filter(BankTransaction.id == bank_txn.id).one()
            journal = db.query(Transaction).filter(Transaction.id == stored_txn.transaction_id).one()
            debit_total = sum((Decimal(str(line.debit)) for line in journal.lines), Decimal("0.00"))
            credit_total = sum((Decimal(str(line.credit)) for line in journal.lines), Decimal("0.00"))
            non_bank_lines = [line for line in journal.lines if line.account_id != bank_gl.id]

        self.assertEqual(result["status"], "coded")
        self.assertEqual(stored_txn.match_status, "coded")
        self.assertTrue(stored_txn.reconciled)
        self.assertEqual(stored_txn.category_account_id, None)
        self.assertEqual(debit_total, Decimal("100.00"))
        self.assertEqual(credit_total, Decimal("100.00"))
        self.assertEqual(len(non_bank_lines), 2)

    def test_purchase_gst_split_coding_extracts_input_gst_from_gross_statement_amount(self):
        from app.models.banking import BankTransaction
        from app.models.transactions import Transaction
        from app.routes.banking import split_code_bank_transaction
        from app.schemas.banking import BankTransactionSplitCodeApproval, BankTransactionSplitLine

        with self.Session() as db:
            bank_account, bank_gl, expense_a, expense_b = self._seed_banking(db)
            bank_txn = BankTransaction(
                bank_account_id=bank_account.id,
                date=date(2026, 4, 20),
                amount=Decimal("-115.00"),
                payee="Harbour Supplies",
                description="Supplier payment",
                reference="B-900",
                code="SUPPLIER",
                reconciled=False,
                match_status="unmatched",
            )
            db.add(bank_txn)
            db.commit()

            result = split_code_bank_transaction(
                bank_txn.id,
                BankTransactionSplitCodeApproval(
                    use_purchase_gst=True,
                    splits=[
                        BankTransactionSplitLine(account_id=expense_a.id, amount=Decimal("57.50"), description="Stationery", gst_code="GST15"),
                        BankTransactionSplitLine(account_id=expense_b.id, amount=Decimal("57.50"), description="Travel", gst_code="NO_GST"),
                    ]
                ),
                db=db,
                auth=True,
            )

            stored_txn = db.query(BankTransaction).filter(BankTransaction.id == bank_txn.id).one()
            journal = db.query(Transaction).filter(Transaction.id == stored_txn.transaction_id).one()
            debit_total = sum((Decimal(str(line.debit)) for line in journal.lines), Decimal("0.00"))
            credit_total = sum((Decimal(str(line.credit)) for line in journal.lines), Decimal("0.00"))
            non_bank_lines = [line for line in journal.lines if line.account_id != bank_gl.id]
            gst_lines = [line for line in non_bank_lines if line.description == "GST on reconciled purchase split"]
            expense_lines = [line for line in non_bank_lines if line.description != "GST on reconciled purchase split"]

        self.assertEqual(result["status"], "coded")
        self.assertEqual(stored_txn.match_status, "coded")
        self.assertTrue(stored_txn.reconciled)
        self.assertEqual(debit_total, Decimal("115.00"))
        self.assertEqual(credit_total, Decimal("115.00"))
        self.assertEqual(len(gst_lines), 1)
        self.assertEqual(Decimal(str(gst_lines[0].debit)), Decimal("7.50"))
        self.assertEqual(sorted(Decimal(str(line.debit)) for line in expense_lines), [Decimal("50.00"), Decimal("57.50")])

    def test_split_coding_rejects_unbalanced_lines(self):
        from app.models.banking import BankTransaction
        from app.routes.banking import split_code_bank_transaction
        from app.schemas.banking import BankTransactionSplitCodeApproval, BankTransactionSplitLine

        with self.Session() as db:
            bank_account, _bank_gl, expense_a, expense_b = self._seed_banking(db)
            bank_txn = BankTransaction(
                bank_account_id=bank_account.id,
                date=date(2026, 4, 20),
                amount=Decimal("-100.00"),
                payee="Mixed expense vendor",
                description="Split expense",
                reference="SPLIT-2",
                code="MIXED",
                reconciled=False,
                match_status="unmatched",
            )
            db.add(bank_txn)
            db.commit()

            with self.assertRaises(HTTPException):
                split_code_bank_transaction(
                    bank_txn.id,
                    BankTransactionSplitCodeApproval(
                        splits=[
                            BankTransactionSplitLine(account_id=expense_a.id, amount=Decimal("60.00"), description="Office"),
                            BankTransactionSplitLine(account_id=expense_b.id, amount=Decimal("30.00"), description="Travel"),
                        ]
                    ),
                    db=db,
                    auth=True,
                )


if __name__ == "__main__":
    unittest.main()
