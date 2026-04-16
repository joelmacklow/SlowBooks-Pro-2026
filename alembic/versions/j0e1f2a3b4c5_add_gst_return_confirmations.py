"""add gst return confirmations

Revision ID: j0e1f2a3b4c5
Revises: i9d0e1f2a3b4
Create Date: 2026-04-16 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "j0e1f2a3b4c5"
down_revision: Union[str, None] = "i9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gst_returns",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("gst_basis", sa.String(length=20), nullable=False),
        sa.Column("gst_period", sa.String(length=20), nullable=False),
        sa.Column("net_position", sa.String(length=20), nullable=False),
        sa.Column("box5", sa.Numeric(12, 2), nullable=False),
        sa.Column("box6", sa.Numeric(12, 2), nullable=False),
        sa.Column("box7", sa.Numeric(12, 2), nullable=False),
        sa.Column("box8", sa.Numeric(12, 2), nullable=False),
        sa.Column("box9", sa.Numeric(12, 2), nullable=False),
        sa.Column("box10", sa.Numeric(12, 2), nullable=False),
        sa.Column("box11", sa.Numeric(12, 2), nullable=False),
        sa.Column("box12", sa.Numeric(12, 2), nullable=False),
        sa.Column("box13", sa.Numeric(12, 2), nullable=False),
        sa.Column("box14", sa.Numeric(12, 2), nullable=False),
        sa.Column("box15", sa.Numeric(12, 2), nullable=False),
        sa.Column("output_gst", sa.Numeric(12, 2), nullable=False),
        sa.Column("input_gst", sa.Numeric(12, 2), nullable=False),
        sa.Column("net_gst", sa.Numeric(12, 2), nullable=False),
        sa.Column("box9_adjustments", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("box13_adjustments", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("status", sa.Enum("CONFIRMED", "VOIDED", name="gstreturnstatus"), nullable=False, server_default="CONFIRMED"),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.UniqueConstraint("start_date", "end_date", name="uq_gst_returns_period"),
    )


def downgrade() -> None:
    op.drop_table("gst_returns")
    sa.Enum("CONFIRMED", "VOIDED", name="gstreturnstatus").drop(op.get_bind(), checkfirst=False)
