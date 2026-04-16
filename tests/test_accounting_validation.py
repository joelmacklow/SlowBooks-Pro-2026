import os
import unittest
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from app.database import Base
from app.models.accounts import Account, AccountType


class AccountingValidationTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_create_journal_entry_rejects_negative_amounts(self):
        from app.services.accounting import create_journal_entry

        with self.Session() as db:
            bank = Account(name='Operating', account_number='090', account_type=AccountType.ASSET)
            equity = Account(name='Equity', account_number='950', account_type=AccountType.EQUITY)
            db.add_all([bank, equity])
            db.commit()

            with self.assertRaises(ValueError) as ctx:
                create_journal_entry(
                    db,
                    date(2026, 4, 30),
                    'Bad journal',
                    [
                        {'account_id': bank.id, 'debit': Decimal('-1.00'), 'credit': Decimal('0')},
                        {'account_id': equity.id, 'debit': Decimal('0'), 'credit': Decimal('1.00')},
                    ],
                )

        self.assertIn('non-negative', str(ctx.exception))

    def test_create_journal_entry_rejects_line_with_both_debit_and_credit(self):
        from app.services.accounting import create_journal_entry

        with self.Session() as db:
            bank = Account(name='Operating', account_number='090', account_type=AccountType.ASSET)
            equity = Account(name='Equity', account_number='950', account_type=AccountType.EQUITY)
            db.add_all([bank, equity])
            db.commit()

            with self.assertRaises(ValueError) as ctx:
                create_journal_entry(
                    db,
                    date(2026, 4, 30),
                    'Bad journal',
                    [
                        {'account_id': bank.id, 'debit': Decimal('1.00'), 'credit': Decimal('1.00')},
                        {'account_id': equity.id, 'debit': Decimal('0'), 'credit': Decimal('2.00')},
                    ],
                )

        self.assertIn('both debit and credit', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
