"""add gst codes

Revision ID: a1f7c8d9e0b1
Revises: 27e17711c1a2
Create Date: 2026-04-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1f7c8d9e0b1"
down_revision: Union[str, None] = "27e17711c1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gst_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rate", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_gst_codes_code"), "gst_codes", ["code"], unique=False)
    op.create_index(op.f("ix_gst_codes_id"), "gst_codes", ["id"], unique=False)

    gst_codes = sa.table(
        "gst_codes",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("rate", sa.Numeric),
        sa.column("category", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("is_system", sa.Boolean),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(
        gst_codes,
        [
            {
                "code": "GST15",
                "name": "GST 15%",
                "description": "Standard-rated New Zealand GST at 15%.",
                "rate": 0.1500,
                "category": "taxable",
                "is_active": True,
                "is_system": True,
                "sort_order": 10,
            },
            {
                "code": "ZERO",
                "name": "Zero-rated",
                "description": "Zero-rated taxable supplies.",
                "rate": 0.0000,
                "category": "zero_rated",
                "is_active": True,
                "is_system": True,
                "sort_order": 20,
            },
            {
                "code": "EXEMPT",
                "name": "Exempt",
                "description": "GST-exempt supplies.",
                "rate": 0.0000,
                "category": "exempt",
                "is_active": True,
                "is_system": True,
                "sort_order": 30,
            },
            {
                "code": "NO_GST",
                "name": "No GST",
                "description": "Out-of-scope or non-GST transactions.",
                "rate": 0.0000,
                "category": "no_gst",
                "is_active": True,
                "is_system": True,
                "sort_order": 40,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_gst_codes_id"), table_name="gst_codes")
    op.drop_index(op.f("ix_gst_codes_code"), table_name="gst_codes")
    op.drop_table("gst_codes")
