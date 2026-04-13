# ============================================================================
# Decompiled from qbw32.exe!CQBJournalEngine::PostTransaction()
# Offset: 0x00128400
# This is the heart of the double-entry system. Every financial event
# (invoice, payment, bank transaction) creates a balanced journal entry
# through this service. The original validated sum(debits) == sum(credits)
# with a tolerance of 0.004 (BCD rounding). We use exact Decimal math.
# ============================================================================

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.transactions import Transaction, TransactionLine
from app.models.accounts import Account, AccountType


def get_or_create_system_account(
    db: Session,
    account_number: str,
    name: str,
    account_type: AccountType,
) -> int | None:
    acct = db.query(Account).filter(Account.account_number == account_number).first()
    if acct:
        acct.name = name
        acct.account_type = account_type
        acct.is_system = True
        acct.is_active = True
        db.flush()
        return acct.id

    acct = Account(
        name=name,
        account_number=account_number,
        account_type=account_type,
        is_system=True,
        is_active=True,
    )
    db.add(acct)
    db.flush()
    return acct.id if acct else None


def create_journal_entry(
    db: Session,
    txn_date: date,
    description: str,
    lines: list[dict],
    source_type: str = None,
    source_id: int = None,
    reference: str = None,
) -> Transaction:
    """Create a balanced journal entry.

    lines: [{"account_id": int, "debit": Decimal, "credit": Decimal}, ...]
    Each line must have debit > 0 OR credit > 0, not both.
    Total debits must equal total credits.
    """
    total_debit = sum(Decimal(str(l.get("debit", 0))) for l in lines)
    total_credit = sum(Decimal(str(l.get("credit", 0))) for l in lines)

    if total_debit != total_credit:
        raise ValueError(f"Journal entry not balanced: debits={total_debit}, credits={total_credit}")

    txn = Transaction(
        date=txn_date,
        description=description,
        source_type=source_type,
        source_id=source_id,
        reference=reference,
    )
    db.add(txn)
    db.flush()

    for line_data in lines:
        debit = Decimal(str(line_data.get("debit", 0)))
        credit = Decimal(str(line_data.get("credit", 0)))
        if debit == 0 and credit == 0:
            continue

        txn_line = TransactionLine(
            transaction_id=txn.id,
            account_id=line_data["account_id"],
            debit=debit,
            credit=credit,
            description=line_data.get("description", ""),
        )
        db.add(txn_line)

        # Update account balance
        account = db.query(Account).filter(Account.id == line_data["account_id"]).first()
        if account:
            if account.account_type.value in ("asset", "expense", "cogs"):
                account.balance += debit - credit
            else:
                account.balance += credit - debit

    return txn


def reverse_journal_entry(
    db: Session,
    transaction_id: int,
    reversal_date: date,
    description: str,
    source_type: str = None,
    source_id: int = None,
    reference: str = None,
) -> Transaction | None:
    """Create a reversing entry for an existing journal transaction."""
    original = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not original:
        return None

    reverse_lines = [
        {
            "account_id": line.account_id,
            "debit": line.credit,
            "credit": line.debit,
            "description": f"REVERSAL: {line.description or ''}",
        }
        for line in original.lines
    ]
    if not reverse_lines:
        return None

    return create_journal_entry(
        db,
        reversal_date,
        description,
        reverse_lines,
        source_type=source_type,
        source_id=source_id,
        reference=reference,
    )


def get_ar_account_id(db: Session) -> int:
    """Get Accounts Receivable account ID (1100)."""
    acct = db.query(Account).filter(Account.account_number == "1100").first()
    return acct.id if acct else None


def get_default_income_account_id(db: Session) -> int:
    """Get default Service Income account ID (4000)."""
    acct = db.query(Account).filter(Account.account_number == "4000").first()
    return acct.id if acct else None


def get_gst_account_id(db: Session) -> int:
    """Get or create the NZ GST control account (2200)."""
    return get_or_create_system_account(db, "2200", "GST", AccountType.LIABILITY)


def get_sales_tax_account_id(db: Session) -> int:
    """Compatibility alias for the NZ GST account."""
    return get_gst_account_id(db)


def get_undeposited_funds_id(db: Session) -> int:
    """Get Undeposited Funds account ID (1200)."""
    acct = db.query(Account).filter(Account.account_number == "1200").first()
    return acct.id if acct else None


def get_ap_account_id(db: Session) -> int:
    """Get Accounts Payable account ID (2000)."""
    acct = db.query(Account).filter(Account.account_number == "2000").first()
    return acct.id if acct else None


def get_wages_expense_account_id(db: Session) -> int | None:
    return get_or_create_system_account(db, "7000", "Wages & Salaries Expense", AccountType.EXPENSE)


def get_employer_kiwisaver_expense_account_id(db: Session) -> int | None:
    return get_or_create_system_account(db, "7010", "Employer KiwiSaver Expense", AccountType.EXPENSE)


def get_paye_payable_account_id(db: Session) -> int | None:
    return get_or_create_system_account(db, "2310", "PAYE Payable", AccountType.LIABILITY)


def get_kiwisaver_payable_account_id(db: Session) -> int | None:
    return get_or_create_system_account(db, "2315", "KiwiSaver Payable", AccountType.LIABILITY)


def get_esct_payable_account_id(db: Session) -> int | None:
    return get_or_create_system_account(db, "2320", "ESCT Payable", AccountType.LIABILITY)


def get_child_support_payable_account_id(db: Session) -> int | None:
    return get_or_create_system_account(db, "2325", "Child Support Payable", AccountType.LIABILITY)


def get_payroll_clearing_account_id(db: Session) -> int | None:
    return get_or_create_system_account(db, "2330", "Payroll Clearing", AccountType.LIABILITY)
