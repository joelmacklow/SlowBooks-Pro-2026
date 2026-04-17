# ============================================================================
# Closing Date Enforcement — prevent modifications before closing date
# Feature 10: Configurable closing date with optional password override
# ============================================================================

import hmac
from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.settings import Settings
from app.services.auth import hash_password, verify_password


def get_closing_date(db: Session) -> date | None:
    """Get the configured closing date, or None if not set."""
    row = db.query(Settings).filter(Settings.key == "closing_date").first()
    if row and row.value:
        try:
            return date.fromisoformat(row.value)
        except ValueError:
            return None
    return None


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


def check_closing_date(db: Session, txn_date: date, password: str = None):
    """Raise HTTPException if txn_date is on or before the closing date.
    If a closing_date_password is set and the caller provides it, allow override."""
    closing = get_closing_date(db)
    if closing is None:
        return  # No closing date configured

    if txn_date <= closing:
        # Check if password override is available
        pw_row = db.query(Settings).filter(Settings.key == "closing_date_password").first()
        if pw_row and pw_row.value and verify_closing_date_password(password, pw_row.value):
            if not pw_row.value.startswith("pbkdf2_sha256$"):
                pw_row.value = hash_closing_date_password(password)
                db.flush()
            return  # Password override accepted
        raise HTTPException(
            status_code=403,
            detail=f"Transaction date {txn_date} is on or before the closing date ({closing}). "
                   f"Modifications to closed periods are not allowed."
        )
