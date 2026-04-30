import csv
from io import StringIO
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models.payroll import Employee
from app.models.timesheets import (
    Timesheet,
    TimesheetAuditEvent,
    TimesheetEntryMode,
    TimesheetLine,
    TimesheetStatus,
)
from app.schemas.timesheets import TimesheetLineUpsert


HOURS_QUANTIZE = Decimal("0.01")
MAX_LINE_HOURS = Decimal("24.00")


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _normalize_hours(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(HOURS_QUANTIZE, rounding=ROUND_HALF_UP)


def _status_value(status: TimesheetStatus | str | None) -> str | None:
    if status is None:
        return None
    return status.value if hasattr(status, "value") else str(status)


def _coerce_status(status: TimesheetStatus | str | None) -> TimesheetStatus | None:
    if status is None:
        return None
    if isinstance(status, TimesheetStatus):
        return status
    normalized = _status_value(status)
    for candidate in TimesheetStatus:
        if candidate.value == normalized:
            return candidate
    raise ValueError(f"Unsupported timesheet status {status}")


def _parse_entry_mode(value: str) -> TimesheetEntryMode:
    normalized = str(value or "").strip().lower()
    if normalized == TimesheetEntryMode.DURATION.value:
        return TimesheetEntryMode.DURATION
    if normalized == TimesheetEntryMode.START_END.value:
        return TimesheetEntryMode.START_END
    raise ValueError("Unsupported timesheet entry mode")


def _validate_period(period_start, period_end) -> None:
    if period_start > period_end:
        raise ValueError("Timesheet period start must be on or before period end")


def _line_duration_hours(line: TimesheetLineUpsert, period_start, period_end) -> Decimal:
    if not (period_start <= line.work_date <= period_end):
        raise ValueError("Timesheet line work date must be within the period")

    mode = _parse_entry_mode(line.entry_mode)
    if mode == TimesheetEntryMode.DURATION:
        if line.duration_hours is None:
            raise ValueError("Duration hours are required for duration entry mode")
        duration = Decimal(str(line.duration_hours))
        if duration <= 0:
            raise ValueError("Duration hours must be greater than zero")
        if duration > MAX_LINE_HOURS:
            raise ValueError("Duration hours cannot exceed 24.00 for a single line")
        return _normalize_hours(duration)

    if line.start_time is None or line.end_time is None:
        raise ValueError("Start and end time are required for start/end entry mode")
    if line.end_time < line.start_time:
        raise ValueError("Overnight shifts are not supported in this timesheet MVP")
    if line.end_time == line.start_time:
        raise ValueError("Start/end entry mode requires positive net worked hours")

    start_minutes = (line.start_time.hour * 60) + line.start_time.minute
    end_minutes = (line.end_time.hour * 60) + line.end_time.minute
    shift_minutes = end_minutes - start_minutes
    if shift_minutes <= 0:
        raise ValueError("Start/end entry mode requires positive net worked hours")

    break_minutes = int(line.break_minutes or 0)
    if break_minutes < 0:
        raise ValueError("Break minutes must be non-negative")
    if break_minutes >= shift_minutes:
        raise ValueError("Break minutes must be less than the worked shift duration")

    net_minutes = shift_minutes - break_minutes
    if net_minutes <= 0:
        raise ValueError("Start/end entry mode requires positive net worked hours")
    return _normalize_hours(Decimal(net_minutes) / Decimal("60"))


def _build_line_models(lines: list[TimesheetLineUpsert], period_start, period_end) -> tuple[list[TimesheetLine], Decimal]:
    if not lines:
        raise ValueError("Timesheet must include at least one line")

    built_lines: list[TimesheetLine] = []
    total_hours = Decimal("0.00")
    for payload in lines:
        duration = _line_duration_hours(payload, period_start, period_end)
        mode = _parse_entry_mode(payload.entry_mode)
        model = TimesheetLine(
            work_date=payload.work_date,
            entry_mode=mode,
            duration_hours=duration,
            start_time=payload.start_time if mode == TimesheetEntryMode.START_END else None,
            end_time=payload.end_time if mode == TimesheetEntryMode.START_END else None,
            break_minutes=int(payload.break_minutes or 0) if mode == TimesheetEntryMode.START_END else None,
            notes=payload.notes,
        )
        built_lines.append(model)
        total_hours += duration
    return built_lines, _normalize_hours(total_hours)


def _add_audit_event(
    db: Session,
    *,
    timesheet: Timesheet,
    action: str,
    actor_user_id: int | None,
    status_from: TimesheetStatus | str | None = None,
    status_to: TimesheetStatus | str | None = None,
    reason: str | None = None,
) -> None:
    db.add(TimesheetAuditEvent(
        timesheet=timesheet,
        actor_user_id=actor_user_id,
        action=action,
        status_from=_coerce_status(status_from),
        status_to=_coerce_status(status_to),
        reason=reason,
    ))


def _ensure_unique_employee_period(
    db: Session,
    *,
    employee_id: int,
    period_start,
    period_end,
    excluding_timesheet_id: int | None = None,
) -> None:
    q = db.query(Timesheet).filter(
        Timesheet.employee_id == employee_id,
        Timesheet.period_start == period_start,
        Timesheet.period_end == period_end,
    )
    if excluding_timesheet_id is not None:
        q = q.filter(Timesheet.id != excluding_timesheet_id)
    if q.first() is not None:
        raise ValueError("Timesheet already exists for this employee and period")


def _get_timesheet(db: Session, timesheet_id: int) -> Timesheet:
    timesheet = db.query(Timesheet).filter(Timesheet.id == timesheet_id).first()
    if not timesheet:
        raise ValueError("Timesheet not found")
    return timesheet


def list_timesheets_for_employee(
    db: Session,
    *,
    employee_id: int,
    status: TimesheetStatus | str | None = None,
    period_start=None,
    period_end=None,
) -> list[Timesheet]:
    q = db.query(Timesheet).filter(Timesheet.employee_id == employee_id)
    parsed_status = _coerce_status(status) if status is not None else None
    if parsed_status is not None:
        q = q.filter(Timesheet.status == parsed_status)
    if period_start is not None:
        q = q.filter(Timesheet.period_start >= period_start)
    if period_end is not None:
        q = q.filter(Timesheet.period_end <= period_end)
    return q.order_by(Timesheet.period_start.desc(), Timesheet.id.desc()).all()


def get_timesheet_for_employee(db: Session, *, timesheet_id: int, employee_id: int) -> Timesheet:
    timesheet = (
        db.query(Timesheet)
        .filter(Timesheet.id == timesheet_id, Timesheet.employee_id == employee_id)
        .first()
    )
    if not timesheet:
        raise ValueError("Timesheet not found")
    return timesheet


def export_timesheet_csv(timesheet: Timesheet) -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "timesheet_id",
        "period_start",
        "period_end",
        "status",
        "work_date",
        "entry_mode",
        "duration_hours",
        "start_time",
        "end_time",
        "break_minutes",
    ])

    sorted_lines = sorted(
        list(timesheet.lines or []),
        key=lambda line: (line.work_date, getattr(line, "id", 0) or 0),
    )
    for line in sorted_lines:
        writer.writerow([
            timesheet.id,
            timesheet.period_start.isoformat(),
            timesheet.period_end.isoformat(),
            _status_value(timesheet.status),
            line.work_date.isoformat() if line.work_date else "",
            _status_value(line.entry_mode),
            str(line.duration_hours) if line.duration_hours is not None else "",
            line.start_time.isoformat() if line.start_time else "",
            line.end_time.isoformat() if line.end_time else "",
            str(line.break_minutes) if line.break_minutes is not None else "",
        ])
    return output.getvalue()


