"""add employee portal links

Revision ID: x1y2z3a4b5c6
Revises: w2k3l4m5n6o7
Create Date: 2026-04-30 06:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "x1y2z3a4b5c6"
down_revision: Union[str, None] = "w2k3l4m5n6o7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee_portal_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("company_scope", sa.String(length=100), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("deactivated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deactivated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_employee_portal_links_id"), "employee_portal_links", ["id"], unique=False)
    op.create_index(
        "uq_employee_portal_links_user_scope_active",
        "employee_portal_links",
        ["user_id", "company_scope"],
        unique=True,
        sqlite_where=sa.text("is_active = 1"),
        postgresql_where=sa.text("is_active = true"),
    )
    op.create_index(
        "uq_employee_portal_links_scope_employee_active",
        "employee_portal_links",
        ["company_scope", "employee_id"],
        unique=True,
        sqlite_where=sa.text("is_active = 1"),
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_employee_portal_links_scope_employee_active", table_name="employee_portal_links")
    op.drop_index("uq_employee_portal_links_user_scope_active", table_name="employee_portal_links")
    op.drop_index(op.f("ix_employee_portal_links_id"), table_name="employee_portal_links")
    op.drop_table("employee_portal_links")
