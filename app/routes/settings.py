# ============================================================================
# Decompiled from qbw32.exe!CPreferencesDialog  Offset: 0x0023F800
# Original: tabbed dialog (IDD_PREFERENCES) with 12 tabs. We condensed
# everything into a single key-value store because nobody needs 12 tabs.
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.requests import Request

import app.config as app_config
from app.database import get_db
from app.models.invoice_reminders import InvoiceReminderAudit, InvoiceReminderRule
from app.models.settings import Settings, DEFAULT_SETTINGS
from app.schemas.invoice_reminders import (
    InvoiceReminderRuleCreate,
    InvoiceReminderRuleResponse,
    InvoiceReminderRuleUpdate,
)
from app.services.auth import require_permissions
from app.services.chart_setup_status import (
    CHART_SETUP_SOURCE_TEMPLATE_PREFIX,
    mark_chart_setup_ready,
)
from app.services.chart_template_loader import load_chart_template as run_chart_template_load
from app.services.closing_date import (
    hash_closing_date_password,
    lock_context_for_client,
    normalize_financial_year_boundary,
    validate_financial_year_dates,
)
from app.services.invoice_reminders import (
    default_invoice_reminder_body_template,
    default_invoice_reminder_subject_template,
    ensure_default_invoice_reminder_rules,
    invoice_reminder_rule_label,
)
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


def _validate_period_settings(data: dict) -> None:
    start_value = data.get("financial_year_start")
    end_value = data.get("financial_year_end")
    if start_value is None and end_value is None:
        return
    validate_financial_year_dates(start_value, end_value)


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


def _validate_invoice_reminder_rule_uniqueness(
    db: Session,
    *,
    timing_direction: str,
    day_offset: int,
    exclude_rule_id: int | None = None,
):
    query = (
        db.query(InvoiceReminderRule)
        .filter(InvoiceReminderRule.timing_direction == timing_direction)
        .filter(InvoiceReminderRule.day_offset == day_offset)
    )
    if exclude_rule_id is not None:
        query = query.filter(InvoiceReminderRule.id != exclude_rule_id)
    if query.first():
        raise HTTPException(
            status_code=400,
            detail="A reminder rule already exists for that timing direction and day offset",
        )


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
    settings.update(lock_context_for_client(db))
    db.commit()
    return _settings_for_client(settings)


@router.put("")
def update_settings(
    data: dict,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("settings.manage")),
):
    _validate_period_settings(data)
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
            if key in ("financial_year_start", "financial_year_end"):
                _set(db, key, normalize_financial_year_boundary(str(value) if value is not None else ""))
                continue
            _set(db, key, str(value) if value is not None else "")
    settings = _apply_smtp_secret_status(db, _get_all(db))
    settings.update(lock_context_for_client(db))
    db.commit()
    return _settings_for_client(settings)


@router.get("/invoice-reminder-rules", response_model=list[InvoiceReminderRuleResponse])
def list_invoice_reminder_rules(
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("settings.manage")),
):
    rows = ensure_default_invoice_reminder_rules(db)
    return [InvoiceReminderRuleResponse.model_validate(row) for row in rows]


@router.post("/invoice-reminder-rules", response_model=InvoiceReminderRuleResponse, status_code=201)
def create_invoice_reminder_rule(
    data: InvoiceReminderRuleCreate,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("settings.manage")),
):
    ensure_default_invoice_reminder_rules(db)
    _validate_invoice_reminder_rule_uniqueness(
        db,
        timing_direction=data.timing_direction,
        day_offset=data.day_offset,
    )
    current_max = db.query(InvoiceReminderRule).order_by(InvoiceReminderRule.sort_order.desc(), InvoiceReminderRule.id.desc()).first()
    next_sort_order = (current_max.sort_order if current_max else -1) + 1
    rule = InvoiceReminderRule(
        name=data.name or invoice_reminder_rule_label(data.timing_direction, data.day_offset),
        timing_direction=data.timing_direction,
        day_offset=data.day_offset,
        is_enabled=data.is_enabled,
        sort_order=data.sort_order if data.sort_order is not None else next_sort_order,
        subject_template=data.subject_template or default_invoice_reminder_subject_template(data.timing_direction, data.day_offset),
        body_template=data.body_template or default_invoice_reminder_body_template(data.timing_direction, data.day_offset),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return InvoiceReminderRuleResponse.model_validate(rule)


@router.put("/invoice-reminder-rules/{rule_id}", response_model=InvoiceReminderRuleResponse)
def update_invoice_reminder_rule(
    rule_id: int,
    data: InvoiceReminderRuleUpdate,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("settings.manage")),
):
    ensure_default_invoice_reminder_rules(db)
    rule = db.query(InvoiceReminderRule).filter(InvoiceReminderRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Invoice reminder rule not found")

    new_direction = data.timing_direction or rule.timing_direction
    new_day_offset = data.day_offset if data.day_offset is not None else rule.day_offset
    _validate_invoice_reminder_rule_uniqueness(
        db,
        timing_direction=new_direction,
        day_offset=new_day_offset,
        exclude_rule_id=rule.id,
    )

    rule.timing_direction = new_direction
    rule.day_offset = new_day_offset
    if data.is_enabled is not None:
        rule.is_enabled = data.is_enabled
    if data.sort_order is not None:
        rule.sort_order = data.sort_order
    rule.name = data.name or invoice_reminder_rule_label(rule.timing_direction, rule.day_offset)
    rule.subject_template = data.subject_template or default_invoice_reminder_subject_template(rule.timing_direction, rule.day_offset)
    rule.body_template = data.body_template or default_invoice_reminder_body_template(rule.timing_direction, rule.day_offset)

    db.commit()
    db.refresh(rule)
    return InvoiceReminderRuleResponse.model_validate(rule)


@router.delete("/invoice-reminder-rules/{rule_id}")
def delete_invoice_reminder_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("settings.manage")),
):
    ensure_default_invoice_reminder_rules(db)
    rule = db.query(InvoiceReminderRule).filter(InvoiceReminderRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Invoice reminder rule not found")
    if db.query(InvoiceReminderAudit).filter(InvoiceReminderAudit.rule_id == rule_id).first():
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a reminder rule with history; disable it instead",
        )
    db.delete(rule)
    db.commit()
    return {"status": "deleted"}


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
        raise HTTPException(status_code=500, detail=f"Email failed: {str(e)}")


@router.post("/load-chart-template/{template_key}")
def load_chart_template(
    template_key: str,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("settings.manage")),
):
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
