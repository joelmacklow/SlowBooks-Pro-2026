"""add item code field

Revision ID: r8g9h0i1j2k3
Revises: q7f8g9h0i1j2
Create Date: 2026-04-20 18:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "r8g9h0i1j2k3"
down_revision: Union[str, None] = "q7f8g9h0i1j2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("items") as batch_op:
        batch_op.add_column(sa.Column("code", sa.String(length=50), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("items") as batch_op:
        batch_op.drop_column("code")
