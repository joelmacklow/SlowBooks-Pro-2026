from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session, joinedload

from app.models.accounts import Account, AccountType
from app.models.banking import BankAccount, BankTransaction, Reconciliation, ReconciliationStatus
from app.models.invoices import Invoice, InvoiceStatus
from app.models.settings import Settings
from app.models.transactions import Transaction, TransactionLine
from app.services.accounting import get_default_bank_account_id


def _decimal(value) -> Decimal:
    return Decimal(str(value or 0))


def _month_start(day: date) -> date:
    return date(day.year, day.month, 1)


def _shift_month(day: date, delta_months: int) -> date:
    month_index = (day.year * 12 + (day.month - 1)) + delta_months
    year = month_index // 12
    month = (month_index % 12) + 1
    return date(year, month, 1)


def _period_label(start_date: date, end_date: date) -> str:
    return f"{start_date.day} {start_date.strftime('%b')} - {end_date.day} {end_date.strftime('%b %Y')}"


def _financial_year_start(db: Session, today: date) -> date:
    start_value = (
        db.query(Settings.value)
        .filter(Settings.key == "financial_year_start")
        .scalar()
    ) or ""
    start_value = str(start_value or "").strip()
    if not start_value:
        return date(today.year, 1, 1)

    month = int(start_value[:2])
    day = int(start_value[3:])
    candidate = date(today.year, month, day)
    if today < candidate:
        candidate = date(today.year - 1, month, day)
    return candidate


def natural_balance_amount(account_type: AccountType, debit_total, credit_total) -> Decimal:
    debit = _decimal(debit_total)
    credit = _decimal(credit_total)
    if account_type in (AccountType.ASSET, AccountType.EXPENSE, AccountType.COGS):
        return debit - credit
    return credit - debit


def cash_flow_category_for_account(account: Account | None) -> str:
    if not account:
        return "operating"

    name = (account.name or "").lower()
    number = (account.account_number or "").lower()
    operating_asset_markers = (
        "receivable", "debtor", "inventory", "stock", "prepayment", "undeposited", "gst", "tax"
    )
    financing_liability_markers = ("loan", "mortgage", "lease", "note payable", "note")

    if account.account_type in (AccountType.INCOME, AccountType.EXPENSE, AccountType.COGS):
        return "operating"
    if account.account_type == AccountType.EQUITY:
        return "financing"
    if account.account_type == AccountType.LIABILITY:
        if any(marker in name for marker in financing_liability_markers):
            return "financing"
        return "operating"
    if any(marker in name for marker in operating_asset_markers) or number.startswith("11"):
        return "operating"
    return "investing"


def cash_account_ids(db: Session) -> set[int]:
    ids = {
        int(account_id)
        for account_id, in (
            db.query(BankAccount.account_id)
            .filter(BankAccount.is_active == True, BankAccount.account_id.is_not(None))
            .all()
        )
        if account_id is not None
    }
    default_bank_id = get_default_bank_account_id(db, allow_create=False)
    if default_bank_id:
        ids.add(int(default_bank_id))
    return ids


def opening_cash_balance(db: Session, cash_account_ids_: set[int], start_date: date) -> Decimal:
    if not cash_account_ids_:
        return Decimal("0.00")
    rows = (
        db.query(TransactionLine.debit, TransactionLine.credit)
        .join(Transaction, TransactionLine.transaction_id == Transaction.id)
        .filter(TransactionLine.account_id.in_(cash_account_ids_), Transaction.date < start_date)
        .all()
    )
    return sum((_decimal(debit) - _decimal(credit) for debit, credit in rows), Decimal("0.00"))


def build_dashboard_invoice_summary(db: Session, today: date | None = None) -> dict:
    today = today or date.today()
    outstanding_invoices = (
        db.query(Invoice)
        .filter(Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PARTIAL]))
        .all()
    )

    total_receivables = sum((_decimal(invoice.balance_due) for invoice in outstanding_invoices), Decimal("0.00"))
    overdue_invoices = [
        invoice for invoice in outstanding_invoices
        if invoice.due_date and invoice.due_date < today
    ]
    overdue_value = sum((_decimal(invoice.balance_due) for invoice in overdue_invoices), Decimal("0.00"))

    return {
        "total_receivables": float(total_receivables),
        "awaiting_payment_count": len(outstanding_invoices),
        "overdue_count": len(overdue_invoices),
        "overdue_value": float(overdue_value),
        "cta_hash": "#/invoices",
    }


