import html
import json
from datetime import date, datetime, timezone

from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment
from sqlalchemy.orm import Session

from app.models.contacts import Customer
from app.models.invoice_reminders import InvoiceReminderAudit, InvoiceReminderRule
from app.models.invoices import Invoice, InvoiceStatus
from app.models.settings import DEFAULT_SETTINGS, Settings
from app.services.email_service import send_document_email_result
from app.services.formatting import format_currency, format_date
from app.services.pdf_service import generate_invoice_pdf

_scheduler_env = SandboxedEnvironment(undefined=StrictUndefined, autoescape=False)


def invoice_reminder_rule_label(timing_direction: str, day_offset: int) -> str:
    if day_offset == 0:
        return "On due date reminder"
    unit = "day" if day_offset == 1 else "days"
    if timing_direction == "before_due":
        return f"{day_offset} {unit} before due"
    return f"{day_offset} {unit} overdue"


def default_invoice_reminder_subject_template(timing_direction: str, day_offset: int) -> str:
    if timing_direction == "before_due" and day_offset == 3:
        return "Upcoming due date for invoice {{ invoice_number }}"
    if timing_direction == "after_due" and day_offset == 3:
        return "Friendly reminder: invoice {{ invoice_number }} is overdue"
    if timing_direction == "after_due" and day_offset == 5:
        return "Payment reminder for invoice {{ invoice_number }}"
    if timing_direction == "after_due" and day_offset == 7:
        return "Action requested: overdue invoice {{ invoice_number }}"
    if timing_direction == "after_due" and day_offset == 10:
        return "Urgent attention required for invoice {{ invoice_number }}"
    if timing_direction == "after_due" and day_offset == 15:
        return "Final reminder before follow-up: invoice {{ invoice_number }}"
    if day_offset == 0:
        return "Reminder: Invoice {{ invoice_number }} is due today"
    if timing_direction == "before_due":
        return f"Reminder: Invoice {{{{ invoice_number }}}} is due in {day_offset} day{'s' if day_offset != 1 else ''}"
    return f"Reminder: Invoice {{{{ invoice_number }}}} is {day_offset} day{'s' if day_offset != 1 else ''} overdue"


def default_invoice_reminder_body_template(timing_direction: str, day_offset: int) -> str:
    if timing_direction == "before_due" and day_offset == 3:
        return (
            "Hi {{ customer_name }},\n\n"
            "We hope you're well. This is a courtesy reminder that invoice {{ invoice_number }} for {{ balance_due }} is due on {{ due_date }}.\n\n"
            "If payment has already been arranged, please disregard this message. Otherwise, we would appreciate payment by the due date.\n\n"
            "Thank you."
        )
    if timing_direction == "after_due" and day_offset == 3:
        return (
            "Hi {{ customer_name }},\n\n"
            "This is a friendly reminder that invoice {{ invoice_number }} for {{ balance_due }} was due on {{ due_date }} and remains outstanding.\n\n"
            "If payment has already been sent, please disregard this reminder. If not, we would appreciate payment at your earliest convenience.\n\n"
            "Thank you."
        )
    if timing_direction == "after_due" and day_offset == 5:
        return (
            "Hi {{ customer_name }},\n\n"
            "We are following up regarding invoice {{ invoice_number }} for {{ balance_due }}, which was due on {{ due_date }} and is still awaiting payment.\n\n"
            "Please arrange payment as soon as possible, or let us know if there is anything we should be aware of.\n\n"
            "Thank you for your prompt attention."
        )
    if timing_direction == "after_due" and day_offset == 7:
        return (
            "Hi {{ customer_name }},\n\n"
            "Invoice {{ invoice_number }} for {{ balance_due }} is now seven days overdue.\n\n"
            "Please arrange payment promptly, or contact us today if you need to discuss the outstanding balance or expected payment timing.\n\n"
            "Thank you."
        )
    if timing_direction == "after_due" and day_offset == 10:
        return (
            "Hi {{ customer_name }},\n\n"
            "Invoice {{ invoice_number }} for {{ balance_due }} remains unpaid ten days after its due date of {{ due_date }}.\n\n"
            "We would appreciate your urgent attention to this matter. Please confirm payment or contact us today to discuss next steps.\n\n"
            "Thank you."
        )
    if timing_direction == "after_due" and day_offset == 15:
        return (
            "Hi {{ customer_name }},\n\n"
            "This is our final reminder before further follow-up regarding invoice {{ invoice_number }} for {{ balance_due }}, originally due on {{ due_date }}.\n\n"
            "Please arrange payment immediately or reply by return email to discuss the overdue balance.\n\n"
            "Thank you for your prompt attention."
        )
    if day_offset == 0:
        timing_text = "is due today"
    elif timing_direction == "before_due":
        timing_text = f"is due in {day_offset} day{'s' if day_offset != 1 else ''}"
    else:
        timing_text = f"is {day_offset} day{'s' if day_offset != 1 else ''} overdue"

    return (
        "Hi {{ customer_name }},\n\n"
        f"This is a reminder that invoice {{{{ invoice_number }}}} {timing_text}.\n"
        "Amount owing: {{ balance_due }}\n"
        "Due date: {{ due_date }}\n\n"
        "Please contact us if payment is already on the way.\n"
    )


