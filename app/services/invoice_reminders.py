from app.models.invoice_reminders import InvoiceReminderRule


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