def build_dashboard_bank_account_summaries(db: Session) -> list[dict]:
    bank_accounts = (
        db.query(BankAccount)
        .filter(BankAccount.is_active == True)
        .order_by(BankAccount.name)
        .all()
    )
    summaries = []
    for bank_account in bank_accounts:
        unreconciled_count = db.query(sqlfunc.count(BankTransaction.id)).filter(
            BankTransaction.bank_account_id == bank_account.id,
            BankTransaction.reconciled == False,
        ).scalar() or 0

        latest_reconciliation = (
            db.query(Reconciliation)
            .filter(Reconciliation.bank_account_id == bank_account.id)
            .order_by(Reconciliation.statement_date.desc(), Reconciliation.id.desc())
            .first()
        )

        balance_difference = None
        statement_balance = None
        statement_date = None
        if latest_reconciliation:
            statement_balance = _decimal(latest_reconciliation.statement_balance)
            statement_date = latest_reconciliation.statement_date.isoformat() if latest_reconciliation.statement_date else None
            balance_difference = _decimal(bank_account.balance) - statement_balance

        if unreconciled_count:
            status_label = f"{unreconciled_count} item{'s' if unreconciled_count != 1 else ''} to reconcile"
        elif latest_reconciliation and latest_reconciliation.status == ReconciliationStatus.IN_PROGRESS:
            status_label = "Reconciliation in progress"
        elif latest_reconciliation and latest_reconciliation.statement_date:
            status_label = f"Last statement {latest_reconciliation.statement_date.strftime('%d %b')}"
        else:
            status_label = "Ready to reconcile"

        summaries.append({
            "id": bank_account.id,
            "name": bank_account.name,
            "bank_name": bank_account.bank_name,
            "last_four": bank_account.last_four,
            "balance": float(_decimal(bank_account.balance)),
            "unreconciled_count": int(unreconciled_count),
            "statement_balance": float(statement_balance) if statement_balance is not None else None,
            "balance_difference": float(balance_difference) if balance_difference is not None else None,
            "statement_date": statement_date,
            "status_label": status_label,
            "cta_hash": "#/banking",
        })
    return summaries


def _account_totals_by_period(
    db: Session,
    account_types: tuple[AccountType, ...],
    start_date: date,
    end_date: date,
) -> list[tuple[int, str | None, str, AccountType, Decimal]]:
    rows = (
        db.query(
            Account.id,
            Account.account_number,
            Account.name,
            Account.account_type,
            sqlfunc.coalesce(sqlfunc.sum(TransactionLine.debit), 0),
            sqlfunc.coalesce(sqlfunc.sum(TransactionLine.credit), 0),
        )
        .join(TransactionLine, TransactionLine.account_id == Account.id)
        .join(Transaction, TransactionLine.transaction_id == Transaction.id)
        .filter(Account.is_active == True)
        .filter(Account.account_type.in_(account_types))
        .filter(Transaction.date >= start_date)
        .filter(Transaction.date <= end_date)
        .group_by(Account.id, Account.account_number, Account.name, Account.account_type)
        .all()
    )
    return [
        (account_id, account_number, account_name, account_type, natural_balance_amount(account_type, debit_total, credit_total))
        for account_id, account_number, account_name, account_type, debit_total, credit_total in rows
    ]


def build_dashboard_account_watchlist(db: Session, today: date | None = None, limit: int = 8) -> list[dict]:
    today = today or date.today()
    start_of_year = date(today.year, 1, 1)
    start_of_month = date(today.year, today.month, 1)
    watchlist_types = (AccountType.INCOME, AccountType.COGS, AccountType.EXPENSE)

    month_totals = {
        account_id: amount
        for account_id, _account_number, _account_name, _account_type, amount
        in _account_totals_by_period(db, watchlist_types, start_of_month, today)
    }
    ytd_rows = _account_totals_by_period(db, watchlist_types, start_of_year, today)

    entries = []
    for account_id, account_number, account_name, _account_type, ytd_amount in ytd_rows:
        this_month_amount = month_totals.get(account_id, Decimal("0.00"))
        if ytd_amount == 0 and this_month_amount == 0:
            continue
        entries.append({
            "account_id": account_id,
            "account_number": account_number or "",
            "account_name": account_name,
            "this_month": float(this_month_amount),
            "ytd": float(ytd_amount),
            "cta_hash": "#/accounts",
        })

    entries.sort(key=lambda entry: ((entry["account_number"] or "ZZZ"), entry["account_name"]))
    return entries[:limit]


