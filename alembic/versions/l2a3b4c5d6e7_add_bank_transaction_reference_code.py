"""add bank transaction reference and code

Revision ID: l2a3b4c5d6e7
Revises: k1f2a3b4c5d6
Create Date: 2026-04-17 15:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "l2a3b4c5d6e7"
down_revision: Union[str, None] = "k1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("bank_transactions") as batch_op:
        batch_op.add_column(sa.Column("reference", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("code", sa.String(length=100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("bank_transactions") as batch_op:
        batch_op.drop_column("code")
        batch_op.drop_column("reference")
