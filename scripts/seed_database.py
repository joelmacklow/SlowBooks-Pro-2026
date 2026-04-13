"""Seed the database with Chart of Accounts."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models.accounts import Account, AccountType
from app.models.settings import Settings
from app.seed.chart_of_accounts import CHART_OF_ACCOUNTS


SYSTEM_ACCOUNT_NUMBER_BY_SETTING = {
    "system_account_default_bank_id": "090",
    "system_account_accounts_receivable_id": "610",
    "system_account_undeposited_funds_id": "615",
    "system_account_default_sales_income_id": "200",
    "system_account_default_expense_id": "429",
    "system_account_accounts_payable_id": "800",
    "system_account_payroll_clearing_id": "814",
    "system_account_gst_control_id": "820",
    "system_account_paye_payable_id": "825",
    "system_account_kiwisaver_payable_id": "826",
    "system_account_esct_payable_id": "827",
    "system_account_child_support_payable_id": "828",
    "system_account_wages_expense_id": "477",
    "system_account_employer_kiwisaver_expense_id": "478",
}


def _set(db, key: str, value: str):
    row = db.query(Settings).filter(Settings.key == key).first()
    if row:
        row.value = value
    else:
        db.add(Settings(key=key, value=value))


def _populate_system_account_settings(db):
    for key, number in SYSTEM_ACCOUNT_NUMBER_BY_SETTING.items():
        account = db.query(Account).filter(Account.account_number == number).first()
        if account:
            _set(db, key, str(account.id))


def seed_accounts(db):
    for entry in CHART_OF_ACCOUNTS:
        account = Account(
            name=entry["name"],
            account_number=entry["account_number"],
            account_type=AccountType(entry["account_type"]),
            is_system=True,
        )
        db.add(account)


def seed():
    db = SessionLocal()
    try:
        existing = db.query(Account).count()
        if existing == 0:
            seed_accounts(db)
            db.commit()
            print(f"Seeded {len(CHART_OF_ACCOUNTS)} accounts.")
        else:
            print(f"Database already has {existing} accounts. Skipping account creation.")

        _populate_system_account_settings(db)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