SCHEDULER_SETTINGS_DEFAULTS = {
    "invoice_reminder_scheduler_enabled": DEFAULT_SETTINGS.get("invoice_reminder_scheduler_enabled", "false"),
    "invoice_reminder_scheduler_interval_minutes": DEFAULT_SETTINGS.get("invoice_reminder_scheduler_interval_minutes", "15"),
    "invoice_reminder_scheduler_last_started_at": "",
    "invoice_reminder_scheduler_last_heartbeat_at": "",
    "invoice_reminder_scheduler_last_run_started_at": "",
    "invoice_reminder_scheduler_last_run_completed_at": "",
    "invoice_reminder_scheduler_last_run_status": DEFAULT_SETTINGS.get("invoice_reminder_scheduler_last_run_status", "never"),
    "invoice_reminder_scheduler_last_run_summary": "",
    "invoice_reminder_scheduler_last_error": "",
    "invoice_reminder_scheduler_next_run_at": "",
}


def default_invoice_reminder_rule_definitions() -> list[dict]:
    schedule = [
        ("before_due", 3),
        ("after_due", 3),
        ("after_due", 5),
        ("after_due", 7),
        ("after_due", 10),
        ("after_due", 15),
    ]
    definitions = []
    for sort_order, (timing_direction, day_offset) in enumerate(schedule):
        definitions.append({
            "name": invoice_reminder_rule_label(timing_direction, day_offset),
            "timing_direction": timing_direction,
            "day_offset": day_offset,
            "is_enabled": True,
            "sort_order": sort_order,
            "subject_template": default_invoice_reminder_subject_template(timing_direction, day_offset),
            "body_template": default_invoice_reminder_body_template(timing_direction, day_offset),
        })
    return definitions


def ensure_default_invoice_reminder_rules(db: Session) -> list[InvoiceReminderRule]:
    existing = (
        db.query(InvoiceReminderRule)
        .order_by(InvoiceReminderRule.sort_order, InvoiceReminderRule.id)
        .all()
    )
    if existing:
        return existing

    for definition in default_invoice_reminder_rule_definitions():
        db.add(InvoiceReminderRule(**definition))
    db.commit()
    return (
        db.query(InvoiceReminderRule)
        .order_by(InvoiceReminderRule.sort_order, InvoiceReminderRule.id)
        .all()
    )


def company_settings(db: Session) -> dict:
    rows = db.query(Settings).all()
    result = dict(DEFAULT_SETTINGS)
    for row in rows:
        result[row.key] = row.value
    return result


def get_scheduler_state(db: Session) -> dict:
    settings = company_settings(db)
    return {
        "enabled": str(settings.get("invoice_reminder_scheduler_enabled", "false")).lower() == "true",
        "interval_minutes": max(1, int(settings.get("invoice_reminder_scheduler_interval_minutes", "15") or 15)),
        "last_started_at": settings.get("invoice_reminder_scheduler_last_started_at") or None,
        "last_heartbeat_at": settings.get("invoice_reminder_scheduler_last_heartbeat_at") or None,
        "last_run_started_at": settings.get("invoice_reminder_scheduler_last_run_started_at") or None,
        "last_run_completed_at": settings.get("invoice_reminder_scheduler_last_run_completed_at") or None,
        "last_run_status": settings.get("invoice_reminder_scheduler_last_run_status") or "never",
        "last_run_summary": settings.get("invoice_reminder_scheduler_last_run_summary") or "",
        "last_error": settings.get("invoice_reminder_scheduler_last_error") or "",
        "next_run_at": settings.get("invoice_reminder_scheduler_next_run_at") or None,
    }


