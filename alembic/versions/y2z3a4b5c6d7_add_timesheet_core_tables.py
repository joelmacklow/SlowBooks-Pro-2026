"""add timesheet core tables

Revision ID: y2z3a4b5c6d7
Revises: x1y2z3a4b5c6
Create Date: 2026-04-30 19:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "y2z3a4b5c6d7"
down_revision: Union[str, None] = "x1y2z3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


timesheet_status = sa.Enum("draft", "submitted", "approved", "rejected", "locked", name="timesheetstatus")
timesheet_entry_mode = sa.Enum("duration", "start_end", name="timesheetentrymode")


def upgrade() -> None:
    op.create_table(
        "timesheets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("pay_run_id", sa.Integer(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", timesheet_status, nullable=False, server_default="draft"),
        sa.Column("total_hours", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pay_run_id"], ["pay_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "period_start", "period_end", name="uq_timesheet_employee_period"),
    )
    op.create_index(op.f("ix_timesheets_id"), "timesheets", ["id"], unique=False)
    op.create_index("ix_timesheets_employee_period", "timesheets", ["employee_id", "period_start", "period_end"], unique=False)
    op.create_index("ix_timesheets_status", "timesheets", ["status"], unique=False)

    op.create_table(
        "timesheet_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timesheet_id", sa.Integer(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("entry_mode", timesheet_entry_mode, nullable=False, server_default="duration"),
        sa.Column("duration_hours", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("break_minutes", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["timesheet_id"], ["timesheets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_timesheet_lines_id"), "timesheet_lines", ["id"], unique=False)
    op.create_index("ix_timesheet_lines_timesheet_work_date", "timesheet_lines", ["timesheet_id", "work_date"], unique=False)

    op.create_table(
        "timesheet_audit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timesheet_id", sa.Integer(), nullable=False),
        sa.Column("timesheet_line_id", sa.Integer(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("status_from", timesheet_status, nullable=True),
        sa.Column("status_to", timesheet_status, nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["timesheet_id"], ["timesheets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["timesheet_line_id"], ["timesheet_lines.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_timesheet_audit_events_id"), "timesheet_audit_events", ["id"], unique=False)
    op.create_index("ix_timesheet_audit_events_timesheet_created", "timesheet_audit_events", ["timesheet_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_timesheet_audit_events_timesheet_created", table_name="timesheet_audit_events")
    op.drop_index(op.f("ix_timesheet_audit_events_id"), table_name="timesheet_audit_events")
    op.drop_table("timesheet_audit_events")

    op.drop_index("ix_timesheet_lines_timesheet_work_date", table_name="timesheet_lines")
    op.drop_index(op.f("ix_timesheet_lines_id"), table_name="timesheet_lines")
    op.drop_table("timesheet_lines")

    op.drop_index("ix_timesheets_status", table_name="timesheets")
    op.drop_index("ix_timesheets_employee_period", table_name="timesheets")
    op.drop_index(op.f("ix_timesheets_id"), table_name="timesheets")
    op.drop_table("timesheets")

    timesheet_entry_mode.drop(op.get_bind(), checkfirst=True)
    timesheet_status.drop(op.get_bind(), checkfirst=True)
