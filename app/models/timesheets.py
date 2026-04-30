import enum

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class TimesheetStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    LOCKED = "locked"


class TimesheetEntryMode(str, enum.Enum):
    DURATION = "duration"
    START_END = "start_end"


class Timesheet(Base):
    __tablename__ = "timesheets"
    __table_args__ = (
        UniqueConstraint("employee_id", "period_start", "period_end", name="uq_timesheet_employee_period"),
    )

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    pay_run_id = Column(Integer, ForeignKey("pay_runs.id"), nullable=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    status = Column(Enum(TimesheetStatus), nullable=False, default=TimesheetStatus.DRAFT)
    total_hours = Column(Numeric(10, 2), nullable=False, default=0)

    submitted_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    employee = relationship("Employee")
    pay_run = relationship("PayRun")
    lines = relationship("TimesheetLine", back_populates="timesheet", cascade="all, delete-orphan")
    audit_events = relationship("TimesheetAuditEvent", back_populates="timesheet", cascade="all, delete-orphan")


class TimesheetLine(Base):
    __tablename__ = "timesheet_lines"

    id = Column(Integer, primary_key=True, index=True)
    timesheet_id = Column(Integer, ForeignKey("timesheets.id", ondelete="CASCADE"), nullable=False)
    work_date = Column(Date, nullable=False)
    entry_mode = Column(Enum(TimesheetEntryMode), nullable=False, default=TimesheetEntryMode.DURATION)
    duration_hours = Column(Numeric(10, 2), nullable=True)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    break_minutes = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    timesheet = relationship("Timesheet", back_populates="lines")
    audit_events = relationship("TimesheetAuditEvent", back_populates="timesheet_line")


class TimesheetAuditEvent(Base):
    __tablename__ = "timesheet_audit_events"

    id = Column(Integer, primary_key=True, index=True)
    timesheet_id = Column(Integer, ForeignKey("timesheets.id", ondelete="CASCADE"), nullable=False)
    timesheet_line_id = Column(Integer, ForeignKey("timesheet_lines.id", ondelete="SET NULL"), nullable=True)
    actor_user_id = Column(Integer, nullable=True)
    action = Column(String(60), nullable=False)
    status_from = Column(Enum(TimesheetStatus), nullable=True)
    status_to = Column(Enum(TimesheetStatus), nullable=True)
    reason = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    timesheet = relationship("Timesheet", back_populates="audit_events")
    timesheet_line = relationship("TimesheetLine", back_populates="audit_events")
