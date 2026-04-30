"""add monthly statements flag to customers

Revision ID: s9h0i1j2k3l4
Revises: r8g9h0i1j2k3
Create Date: 2026-04-21 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "s9h0i1j2k3l4"
down_revision: Union[str, None] = "r8g9h0i1j2k3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("customers") as batch_op:
        batch_op.add_column(sa.Column("monthly_statements_enabled", sa.Boolean(), nullable=True, server_default=sa.false()))

    op.execute("UPDATE customers SET monthly_statements_enabled = false WHERE monthly_statements_enabled IS NULL")

    with op.batch_alter_table("customers") as batch_op:
        batch_op.alter_column("monthly_statements_enabled", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("customers") as batch_op:
        batch_op.drop_column("monthly_statements_enabled")
