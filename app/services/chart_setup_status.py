from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.accounts import Account, AccountType
from app.models.settings import Settings


CHART_SETUP_SOURCE_TEMPLATE_PREFIX = "template:"
CHART_SETUP_SOURCE_XERO_IMPORT = "xero_import"


def _get_setting(db: Session, key: str) -> str:
    row = db.query(Settings).filter(Settings.key == key).first()
    return row.value if row and row.value else ""


def _set_setting(db: Session, key: str, value: str) -> None:
    row = db.query(Settings).filter(Settings.key == key).first()
    if row:
        row.value = value
    else:
        db.add(Settings(key=key, value=value))


def mark_chart_setup_ready(db: Session, source: str) -> None:
    timestamp = datetime.now(UTC).isoformat()
    _set_setting(db, "chart_setup_source", source)
    _set_setting(db, "chart_setup_ready_at", timestamp)


def chart_setup_status(db: Session) -> dict:
    source = _get_setting(db, "chart_setup_source")
    ready_at = _get_setting(db, "chart_setup_ready_at")
    has_balance_sheet_accounts = (
        db.query(Account)
        .filter(
            Account.is_active == True,
            Account.account_type.in_([
                AccountType.ASSET,
                AccountType.LIABILITY,
                AccountType.EQUITY,
            ]),
        )
        .first()
        is not None
    )
    is_ready = bool(source or has_balance_sheet_accounts)
    effective_source = source or ("legacy_existing_accounts" if has_balance_sheet_accounts else "")
    return {
        "is_ready": is_ready,
        "source": effective_source or None,
        "ready_at": ready_at or None,
    }
