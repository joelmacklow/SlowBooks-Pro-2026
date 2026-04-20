import os
import unittest
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.database import Base


SAMPLE_IIF = Path(__file__).parent / "fixtures" / "sample_qbmac_opening_balances.iif"


class IifImportSampleTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def _import(self, db):
        from app.services.iif_import import import_all

        result = import_all(db, SAMPLE_IIF.read_text(encoding="utf-8"))
        db.commit()
        return result

    def test_parse_decimal_accepts_quoted_qb_mac_amounts(self):
        from app.services.iif_import import _parse_decimal

        self.assertEqual(_parse_decimal('"99,250.02"'), Decimal("99250.02"))
        self.assertEqual(_parse_decimal('"-1,725.00"'), Decimal("-1725.00"))
        self.assertEqual(_parse_decimal('""'), Decimal("0"))

    def test_sample_import_creates_expected_opening_balances_and_balanced_journal(self):
        from app.models.accounts import Account
        from app.models.transactions import Transaction, TransactionLine

        with self.Session() as db:
            result = self._import(db)
            balances = {
                acct.account_number: Decimal(str(acct.balance))
                for acct in db.query(Account).filter(Account.account_number.in_(["1000", "1010", "1100", "2000", "2200", "3000"])).all()
            }
            opening_txn = db.query(Transaction).filter(Transaction.reference == "IIF-OPENING").one()
            opening_lines = db.query(TransactionLine).filter(TransactionLine.transaction_id == opening_txn.id).all()

        self.assertEqual(result["errors"], [])
        self.assertEqual(balances["1000"], Decimal("99250.02"))
        self.assertEqual(balances["1010"], Decimal("5987.50"))
        self.assertEqual(balances["1100"], Decimal("35810.02"))
        self.assertEqual(balances["2000"], Decimal("2578.69"))
        self.assertEqual(balances["2200"], Decimal("2086.50"))
        self.assertEqual(balances["3000"], Decimal("136382.35"))
        self.assertEqual(
            sum((Decimal(str(line.debit)) for line in opening_lines), Decimal("0.00")),
            Decimal("141047.54"),
        )
        self.assertEqual(
            sum((Decimal(str(line.credit)) for line in opening_lines), Decimal("0.00")),
            Decimal("141047.54"),
        )


if __name__ == "__main__":
    unittest.main()
