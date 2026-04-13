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
from sqlalchemy import func

from app.models.transactions import Transaction, TransactionLine
from app.models.accounts import Account, AccountType
from app.models.settings import Settings


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


def _account_id_from_setting(db: Session, key: str, account_type: AccountType | None = None) -> int | None:
    row = db.query(Settings).filter(Settings.key == key).first()
    if not row or not row.value:
        return None
    try:
        account_id = int(str(row.value).strip())
    except (TypeError, ValueError):
        return None
    account = db.query(Account).filter(Account.id == account_id, Account.is_active == True).first()
    if not account:
        return None
    if account_type and account.account_type != account_type:
        return None
    return account.id


def _first_matching_account(
    db: Session,
    account_type: AccountType | None = None,
    account_numbers: tuple[str, ...] = (),
    account_names: tuple[str, ...] = (),
    prefer_first_by_type: bool = False,
) -> int | None:
    if account_numbers:
        account = (
            db.query(Account)
            .filter(Account.account_number.in_(account_numbers), Account.is_active == True)
            .order_by(Account.account_number)
            .first()
        )
        if account and (not account_type or account.account_type == account_type):
            return account.id

    for name in account_names:
        account = (
            db.query(Account)
            .filter(func.lower(Account.name) == name.lower(), Account.is_active == True)
            .first()
        )
        if account and (not account_type or account.account_type == account_type):
            return account.id

    if prefer_first_by_type and account_type:
        account = (
            db.query(Account)
            .filter(Account.account_type == account_type, Account.is_active == True)
            .order_by(Account.account_number, Account.name)
            .first()
        )
        if account:
            return account.id

    return None


def _resolve_system_account_id(
    db: Session,
    setting_key: str,
    account_type: AccountType | None = None,
    fallback_numbers: tuple[str, ...] = (),
    fallback_names: tuple[str, ...] = (),
    prefer_first_by_type: bool = False,
    create_spec: tuple[str, str, AccountType] | None = None,
) -> int | None:
    explicit = _account_id_from_setting(db, setting_key, account_type=account_type)
    if explicit:
        return explicit

    fallback = _first_matching_account(
        db,
        account_type=account_type,
        account_numbers=fallback_numbers,
        account_names=fallback_names,
        prefer_first_by_type=prefer_first_by_type,
    )
    if fallback:
        return fallback

    if create_spec:
        account_number, name, create_type = create_spec
        return get_or_create_system_account(db, account_number, name, create_type)
    return None


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
    """Get Accounts Receivable account ID."""
    return _resolve_system_account_id(
        db,
        "system_account_accounts_receivable_id",
        account_type=AccountType.ASSET,
        fallback_numbers=("1100",),
        fallback_names=("Accounts Receivable", "Trade Debtors"),
    )


def get_default_income_account_id(db: Session) -> int:
    """Get default sales income account ID."""
    return _resolve_system_account_id(
        db,
        "system_account_default_sales_income_id",
        account_type=AccountType.INCOME,
        fallback_numbers=("4000",),
        fallback_names=("Service Income", "Sales"),
        prefer_first_by_type=True,
    )


def get_gst_account_id(db: Session) -> int:
    """Get or create the NZ GST control account."""
    explicit = _account_id_from_setting(db, "system_account_gst_control_id", account_type=AccountType.LIABILITY)
    if explicit:
        return explicit

    account = (
        db.query(Account)
        .filter(
            Account.is_active == True,
            (
                (Account.account_number == "2200")
                | (func.lower(Account.name) == "gst")
                | (func.lower(Account.name) == "sales tax payable")
            ),
        )
        .order_by(Account.account_number)
        .first()
    )
    if account:
        if account.name == "Sales Tax Payable":
            account.name = "GST"
        account.account_type = AccountType.LIABILITY
        account.is_system = True
        db.flush()
        return account.id

    return get_or_create_system_account(db, "2200", "GST", AccountType.LIABILITY)


def get_sales_tax_account_id(db: Session) -> int:
    """Compatibility alias for the NZ GST account."""
    return get_gst_account_id(db)