def _set_setting(db: Session, key: str, value: str | None) -> None:
    row = db.query(Settings).filter(Settings.key == key).first()
    if row:
        row.value = "" if value is None else str(value)
    else:
        db.add(Settings(key=key, value="" if value is None else str(value)))


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def update_scheduler_state(db: Session, **values) -> dict:
    for key, value in values.items():
        if key not in SCHEDULER_SETTINGS_DEFAULTS:
            continue
        _set_setting(db, key, value)
    db.commit()
    return get_scheduler_state(db)


def _latest_audit_map(db: Session, pairs: list[tuple[int, int]]) -> dict[tuple[int, int], InvoiceReminderAudit]:
    if not pairs:
        return {}
    invoice_ids = {invoice_id for invoice_id, _ in pairs}
    rule_ids = {rule_id for _, rule_id in pairs}
    latest: dict[tuple[int, int], InvoiceReminderAudit] = {}
    audits = (
        db.query(InvoiceReminderAudit)
        .filter(InvoiceReminderAudit.invoice_id.in_(invoice_ids))
        .filter(InvoiceReminderAudit.rule_id.in_(rule_ids))
        .order_by(InvoiceReminderAudit.created_at.desc(), InvoiceReminderAudit.id.desc())
        .all()
    )
    for audit in audits:
        latest.setdefault((audit.invoice_id, audit.rule_id), audit)
    return latest


def invoice_reminder_preview_items(db: Session, as_of_date: date) -> list[dict]:
    rules = [rule for rule in ensure_default_invoice_reminder_rules(db) if rule.is_enabled]
    if not rules:
        return []

    invoices = (
        db.query(Invoice)
        .join(Customer, Invoice.customer_id == Customer.id)
        .filter(Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PARTIAL]))
        .filter(Invoice.due_date.is_not(None))
        .filter(Invoice.balance_due > 0)
        .filter(Customer.is_active == True)
        .filter(Customer.invoice_reminders_enabled == True)
        .order_by(Invoice.due_date, Customer.name, Invoice.invoice_number, Invoice.id)
        .all()
    )

    matched_items: list[dict] = []
    matched_keys: list[tuple[int, int]] = []
    for invoice in invoices:
        customer = invoice.customer
        recipient = (customer.email or "").strip() if customer else ""
        if not recipient:
            continue
        days_from_due = (as_of_date - invoice.due_date).days
        for rule in rules:
            is_match = (
                days_from_due == -rule.day_offset
                if rule.timing_direction == "before_due"
                else days_from_due == rule.day_offset
            )
            if not is_match:
                continue
            matched_keys.append((invoice.id, rule.id))
            matched_items.append({
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "customer_id": customer.id,
                "customer_name": customer.name,
                "recipient": recipient,
                "due_date": invoice.due_date,
                "balance_due": invoice.balance_due,
                "days_from_due": days_from_due,
                "rule_id": rule.id,
                "rule_name": rule.name,
                "timing_direction": rule.timing_direction,
                "day_offset": rule.day_offset,
                "last_reminder_sent_at": None,
                "last_reminder_status": None,
                "last_reminder_trigger_type": None,
                "last_reminder_detail": None,
            })

    latest_audits = _latest_audit_map(db, matched_keys)
    for item in matched_items:
        audit = latest_audits.get((item["invoice_id"], item["rule_id"]))
        if audit:
            item["last_reminder_sent_at"] = audit.created_at
            item["last_reminder_status"] = audit.status
            item["last_reminder_trigger_type"] = audit.trigger_type
            item["last_reminder_detail"] = audit.detail

    return matched_items


