import html
from datetime import date
from decimal import Decimal

from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

from app.models.contacts import Customer
from app.models.email_log import EmailLog
from app.models.invoice_reminders import InvoiceReminderAudit, InvoiceReminderRule
from app.models.invoices import Invoice, InvoiceStatus
from app.models.settings import DEFAULT_SETTINGS, Settings
from app.services.email_service import send_document_email
from app.services.formatting import format_currency, format_date
from app.services.pdf_service import generate_invoice_pdf

_template_env = SandboxedEnvironment(autoescape=True, undefined=StrictUndefined)


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


def ensure_default_invoice_reminder_rules(db) -> list[InvoiceReminderRule]:
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


def _settings_map(db) -> dict:
    result = dict(DEFAULT_SETTINGS)
    for row in db.query(Settings).all():
        result[row.key] = row.value
    return result


def _render_template_string(template_text: str, context: dict) -> str:
    return _template_env.from_string(template_text).render(**context).strip()


def _render_reminder_email_html(message: str) -> str:
    escaped = html.escape(message).replace("\n", "<br>")
    return f"<html><body><p>{escaped}</p></body></html>"


def _reminder_template_context(invoice: Invoice, company_settings: dict) -> dict:
    customer_name = invoice.customer.name if invoice.customer else "Customer"
    return {
        "invoice_number": invoice.invoice_number,
        "customer_name": customer_name,
        "balance_due": format_currency(invoice.balance_due or 0, company_settings),
        "due_date": format_date(invoice.due_date, company_settings) if invoice.due_date else "",
    }


def invoice_reminder_preview_items(db, as_of_date: date) -> list[dict]:
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
                "balance_due": Decimal(str(invoice.balance_due or 0)),
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

    if not matched_items:
        return []

    invoice_ids = {invoice_id for invoice_id, _ in matched_keys}
    rule_ids = {rule_id for _, rule_id in matched_keys}
    latest_audits: dict[tuple[int, int], InvoiceReminderAudit] = {}
    audits = (
        db.query(InvoiceReminderAudit)
        .filter(InvoiceReminderAudit.invoice_id.in_(invoice_ids))
        .filter(InvoiceReminderAudit.rule_id.in_(rule_ids))
        .order_by(InvoiceReminderAudit.created_at.desc(), InvoiceReminderAudit.id.desc())
        .all()
    )
    for audit in audits:
        latest_audits.setdefault((audit.invoice_id, audit.rule_id), audit)

    for item in matched_items:
        audit = latest_audits.get((item["invoice_id"], item["rule_id"]))
        if audit:
            item["last_reminder_sent_at"] = audit.created_at
            item["last_reminder_status"] = audit.status
            item["last_reminder_trigger_type"] = audit.trigger_type
            item["last_reminder_detail"] = audit.detail

    return matched_items


def send_document_email_with_log(
    db,
    *,
    to_email: str,
    subject: str,
    html_body: str,
    attachment_bytes: bytes,
    attachment_name: str,
    entity_type: str,
    entity_id: int,
):
    send_document_email(
        db,
        to_email=to_email,
        subject=subject,
        html_body=html_body,
        attachment_bytes=attachment_bytes,
        attachment_name=attachment_name,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    return (
        db.query(EmailLog)
        .filter(EmailLog.entity_type == entity_type)
        .filter(EmailLog.entity_id == entity_id)
        .filter(EmailLog.recipient == to_email)
        .filter(EmailLog.subject == subject)
        .order_by(EmailLog.id.desc())
        .first()
    )


def process_automatic_invoice_reminders(db, as_of_date: date | None = None) -> dict:
    as_of_date = as_of_date or date.today()
    items = invoice_reminder_preview_items(db, as_of_date)
    if not items:
        return {"as_of_date": as_of_date, "sent_count": 0, "failed_count": 0, "skipped_count": 0, "results": []}

    attempted_keys = {
        (audit.invoice_id, audit.rule_id, audit.scheduled_for_date)
        for audit in db.query(InvoiceReminderAudit)
        .filter(InvoiceReminderAudit.trigger_type == "automatic")
        .filter(InvoiceReminderAudit.scheduled_for_date == as_of_date)
        .all()
    }
    invoice_ids = {item["invoice_id"] for item in items}
    rule_ids = {item["rule_id"] for item in items}
    invoices = {
        row.id: row
        for row in db.query(Invoice)
        .filter(Invoice.id.in_(invoice_ids))
        .all()
    }
    rules = {
        row.id: row
        for row in db.query(InvoiceReminderRule)
        .filter(InvoiceReminderRule.id.in_(rule_ids))
        .all()
    }
    company_settings = _settings_map(db)

    results: list[dict] = []
    sent_count = failed_count = skipped_count = 0

    for item in items:
        attempt_key = (item["invoice_id"], item["rule_id"], as_of_date)
        if attempt_key in attempted_keys:
            skipped_count += 1
            results.append({
                "invoice_id": item["invoice_id"],
                "rule_id": item["rule_id"],
                "status": "skipped",
                "detail": "Automatic reminder already attempted for this scheduled date",
            })
            continue

        invoice = invoices[item["invoice_id"]]
        rule = rules[item["rule_id"]]
        context = _reminder_template_context(invoice, company_settings)
        try:
            subject = _render_template_string(rule.subject_template, context).replace("\r", "").replace("\n", " ").strip()
            body_text = _render_template_string(rule.body_template, context)
            html_body = _render_reminder_email_html(body_text)
            pdf_bytes = generate_invoice_pdf(invoice, company_settings)
            email_log = send_document_email_with_log(
                db,
                to_email=item["recipient"],
                subject=subject or f"Invoice #{invoice.invoice_number}",
                html_body=html_body,
                attachment_bytes=pdf_bytes,
                attachment_name=f"Invoice_{invoice.invoice_number}.pdf",
                entity_type="invoice",
                entity_id=invoice.id,
            )
            db.add(InvoiceReminderAudit(
                invoice_id=invoice.id,
                customer_id=item["customer_id"],
                rule_id=rule.id,
                email_log_id=email_log.id if email_log else None,
                recipient=item["recipient"],
                status="sent",
                trigger_type="automatic",
                scheduled_for_date=as_of_date,
                days_from_due_snapshot=item["days_from_due"],
                balance_due_snapshot=Decimal(str(invoice.balance_due or 0)),
                detail=None,
            ))
            db.commit()
            sent_count += 1
            attempted_keys.add(attempt_key)
            results.append({
                "invoice_id": invoice.id,
                "rule_id": rule.id,
                "status": "sent",
                "detail": None,
            })
        except Exception as exc:
            db.add(InvoiceReminderAudit(
                invoice_id=invoice.id,
                customer_id=item["customer_id"],
                rule_id=rule.id,
                email_log_id=None,
                recipient=item["recipient"],
                status="failed",
                trigger_type="automatic",
                scheduled_for_date=as_of_date,
                days_from_due_snapshot=item["days_from_due"],
                balance_due_snapshot=Decimal(str(invoice.balance_due or 0)),
                detail=str(exc),
            ))
            db.commit()
            failed_count += 1
            attempted_keys.add(attempt_key)
            results.append({
                "invoice_id": invoice.id,
                "rule_id": rule.id,
                "status": "failed",
                "detail": str(exc),
            })

    return {
        "as_of_date": as_of_date,
        "sent_count": sent_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "results": results,
    }