def _profit_totals(db: Session, start_date: date, end_date: date) -> tuple[Decimal, Decimal, Decimal]:
    rows = _account_totals_by_period(
        db,
        (AccountType.INCOME, AccountType.COGS, AccountType.EXPENSE),
        start_date,
        end_date,
    )
    total_income = sum((amount for _id, _num, _name, acct_type, amount in rows if acct_type == AccountType.INCOME), Decimal("0.00"))
    total_cogs = sum((abs(amount) for _id, _num, _name, acct_type, amount in rows if acct_type == AccountType.COGS), Decimal("0.00"))
    total_expenses = sum((abs(amount) for _id, _num, _name, acct_type, amount in rows if acct_type == AccountType.EXPENSE), Decimal("0.00"))
    expenses = total_cogs + total_expenses
    return total_income, expenses, total_income - expenses


def build_dashboard_profit_summary(db: Session, today: date | None = None) -> dict:
    today = today or date.today()
    start_of_year = _financial_year_start(db, today)
    income, expenses, net_profit = _profit_totals(db, start_of_year, today)

    elapsed_days = (today - start_of_year).days
    prior_start = date(start_of_year.year - 1, start_of_year.month, start_of_year.day)
    prior_end = prior_start + timedelta(days=elapsed_days)
    _previous_income, _previous_expenses, previous_net_profit = _profit_totals(db, prior_start, prior_end)
    profit_change = net_profit - previous_net_profit
    profit_change_pct = None
    if previous_net_profit != 0:
        profit_change_pct = float((profit_change / abs(previous_net_profit)) * Decimal("100"))

    return {
        "income": float(income),
        "expenses": float(expenses),
        "net_profit": float(net_profit),
        "previous_net_profit": float(previous_net_profit),
        "profit_change": float(profit_change),
        "profit_change_pct": profit_change_pct,
        "period_label": _period_label(start_of_year, today),
        "comparison_label": _period_label(prior_start, prior_end),
    }


def build_dashboard_cash_flow(db: Session, today: date | None = None, months: int = 6) -> dict:
    today = today or date.today()
    cash_ids = cash_account_ids(db)
    first_month = _shift_month(_month_start(today), -(months - 1))
    month_entries = []
    month_map: dict[tuple[int, int], dict] = {}
    cursor = first_month
    for _ in range(months):
        entry = {"month": cursor.strftime("%b"), "cash_in": 0.0, "cash_out": 0.0}
        month_entries.append(entry)
        month_map[(cursor.year, cursor.month)] = entry
        cursor = _shift_month(cursor, 1)

    if not cash_ids:
        return {
            "months": month_entries,
            "cash_in_total": 0.0,
            "cash_out_total": 0.0,
            "net_total": 0.0,
        }

    transactions = (
        db.query(Transaction)
        .options(joinedload(Transaction.lines).joinedload(TransactionLine.account))
        .filter(Transaction.date >= first_month, Transaction.date <= today)
        .order_by(Transaction.date, Transaction.id)
        .all()
    )

    for txn in transactions:
        key = (txn.date.year, txn.date.month)
        if key not in month_map:
            continue
        cash_lines = [line for line in txn.lines if line.account_id in cash_ids]
        counterpart_lines = [line for line in txn.lines if line.account_id not in cash_ids]
        if not cash_lines or not counterpart_lines:
            continue
        month_map[key]["cash_in"] += float(sum((_decimal(line.debit) for line in cash_lines), Decimal("0.00")))
        month_map[key]["cash_out"] += float(sum((_decimal(line.credit) for line in cash_lines), Decimal("0.00")))

    cash_in_total = round(sum(entry["cash_in"] for entry in month_entries), 2)
    cash_out_total = round(sum(entry["cash_out"] for entry in month_entries), 2)
    return {
        "months": month_entries,
        "cash_in_total": cash_in_total,
        "cash_out_total": cash_out_total,
        "net_total": round(cash_in_total - cash_out_total, 2),
    }


def build_dashboard_monthly_revenue(db: Session, today: date | None = None, months: int = 12) -> list[dict]:
    today = today or date.today()
    start_month = _shift_month(_month_start(today), -(months - 1))
    monthly_revenue = []
    cursor = start_month
    for _ in range(months):
        _, last_day = monthrange(cursor.year, cursor.month)
        start = cursor
        end = date(cursor.year, cursor.month, last_day)
        total = db.query(sqlfunc.coalesce(sqlfunc.sum(Invoice.total), 0)).filter(
            Invoice.date >= start,
            Invoice.date <= end,
            Invoice.status != InvoiceStatus.VOID,
        ).scalar()
        monthly_revenue.append({"month": start.strftime("%b"), "amount": float(_decimal(total))})
        cursor = _shift_month(cursor, 1)
    return monthly_revenue