def _template_context(invoice: Invoice, company: dict) -> dict:
    customer = invoice.customer
    return {
        "invoice_number": invoice.invoice_number,
        "customer_name": customer.name if customer else "Customer",
        "balance_due": format_currency(invoice.balance_due or 0, company),
        "due_date": format_date(invoice.due_date, company) if invoice.due_date else "",
        "company_name": company.get("company_name", "Our Company"),
    }


def render_invoice_reminder_email(rule: InvoiceReminderRule, invoice: Invoice, company: dict) -> tuple[str, str]:
    context = _template_context(invoice, company)
    subject_text = _scheduler_env.from_string(rule.subject_template).render(**context)
    body_text = _scheduler_env.from_string(rule.body_template).render(**context)
    safe_subject = subject_text.replace("\r", "").replace("\n", " ").strip()
    body_lines = html.escape(body_text).replace("\n", "<br>")
    safe_html = (
        f"<html><body><p>{body_lines}</p>"
        f"<p>Kind regards,<br>{html.escape(company.get('company_name', 'Our Company'))}</p></body></html>"
    )
    return safe_subject, safe_html


def _existing_audit(db: Session, invoice_id: int, rule_id: int, scheduled_for_date: date) -> InvoiceReminderAudit | None:
    return (
        db.query(InvoiceReminderAudit)
        .filter(InvoiceReminderAudit.invoice_id == invoice_id)
        .filter(InvoiceReminderAudit.rule_id == rule_id)
        .filter(InvoiceReminderAudit.scheduled_for_date == scheduled_for_date)
        .first()
    )


def dispatch_due_invoice_reminders(db: Session, as_of_date: date, trigger_type: str = "automatic") -> dict:
    company = company_settings(db)
    items = invoice_reminder_preview_items(db, as_of_date)
    if not items:
        return {
            "as_of_date": as_of_date.isoformat(),
            "processed_count": 0,
            "sent_count": 0,
            "failed_count": 0,
            "duplicate_count": 0,
        }

    invoice_ids = {item["invoice_id"] for item in items}
    rule_ids = {item["rule_id"] for item in items}
    invoices = {row.id: row for row in db.query(Invoice).filter(Invoice.id.in_(invoice_ids)).all()}
    rules = {row.id: row for row in db.query(InvoiceReminderRule).filter(InvoiceReminderRule.id.in_(rule_ids)).all()}

    sent_count = 0
    failed_count = 0
    duplicate_count = 0

    for item in items:
        invoice = invoices[item["invoice_id"]]
        rule = rules[item["rule_id"]]
        if _existing_audit(db, invoice.id, rule.id, as_of_date):
            duplicate_count += 1
            continue

        subject = ""
        html_body = ""
        attachment_bytes = None
        log_id = None
        error_detail = None
        status = "sent"
        try:
            subject, html_body = render_invoice_reminder_email(rule, invoice, company)
            attachment_bytes = generate_invoice_pdf(invoice, company)
            attachment_name = f"Invoice_{invoice.invoice_number}.pdf"
            log_id, error_detail = send_document_email_result(
                db,
                to_email=item["recipient"],
                subject=subject,
                html_body=html_body,
                attachment_bytes=attachment_bytes,
                attachment_name=attachment_name,
                entity_type="invoice_reminder",
                entity_id=invoice.id,
            )
            if error_detail:
                status = "failed"
                failed_count += 1
            else:
                sent_count += 1
        except Exception as exc:
            status = "failed"
            failed_count += 1
            error_detail = str(exc)

        audit = InvoiceReminderAudit(
            invoice_id=invoice.id,
            customer_id=invoice.customer_id,
            rule_id=rule.id,
            email_log_id=log_id,
            recipient=item["recipient"],
            status=status,
            trigger_type=trigger_type,
            scheduled_for_date=as_of_date,
            days_from_due_snapshot=item["days_from_due"],
            balance_due_snapshot=item["balance_due"],
            detail=error_detail,
        )
        db.add(audit)
        db.commit()

    return {
        "as_of_date": as_of_date.isoformat(),
        "processed_count": len(items),
        "sent_count": sent_count,
        "failed_count": failed_count,
        "duplicate_count": duplicate_count,
    }


def scheduler_summary_text(summary: dict) -> str:
    return json.dumps(summary, sort_keys=True)
