"""add dashboard favorite flag to accounts

Revision ID: t0i1j2k3l4m5
Revises: s9h0i1j2k3l4
Create Date: 2026-04-23 11:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "t0i1j2k3l4m5"
down_revision: Union[str, None] = "s9h0i1j2k3l4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("accounts") as batch_op:
        batch_op.add_column(sa.Column("is_dashboard_favorite", sa.Boolean(), nullable=True, server_default=sa.false()))

    op.execute("UPDATE accounts SET is_dashboard_favorite = false WHERE is_dashboard_favorite IS NULL")

    with op.batch_alter_table("accounts") as batch_op:
        batch_op.alter_column("is_dashboard_favorite", nullable=False, server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("accounts") as batch_op:
        batch_op.drop_column("is_dashboard_favorite")
