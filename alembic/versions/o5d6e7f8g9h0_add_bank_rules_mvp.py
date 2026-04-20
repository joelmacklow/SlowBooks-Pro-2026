"""add bank rules mvp

Revision ID: o5d6e7f8g9h0
Revises: n4c5d6e7f8g9
Create Date: 2026-04-20 14:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "o5d6e7f8g9h0"
down_revision: Union[str, None] = "n4c5d6e7f8g9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


direction_enum = postgresql.ENUM("any", "inflow", "outflow", name="bankruledirection")
direction_enum_column = postgresql.ENUM("any", "inflow", "outflow", name="bankruledirection", create_type=False)


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE bankruledirection AS ENUM ('any', 'inflow', 'outflow');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    op.create_table(
        "bank_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("bank_account_id", sa.Integer(), nullable=True),
        sa.Column("direction", direction_enum_column, nullable=False, server_default="any"),
        sa.Column("payee_contains", sa.String(length=200), nullable=True),
        sa.Column("description_contains", sa.String(length=200), nullable=True),
        sa.Column("reference_contains", sa.String(length=200), nullable=True),
        sa.Column("code_equals", sa.String(length=100), nullable=True),
        sa.Column("target_account_id", sa.Integer(), nullable=False),
        sa.Column("default_description", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["bank_account_id"], ["bank_accounts.id"]),
        sa.ForeignKeyConstraint(["target_account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bank_rules_id"), "bank_rules", ["id"], unique=False)

    with op.batch_alter_table("bank_transactions") as batch_op:
        batch_op.add_column(sa.Column("suggested_rule_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("suggested_account_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("rule_match_reason", sa.String(length=500), nullable=True))
        batch_op.create_foreign_key("fk_bank_transactions_suggested_rule_id", "bank_rules", ["suggested_rule_id"], ["id"])
        batch_op.create_foreign_key("fk_bank_transactions_suggested_account_id", "accounts", ["suggested_account_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("bank_transactions") as batch_op:
        batch_op.drop_constraint("fk_bank_transactions_suggested_account_id", type_="foreignkey")
        batch_op.drop_constraint("fk_bank_transactions_suggested_rule_id", type_="foreignkey")
        batch_op.drop_column("rule_match_reason")
        batch_op.drop_column("suggested_account_id")
        batch_op.drop_column("suggested_rule_id")

    op.drop_index(op.f("ix_bank_rules_id"), table_name="bank_rules")
    op.drop_table("bank_rules")
    direction_enum.drop(op.get_bind(), checkfirst=True)
