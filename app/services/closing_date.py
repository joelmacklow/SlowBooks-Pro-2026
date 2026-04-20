# ============================================================================
# Closing Date Enforcement — layered company/org date locks with optional override
# ============================================================================

import hmac
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.companies import Company
from app.models.settings import Settings
from app.services.auth import hash_password, verify_password

_request_closing_date_password: ContextVar[str | None] = ContextVar("request_closing_date_password", default=None)


@dataclass(frozen=True)
class LockContext:
    company_lock_date: date | None
    org_lock_date: date | None
    effective_lock_date: date | None
    effective_lock_layer: str | None


def _open_master_session():
    return SessionLocal()


def _database_name_for_session(db: Session) -> str:
    bind = db.get_bind()
    database = getattr(bind.url, "database", None) or urlparse(str(bind.url)).path.lstrip("/")
    if not database:
        return "bookkeeper"
    database = str(database).rsplit("/", 1)[-1]
    if database.endswith(".db"):
        database = database.rsplit(".", 1)[0]
    return database or "bookkeeper"


def _read_date_setting(db: Session, key: str) -> date | None:
    row = db.query(Settings).filter(Settings.key == key).first()
    if row and row.value:
        try:
            return date.fromisoformat(row.value)
        except ValueError:
            return None
    return None


def get_closing_date(db: Session) -> date | None:
    return _read_date_setting(db, "closing_date")


def get_org_lock_date(db: Session) -> date | None:
    database_name = _database_name_for_session(db)
    master_db = _open_master_session()
    try:
        company = master_db.query(Company).filter(Company.database_name == database_name, Company.is_active == True).first()
        return company.org_lock_date if company else None
    finally:
        master_db.close()


def resolve_lock_context(db: Session) -> LockContext:
    company_lock_date = get_closing_date(db)
    org_lock_date = get_org_lock_date(db)
    effective_lock_date = None
    effective_lock_layer = None

    if org_lock_date and (company_lock_date is None or org_lock_date >= company_lock_date):
        effective_lock_date = org_lock_date
        effective_lock_layer = "org_admin"
    elif company_lock_date:
        effective_lock_date = company_lock_date
        effective_lock_layer = "company_admin"

    return LockContext(
        company_lock_date=company_lock_date,
        org_lock_date=org_lock_date,
        effective_lock_date=effective_lock_date,
        effective_lock_layer=effective_lock_layer,
    )


def lock_context_for_client(db: Session) -> dict:
    context = resolve_lock_context(db)
    return {
        "org_lock_date": context.org_lock_date.isoformat() if context.org_lock_date else "",
        "effective_lock_date": context.effective_lock_date.isoformat() if context.effective_lock_date else "",
        "effective_lock_layer": context.effective_lock_layer or "",
    }


def hash_closing_date_password(password: str | None) -> str:
    secret = (password or "").strip()
    if not secret:
        return ""
    return hash_password(secret)


def verify_closing_date_password(password: str | None, stored_value: str | None) -> bool:
    candidate = password or ""
    stored = stored_value or ""
    if not candidate or not stored:
        return False
    if stored.startswith("pbkdf2_sha256$"):
        return verify_password(candidate, stored)
    return hmac.compare_digest(candidate, stored)


def set_request_closing_date_password(password: str | None):
    return _request_closing_date_password.set(password or None)


def reset_request_closing_date_password(token) -> None:
    _request_closing_date_password.reset(token)


def get_request_closing_date_password() -> str | None:
    return _request_closing_date_password.get()


def normalize_financial_year_boundary(value: str | None) -> str:
    if value is None:
        return ""
    candidate = str(value).strip()
    if not candidate:
        return ""
    try:
        if len(candidate) == 5 and candidate[2] == "-":
            month = int(candidate[:2])
            day = int(candidate[3:])
        else:
            parsed = date.fromisoformat(candidate)
            month = parsed.month
            day = parsed.day
        date(2001, month, day)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Financial year dates must use a valid day and month") from exc
    return f"{month:02d}-{day:02d}"


def validate_financial_year_dates(start_value: str | None, end_value: str | None) -> None:
    if not start_value and not end_value:
        return
    if not start_value or not end_value:
        raise HTTPException(status_code=400, detail="Financial year start and end dates must both be set")
    start_boundary = normalize_financial_year_boundary(start_value)
    end_boundary = normalize_financial_year_boundary(end_value)
    start_date = date(2001, int(start_boundary[:2]), int(start_boundary[3:]))
    end_date = date(2001, int(end_boundary[:2]), int(end_boundary[3:]))
    if end_date <= start_date:
        end_date = date(2002, int(end_boundary[:2]), int(end_boundary[3:]))
    if (end_date - start_date).days > 370:
        raise HTTPException(status_code=400, detail="Financial year range is too long")


def check_closing_date(db: Session, txn_date: date, password: str = None):
    """Raise HTTPException if txn_date is on or before the effective layered lock date."""
    password = password if password is not None else get_request_closing_date_password()
    context = resolve_lock_context(db)
    if context.effective_lock_date is None:
        return

    if txn_date <= context.effective_lock_date:
        company_password_can_override = (
            context.company_lock_date is not None
            and txn_date <= context.company_lock_date
            and (context.org_lock_date is None or txn_date > context.org_lock_date)
        )
        if company_password_can_override:
            pw_row = db.query(Settings).filter(Settings.key == "closing_date_password").first()
            if pw_row and pw_row.value and verify_closing_date_password(password, pw_row.value):
                if not pw_row.value.startswith("pbkdf2_sha256$"):
                    pw_row.value = hash_closing_date_password(password)
                    db.flush()
                return
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Transaction date {txn_date} is on or before the company admin lock date "
                    f"({context.company_lock_date}). Modifications to closed periods are not allowed without the company override password."
                ),
            )
        if context.org_lock_date and txn_date <= context.org_lock_date:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Transaction date {txn_date} is on or before the organization lock date "
                    f"({context.org_lock_date}). Company override passwords cannot bypass organization locks."
                ),
            )
        raise HTTPException(
            status_code=403,
            detail=(
                f"Transaction date {txn_date} is on or before the effective lock date "
                f"({context.effective_lock_date}). Modifications to closed periods are not allowed."
            ),
        )
