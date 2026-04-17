from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.accounts import Account, AccountType
from app.schemas.opening_balances import (
    OpeningBalanceCreate,
    OpeningBalanceCreateResponse,
    OpeningBalanceStatusResponse,
)
from app.services.accounting import create_journal_entry
from app.services.auth import require_permissions
from app.services.chart_setup_status import chart_setup_status
from app.services.closing_date import check_closing_date
from app.routes.journal import _journal_response

router = APIRouter(prefix="/api/opening-balances", tags=["opening_balances"])


def _normal_line_for_amount(account: Account, amount: Decimal) -> dict:
    if amount == 0:
        return {}

    if account.account_type in {AccountType.ASSET, AccountType.EXPENSE, AccountType.COGS}:
        return {
            "account_id": account.id,
            "debit": amount if amount > 0 else Decimal("0"),
            "credit": -amount if amount < 0 else Decimal("0"),
            "description": "Opening balance",
        }

    return {
        "account_id": account.id,
        "debit": -amount if amount < 0 else Decimal("0"),
        "credit": amount if amount > 0 else Decimal("0"),
        "description": "Opening balance",
    }


@router.get("/status", response_model=OpeningBalanceStatusResponse)
def get_opening_balance_status(
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    return chart_setup_status(db)


@router.post("", response_model=OpeningBalanceCreateResponse, status_code=201)
def create_opening_balances(
    data: OpeningBalanceCreate,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    status = chart_setup_status(db)
    if not status["is_ready"]:
        raise HTTPException(status_code=400, detail="Chart of accounts must be loaded before opening balances can be entered")

    check_closing_date(db, data.date)

    lines = []
    for row in data.lines:
        amount = Decimal(str(row.amount or 0))
        if amount == 0:
            continue
        account = db.query(Account).filter(Account.id == row.account_id, Account.is_active == True).first()
        if not account:
            raise HTTPException(status_code=404, detail=f"Account {row.account_id} not found")
        if account.account_type not in {AccountType.ASSET, AccountType.LIABILITY, AccountType.EQUITY}:
            raise HTTPException(status_code=400, detail="Opening balances only support asset, liability, and equity accounts")
        lines.append(_normal_line_for_amount(account, amount))

    if not lines:
        raise HTTPException(status_code=400, detail="Enter at least one non-zero opening balance")

    total_debit = sum(Decimal(str(line["debit"])) for line in lines)
    total_credit = sum(Decimal(str(line["credit"])) for line in lines)
    difference = total_debit - total_credit

    if difference != 0:
        if not data.auto_balance_account_id:
            raise HTTPException(
                status_code=400,
                detail=f"Opening balances are not balanced: debits={total_debit}, credits={total_credit}",
            )
        balancing_account = (
            db.query(Account)
            .filter(
                Account.id == data.auto_balance_account_id,
                Account.is_active == True,
            )
            .first()
        )
        if not balancing_account:
            raise HTTPException(status_code=404, detail="Auto-balance account not found")
        if balancing_account.account_type != AccountType.EQUITY:
            raise HTTPException(status_code=400, detail="Auto-balance account must be an active equity account")
        lines.append({
            "account_id": balancing_account.id,
            "debit": Decimal("0") if difference > 0 else -difference,
            "credit": difference if difference > 0 else Decimal("0"),
            "description": "Opening balance auto-balance",
        })

    description = data.description or "Opening balances"
    reference = data.reference or "OPENING-BAL"
    try:
        txn = create_journal_entry(
            db,
            data.date,
            description,
            lines,
            source_type="manual_journal",
            reference=reference,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    db.commit()
    db.refresh(txn)
    return OpeningBalanceCreateResponse(journal=_journal_response(db, txn))
