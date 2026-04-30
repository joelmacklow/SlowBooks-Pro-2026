"""persist company logo data uri in settings

Revision ID: w2k3l4m5n6o7
Revises: u1j2k3l4m5n6
Create Date: 2026-04-30 05:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "w2k3l4m5n6o7"
down_revision: Union[str, None] = "u1j2k3l4m5n6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("settings") as batch_op:
        batch_op.alter_column("value", existing_type=sa.String(length=500), type_=sa.Text(), existing_nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("settings") as batch_op:
        batch_op.alter_column("value", existing_type=sa.Text(), type_=sa.String(length=500), existing_nullable=True)