def create_timesheet(
    db: Session,
    *,
    employee_id: int,
    period_start,
    period_end,
    lines: list[TimesheetLineUpsert],
    actor_user_id: int | None = None,
) -> Timesheet:
    _validate_period(period_start, period_end)
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise ValueError("Employee not found")
    if not bool(employee.is_active):
        raise ValueError("Timesheet employee must be active")
    _ensure_unique_employee_period(db, employee_id=employee_id, period_start=period_start, period_end=period_end)
    built_lines, total_hours = _build_line_models(lines, period_start, period_end)

    timesheet = Timesheet(
        employee_id=employee_id,
        period_start=period_start,
        period_end=period_end,
        status=TimesheetStatus.DRAFT,
        total_hours=total_hours,
        lines=built_lines,
    )
    db.add(timesheet)
    db.flush()
    _add_audit_event(
        db,
        timesheet=timesheet,
        action="create",
        actor_user_id=actor_user_id,
        status_from=None,
        status_to=TimesheetStatus.DRAFT,
    )
    db.commit()
    db.refresh(timesheet)
    return timesheet


def update_timesheet(
    db: Session,
    *,
    timesheet_id: int,
    lines: list[TimesheetLineUpsert],
    actor_user_id: int | None = None,
) -> Timesheet:
    timesheet = _get_timesheet(db, timesheet_id)
    current_status = _status_value(timesheet.status)
    if current_status not in {TimesheetStatus.DRAFT.value, TimesheetStatus.REJECTED.value}:
        raise ValueError("Only draft or rejected timesheets can be updated")

    built_lines, total_hours = _build_line_models(lines, timesheet.period_start, timesheet.period_end)
    timesheet.lines = built_lines
    timesheet.total_hours = total_hours

    status_from = timesheet.status
    status_to = timesheet.status
    if current_status == TimesheetStatus.REJECTED.value:
        timesheet.status = TimesheetStatus.DRAFT
        timesheet.rejected_at = None
        status_to = TimesheetStatus.DRAFT

    _add_audit_event(
        db,
        timesheet=timesheet,
        action="update",
        actor_user_id=actor_user_id,
        status_from=status_from,
        status_to=status_to,
    )
    db.commit()
    db.refresh(timesheet)
    return timesheet


