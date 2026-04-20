from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.settings import Settings


def _setting_value(db: Session, key: str, default: str) -> str:
    row = db.query(Settings).filter(Settings.key == key).first()
    if not row or row.value is None:
        return default
    return str(row.value)


def _set_setting_value(db: Session, key: str, value: str) -> None:
    row = db.query(Settings).filter(Settings.key == key).first()
    if row:
        row.value = value
    else:
        db.add(Settings(key=key, value=value))


def allocate_document_number(
    db: Session,
    *,
    model,
    field_name: str,
    prefix_key: str,
    next_key: str,
    default_prefix: str,
    default_next_number: str,
) -> str:
    prefix = _setting_value(db, prefix_key, default_prefix)
    raw_next_number = (_setting_value(db, next_key, default_next_number) or default_next_number).strip() or default_next_number
    if not raw_next_number.isdigit():
        raw_next_number = default_next_number
    width = len(raw_next_number)
    current_number = int(raw_next_number)
    field = getattr(model, field_name)

    while True:
        candidate = f"{prefix}{str(current_number).zfill(width)}"
        exists = db.query(model.id).filter(field == candidate).first()
        if not exists:
            _set_setting_value(db, next_key, str(current_number + 1).zfill(width))
            return candidate
        current_number += 1
