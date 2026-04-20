"""stage imported bank balance until reconciliation complete

Revision ID: p6e7f8g9h0i1
Revises: o5d6e7f8g9h0
Create Date: 2026-04-20 15:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p6e7f8g9h0i1"
down_revision: Union[str, None] = "o5d6e7f8g9h0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("reconciliations") as batch_op:
        batch_op.add_column(sa.Column("balance_applied_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("reconciliations") as batch_op:
        batch_op.drop_column("balance_applied_at")
