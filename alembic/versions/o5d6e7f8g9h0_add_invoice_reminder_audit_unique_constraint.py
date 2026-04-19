"""add invoice reminder audit uniqueness

Revision ID: o5d6e7f8g9h0
Revises: n4c5d6e7f8g9
Create Date: 2026-04-19 15:55:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "o5d6e7f8g9h0"
down_revision: Union[str, None] = "n4c5d6e7f8g9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("invoice_reminder_audit") as batch_op:
        batch_op.create_unique_constraint(
            "uq_invoice_reminder_audit_scheduled",
            ["invoice_id", "rule_id", "scheduled_for_date"],
        )


def downgrade() -> None:
    with op.batch_alter_table("invoice_reminder_audit") as batch_op:
        batch_op.drop_constraint("uq_invoice_reminder_audit_scheduled", type_="unique")
