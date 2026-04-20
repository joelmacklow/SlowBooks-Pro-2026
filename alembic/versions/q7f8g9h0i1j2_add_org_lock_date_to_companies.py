"""add org lock date to companies

Revision ID: q7f8g9h0i1j2
Revises: p6e7f8g9h0i1
Create Date: 2026-04-20 17:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "q7f8g9h0i1j2"
down_revision: Union[str, None] = "p6e7f8g9h0i1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("companies") as batch_op:
        batch_op.add_column(sa.Column("org_lock_date", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("companies") as batch_op:
        batch_op.drop_column("org_lock_date")
