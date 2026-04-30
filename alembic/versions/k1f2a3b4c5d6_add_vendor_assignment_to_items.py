"""add vendor assignment to items

Revision ID: k1f2a3b4c5d6
Revises: j0e1f2a3b4c5
Create Date: 2026-04-17 12:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "k1f2a3b4c5d6"
down_revision: Union[str, None] = "j0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("items", sa.Column("vendor_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_items_vendor_id_vendors", "items", "vendors", ["vendor_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_items_vendor_id_vendors", "items", type_="foreignkey")
    op.drop_column("items", "vendor_id")
