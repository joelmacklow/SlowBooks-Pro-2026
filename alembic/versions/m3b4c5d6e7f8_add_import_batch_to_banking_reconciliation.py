"""add import batch to banking reconciliation

Revision ID: m3b4c5d6e7f8
Revises: l2a3b4c5d6e7
Create Date: 2026-04-17 18:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "m3b4c5d6e7f8"
down_revision: Union[str, None] = "l2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("bank_transactions") as batch_op:
        batch_op.add_column(sa.Column("import_batch_id", sa.String(length=64), nullable=True))

    with op.batch_alter_table("reconciliations") as batch_op:
        batch_op.add_column(sa.Column("import_batch_id", sa.String(length=64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("reconciliations") as batch_op:
        batch_op.drop_column("import_batch_id")

    with op.batch_alter_table("bank_transactions") as batch_op:
        batch_op.drop_column("import_batch_id")
