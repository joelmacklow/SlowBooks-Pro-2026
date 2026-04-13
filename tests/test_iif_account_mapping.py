import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.database import Base
from app.models.accounts import Account, AccountType


class IifAccountMappingTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_nz_chart_bank_ar_ap_accounts_map_to_expected_iif_types(self):
        from app.services.iif_export import _map_account_type

        bank = Account(name="Business Bank Account", account_number="090", account_type=AccountType.ASSET)
        ar = Account(name="Accounts Receivable", account_number="610", account_type=AccountType.ASSET)
        ap = Account(name="Accounts Payable", account_number="800", account_type=AccountType.LIABILITY)

        self.assertEqual(_map_account_type(bank), "BANK")
        self.assertEqual(_map_account_type(ar), "AR")
        self.assertEqual(_map_account_type(ap), "AP")


if __name__ == "__main__":
    unittest.main()