def submit_timesheet(db: Session, *, timesheet_id: int, actor_user_id: int | None = None) -> Timesheet:
    timesheet = _get_timesheet(db, timesheet_id)
    current_status = _status_value(timesheet.status)
    if current_status not in {TimesheetStatus.DRAFT.value, TimesheetStatus.REJECTED.value}:
        raise ValueError("Only draft or rejected timesheets can be submitted")
    status_from = timesheet.status
    timesheet.status = TimesheetStatus.SUBMITTED
    timesheet.submitted_at = _utcnow()
    _add_audit_event(
        db,
        timesheet=timesheet,
        action="submit",
        actor_user_id=actor_user_id,
        status_from=status_from,
        status_to=TimesheetStatus.SUBMITTED,
    )
    db.commit()
    db.refresh(timesheet)
    return timesheet


def approve_timesheet(db: Session, *, timesheet_id: int, actor_user_id: int | None = None) -> Timesheet:
    timesheet = _get_timesheet(db, timesheet_id)
    if _status_value(timesheet.status) != TimesheetStatus.SUBMITTED.value:
        raise ValueError("Only submitted timesheets can be approved")
    status_from = timesheet.status
    timesheet.status = TimesheetStatus.APPROVED
    timesheet.approved_at = _utcnow()
    _add_audit_event(
        db,
        timesheet=timesheet,
        action="approve",
        actor_user_id=actor_user_id,
        status_from=status_from,
        status_to=TimesheetStatus.APPROVED,
    )
    db.commit()
    db.refresh(timesheet)
    return timesheet


def reject_timesheet(
    db: Session,
    *,
    timesheet_id: int,
    reason: str | None,
    actor_user_id: int | None = None,
) -> Timesheet:
    timesheet = _get_timesheet(db, timesheet_id)
    if _status_value(timesheet.status) != TimesheetStatus.SUBMITTED.value:
        raise ValueError("Only submitted timesheets can be rejected")
    clean_reason = str(reason or "").strip()
    if not clean_reason:
        raise ValueError("A rejection reason is required")
    status_from = timesheet.status
    timesheet.status = TimesheetStatus.REJECTED
    timesheet.rejected_at = _utcnow()
    _add_audit_event(
        db,
        timesheet=timesheet,
        action="reject",
        actor_user_id=actor_user_id,
        status_from=status_from,
        status_to=TimesheetStatus.REJECTED,
        reason=clean_reason,
    )
    db.commit()
    db.refresh(timesheet)
    return timesheet


def lock_timesheet(db: Session, *, timesheet_id: int, actor_user_id: int | None = None) -> Timesheet:
    timesheet = _get_timesheet(db, timesheet_id)
    if _status_value(timesheet.status) != TimesheetStatus.APPROVED.value:
        raise ValueError("Only approved timesheets can be locked")
    status_from = timesheet.status
    timesheet.status = TimesheetStatus.LOCKED
    timesheet.locked_at = _utcnow()
    _add_audit_event(
        db,
        timesheet=timesheet,
        action="lock",
        actor_user_id=actor_user_id,
        status_from=status_from,
        status_to=TimesheetStatus.LOCKED,
    )
    db.commit()
    db.refresh(timesheet)
    return timesheet
