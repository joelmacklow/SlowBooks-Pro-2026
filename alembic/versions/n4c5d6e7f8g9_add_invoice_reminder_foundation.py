"""add invoice reminder foundation

Revision ID: n4c5d6e7f8g9
Revises: m3b4c5d6e7f8
Create Date: 2026-04-19 15:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "n4c5d6e7f8g9"
down_revision: Union[str, None] = "m3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("customers") as batch_op:
        batch_op.add_column(sa.Column("invoice_reminders_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))

    op.create_table(
        "invoice_reminder_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("timing_direction", sa.String(length=20), nullable=False),
        sa.Column("day_offset", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("subject_template", sa.String(length=500), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoice_reminder_rules_id"), "invoice_reminder_rules", ["id"], unique=False)

    rules_table = sa.table(
        "invoice_reminder_rules",
        sa.column("name", sa.String(length=200)),
        sa.column("timing_direction", sa.String(length=20)),
        sa.column("day_offset", sa.Integer()),
        sa.column("is_enabled", sa.Boolean()),
        sa.column("sort_order", sa.Integer()),
        sa.column("subject_template", sa.String(length=500)),
        sa.column("body_template", sa.Text()),
    )
    op.bulk_insert(
        rules_table,
        [
            {
                "name": "3 days before due",
                "timing_direction": "before_due",
                "day_offset": 3,
                "is_enabled": True,
                "sort_order": 0,
                "subject_template": "Upcoming due date for invoice {{ invoice_number }}",
                "body_template": "Hi {{ customer_name }},\n\nWe hope you're well. This is a courtesy reminder that invoice {{ invoice_number }} for {{ balance_due }} is due on {{ due_date }}.\n\nIf payment has already been arranged, please disregard this message. Otherwise, we would appreciate payment by the due date.\n\nThank you.",
            },
            {
                "name": "3 days overdue",
                "timing_direction": "after_due",
                "day_offset": 3,
                "is_enabled": True,
                "sort_order": 1,
                "subject_template": "Friendly reminder: invoice {{ invoice_number }} is overdue",
                "body_template": "Hi {{ customer_name }},\n\nThis is a friendly reminder that invoice {{ invoice_number }} for {{ balance_due }} was due on {{ due_date }} and remains outstanding.\n\nIf payment has already been sent, please disregard this reminder. If not, we would appreciate payment at your earliest convenience.\n\nThank you.",
            },
            {
                "name": "5 days overdue",
                "timing_direction": "after_due",
                "day_offset": 5,
                "is_enabled": True,
                "sort_order": 2,
                "subject_template": "Payment reminder for invoice {{ invoice_number }}",
                "body_template": "Hi {{ customer_name }},\n\nWe are following up regarding invoice {{ invoice_number }} for {{ balance_due }}, which was due on {{ due_date }} and is still awaiting payment.\n\nPlease arrange payment as soon as possible, or let us know if there is anything we should be aware of.\n\nThank you for your prompt attention.",
            },
            {
                "name": "7 days overdue",
                "timing_direction": "after_due",
                "day_offset": 7,
                "is_enabled": True,
                "sort_order": 3,
                "subject_template": "Action requested: overdue invoice {{ invoice_number }}",
                "body_template": "Hi {{ customer_name }},\n\nInvoice {{ invoice_number }} for {{ balance_due }} is now seven days overdue.\n\nPlease arrange payment promptly, or contact us today if you need to discuss the outstanding balance or expected payment timing.\n\nThank you.",
            },
            {
                "name": "10 days overdue",
                "timing_direction": "after_due",
                "day_offset": 10,
                "is_enabled": True,
                "sort_order": 4,
                "subject_template": "Urgent attention required for invoice {{ invoice_number }}",
                "body_template": "Hi {{ customer_name }},\n\nInvoice {{ invoice_number }} for {{ balance_due }} remains unpaid ten days after its due date of {{ due_date }}.\n\nWe would appreciate your urgent attention to this matter. Please confirm payment or contact us today to discuss next steps.\n\nThank you.",
            },
            {
                "name": "15 days overdue",
                "timing_direction": "after_due",
                "day_offset": 15,
                "is_enabled": True,
                "sort_order": 5,
                "subject_template": "Final reminder before follow-up: invoice {{ invoice_number }}",
                "body_template": "Hi {{ customer_name }},\n\nThis is our final reminder before further follow-up regarding invoice {{ invoice_number }} for {{ balance_due }}, originally due on {{ due_date }}.\n\nPlease arrange payment immediately or reply by return email to discuss the overdue balance.\n\nThank you for your prompt attention.",
            },
        ],
    )

    op.create_table(
        "invoice_reminder_audit",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("email_log_id", sa.Integer(), nullable=True),
        sa.Column("recipient", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("trigger_type", sa.String(length=20), nullable=False),
        sa.Column("scheduled_for_date", sa.Date(), nullable=False),
        sa.Column("days_from_due_snapshot", sa.Integer(), nullable=False),
        sa.Column("balance_due_snapshot", sa.Numeric(12, 2), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["email_log_id"], ["email_log.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["rule_id"], ["invoice_reminder_rules.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoice_reminder_audit_id"), "invoice_reminder_audit", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_invoice_reminder_audit_id"), table_name="invoice_reminder_audit")
    op.drop_table("invoice_reminder_audit")
    op.drop_index(op.f("ix_invoice_reminder_rules_id"), table_name="invoice_reminder_rules")
    op.drop_table("invoice_reminder_rules")

    with op.batch_alter_table("customers") as batch_op:
        batch_op.drop_column("invoice_reminders_enabled")