def get_undeposited_funds_id(db: Session) -> int:
    """Get undeposited funds / receipt clearing account ID."""
    return _resolve_system_account_id(
        db,
        "system_account_undeposited_funds_id",
        account_type=AccountType.ASSET,
        fallback_numbers=("1200",),
        fallback_names=("Undeposited Funds", "Receipt Clearing"),
        prefer_first_by_type=True,
    )


def get_ap_account_id(db: Session) -> int:
    """Get accounts payable account ID."""
    return _resolve_system_account_id(
        db,
        "system_account_accounts_payable_id",
        account_type=AccountType.LIABILITY,
        fallback_numbers=("2000",),
        fallback_names=("Accounts Payable", "Trade Creditors"),
    )


def get_default_expense_account_id(db: Session) -> int | None:
    return _resolve_system_account_id(
        db,
        "system_account_default_expense_id",
        account_type=AccountType.EXPENSE,
        fallback_numbers=("6000",),
        fallback_names=("Expenses", "Advertising & Marketing", "Purchases"),
        prefer_first_by_type=True,
    )


def get_default_bank_account_id(db: Session) -> int | None:
    return _resolve_system_account_id(
        db,
        "system_account_default_bank_id",
        account_type=AccountType.ASSET,
        fallback_numbers=("1000", "1010"),
        fallback_names=("Checking", "Business Bank Account", "Operating Account"),
        prefer_first_by_type=True,
    )


def get_wages_expense_account_id(db: Session) -> int | None:
    return _resolve_system_account_id(
        db,
        "system_account_wages_expense_id",
        account_type=AccountType.EXPENSE,
        fallback_numbers=("7000",),
        fallback_names=("Wages & Salaries Expense", "Salaries"),
        create_spec=("7000", "Wages & Salaries Expense", AccountType.EXPENSE),
    )


def get_employer_kiwisaver_expense_account_id(db: Session) -> int | None:
    return _resolve_system_account_id(
        db,
        "system_account_employer_kiwisaver_expense_id",
        account_type=AccountType.EXPENSE,
        fallback_numbers=("7010",),
        fallback_names=("Employer KiwiSaver Expense", "KiwiSaver Employer Contributions"),
        create_spec=("7010", "Employer KiwiSaver Expense", AccountType.EXPENSE),
    )


def get_paye_payable_account_id(db: Session) -> int | None:
    return _resolve_system_account_id(
        db,
        "system_account_paye_payable_id",
        account_type=AccountType.LIABILITY,
        fallback_numbers=("2310",),
        fallback_names=("PAYE Payable", "PAYE Liability"),
        create_spec=("2310", "PAYE Payable", AccountType.LIABILITY),
    )


def get_kiwisaver_payable_account_id(db: Session) -> int | None:
    return _resolve_system_account_id(
        db,
        "system_account_kiwisaver_payable_id",
        account_type=AccountType.LIABILITY,
        fallback_numbers=("2315",),
        fallback_names=("KiwiSaver Payable", "KiwiSaver Liability"),
        create_spec=("2315", "KiwiSaver Payable", AccountType.LIABILITY),
    )


def get_esct_payable_account_id(db: Session) -> int | None:
    return _resolve_system_account_id(
        db,
        "system_account_esct_payable_id",
        account_type=AccountType.LIABILITY,
        fallback_numbers=("2320",),
        fallback_names=("ESCT Payable", "ESCT Liability"),
        create_spec=("2320", "ESCT Payable", AccountType.LIABILITY),
    )


def get_child_support_payable_account_id(db: Session) -> int | None:
    return _resolve_system_account_id(
        db,
        "system_account_child_support_payable_id",
        account_type=AccountType.LIABILITY,
        fallback_numbers=("2325",),
        fallback_names=("Child Support Payable", "Child Support Liability"),
        create_spec=("2325", "Child Support Payable", AccountType.LIABILITY),
    )


def get_payroll_clearing_account_id(db: Session) -> int | None:
    return _resolve_system_account_id(
        db,
        "system_account_payroll_clearing_id",
        account_type=AccountType.LIABILITY,
        fallback_numbers=("2330",),
        fallback_names=("Payroll Clearing", "Net Wages Clearing"),
        create_spec=("2330", "Payroll Clearing", AccountType.LIABILITY),
    )
