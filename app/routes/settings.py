# ============================================================================
# Decompiled from qbw32.exe!CPreferencesDialog  Offset: 0x0023F800
# Original: tabbed dialog (IDD_PREFERENCES) with 12 tabs. We condensed
# everything into a single key-value store because nobody needs 12 tabs.
# ============================================================================

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.requests import Request

import app.config as app_config
from app.database import get_db
from app.models.settings import Settings, DEFAULT_SETTINGS
from app.services.auth import require_permissions
from app.services.chart_setup_status import (
    CHART_SETUP_SOURCE_TEMPLATE_PREFIX,
    mark_chart_setup_ready,
)
from app.services.chart_template_loader import load_chart_template as run_chart_template_load
from app.services.closing_date import hash_closing_date_password
from app.services.rate_limit import enforce_rate_limit
from scripts.seed_nz_demo_data import seed as run_demo_seed

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _get_all(db: Session) -> dict:
    rows = db.query(Settings).all()
    result = dict(DEFAULT_SETTINGS)
    for row in rows:
        result[row.key] = row.value
    return result


def _set(db: Session, key: str, value: str):
    row = db.query(Settings).filter(Settings.key == key).first()
    if row:
        row.value = value
    else:
        row = Settings(key=key, value=value)
        db.add(row)


def _settings_for_client(settings: dict) -> dict:
    result = dict(settings)
    result["closing_date_password"] = ""
    result["smtp_password"] = ""
    return result


def _apply_smtp_secret_status(db: Session, settings: dict) -> dict:
    result = dict(settings)
    legacy_row = db.query(Settings).filter(Settings.key == "smtp_password").first()
    env_ready = bool((app_config.SMTP_PASSWORD or "").strip())

    if legacy_row and env_ready:
        db.delete(legacy_row)
        db.flush()
        result["smtp_password_status"] = "env_managed_legacy_removed"
        result["smtp_password_notice"] = "Legacy stored SMTP password was removed because SMTP_PASSWORD is configured."
    elif legacy_row:
        result["smtp_password_status"] = "legacy_db_password_present"
        result["smtp_password_notice"] = "Legacy stored SMTP password remains in the database until SMTP_PASSWORD is configured."
    elif env_ready:
        result["smtp_password_status"] = "env_managed"
        result["smtp_password_notice"] = "SMTP password is managed via the SMTP_PASSWORD environment variable."
    else:
        result["smtp_password_status"] = "not_configured"
        result["smtp_password_notice"] = "Configure SMTP_PASSWORD in the environment before using authenticated SMTP."

    return result


@router.get("/public")
def get_public_settings(db: Session = Depends(get_db)):
    result = _get_all(db)
    allowed_keys = (
        "company_name",
        "default_tax_rate",
        "country",
        "currency",
        "locale",
        "timezone",
        "tax_regime",
        "gst_basis",
        "gst_period",
        "prices_include_gst",
    )
    return {key: result.get(key, DEFAULT_SETTINGS.get(key, "")) for key in allowed_keys}


@router.get("")
def get_settings(
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("settings.manage")),
):
    settings = _apply_smtp_secret_status(db, _get_all(db))
    db.commit()
    return _settings_for_client(settings)


@router.put("")
def update_settings(
    data: dict,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("settings.manage")),
):
    for key, value in data.items():
        if key in DEFAULT_SETTINGS:
            if key == "closing_date_password":
                secret = str(value) if value is not None else ""
                if secret:
                    _set(db, key, hash_closing_date_password(secret))
                else:
                    existing = db.query(Settings).filter(Settings.key == key).first()
                    if existing is None:
                        _set(db, key, "")
                continue
            if key == "smtp_password":
                continue
            _set(db, key, str(value) if value is not None else "")
    settings = _apply_smtp_secret_status(db, _get_all(db))
    db.commit()
    return _settings_for_client(settings)


@router.post("/test-email")
def test_email(
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("settings.manage")),
    request: Request = None,
):
    """Feature 8: Send a test email to verify SMTP settings."""
    enforce_rate_limit(
        request,
        scope="email:test",
        limit=5,
        window_seconds=60,
        detail="Too many SMTP test email requests. Please wait and try again.",
    )
    settings = _get_all(db)
    if not settings.get("smtp_host"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="SMTP not configured")
    try:
        from app.services.email_service import send_email_or_raise
        send_email_or_raise(
            db,
            to_email=settings.get("smtp_from_email") or settings.get("smtp_user", ""),
            subject="Slowbooks Pro 2026 — Test Email",
            html_body="<p>This is a test email from Slowbooks Pro 2026. SMTP is configured correctly.</p>",
            entity_type="settings_test",
            entity_id=0,
        )
        return {"status": "sent"}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Email failed: {str(e)}")



@router.post("/load-chart-template/{template_key}")
def load_chart_template(
    template_key: str,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("settings.manage")),
):
    from fastapi import HTTPException
    try:
        result = run_chart_template_load(db, template_key)
        mark_chart_setup_ready(db, f"{CHART_SETUP_SOURCE_TEMPLATE_PREFIX}{template_key}")
        db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.post("/load-demo-data")
def load_demo_data(
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("settings.manage")),
):
    run_demo_seed()
    return {"status": "loaded"}
