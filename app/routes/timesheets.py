from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.models.auth import User
from app.database import get_db, get_master_db
from app.models.timesheets import Timesheet
from app.models.payroll import PayRun
from app.schemas.timesheets import (
    TimesheetAuditEventResponse,
    TimesheetBulkApproveRequest,
    TimesheetCorrectionRequest,
    TimesheetDetailResponse,
    TimesheetListResponse,
    TimesheetReadinessResponse,
    TimesheetSelfCreateRequest,
    TimesheetStatusActionRequest,
    TimesheetUpdateRequest,
)
from app.services.auth import require_permissions
from app.services.employee_portal import resolve_employee_link
from app.services.timesheets import (
    approve_timesheet,
    bulk_approve_timesheets,
    correct_timesheet,
    create_timesheet,
    export_timesheets_csv,
    export_timesheet_csv,
    get_timesheet_audit_events,
    get_timesheet_for_employee,
    group_timesheets_by_status,
    list_timesheets_for_employee,
    list_timesheets_for_period,
    reject_timesheet,
    submit_timesheet,
    update_timesheet,
)

router = APIRouter(prefix="/api/timesheets", tags=["timesheets"])


def _resolved_employee_id(master_db: Session, db: Session, auth) -> int:
    link = resolve_employee_link(master_db, db, auth)
    return link.employee.id


def _detail_response(timesheet) -> TimesheetDetailResponse:
    response = TimesheetDetailResponse.model_validate(timesheet)
    response.employee_name = f"{timesheet.employee.first_name} {timesheet.employee.last_name}".strip()
    response.lines = sorted(response.lines, key=lambda line: (line.work_date, line.id))
    response.audit_events = sorted(response.audit_events, key=lambda event: event.id)
    return response


def _list_response(timesheet) -> TimesheetListResponse:
    response = TimesheetListResponse.model_validate(timesheet)
    response.employee_name = f"{timesheet.employee.first_name} {timesheet.employee.last_name}".strip()
    return response


def _audit_response(event, actor_map: dict[int, User]) -> TimesheetAuditEventResponse:
    response = TimesheetAuditEventResponse.model_validate(event)
    actor = actor_map.get(event.actor_user_id) if event.actor_user_id is not None else None
    if actor is not None:
        response.actor_name = actor.full_name
        response.actor_email = actor.email
    return response


def _readiness_response(*, period_start: date, period_end: date, timesheets, pay_run_id: int | None = None) -> TimesheetReadinessResponse:
    grouped = group_timesheets_by_status(timesheets)
    return TimesheetReadinessResponse(
        period_start=period_start,
        period_end=period_end,
        pay_run_id=pay_run_id,
        draft=[_list_response(row) for row in grouped["draft"]],
        submitted=[_list_response(row) for row in grouped["submitted"]],
        approved=[_list_response(row) for row in grouped["approved"]],
        rejected=[_list_response(row) for row in grouped["rejected"]],
        locked=[_list_response(row) for row in grouped["locked"]],
    )


def _load_timesheet(db: Session, timesheet_id: int):
    timesheet = db.query(Timesheet).filter(Timesheet.id == timesheet_id).first()
    if not timesheet:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    return timesheet


def _load_pay_run(db: Session, pay_run_id: int) -> PayRun:
    pay_run = db.query(PayRun).filter(PayRun.id == pay_run_id).first()
    if not pay_run:
        raise HTTPException(status_code=404, detail="Pay run not found")
    return pay_run


@router.get("/self", response_model=list[TimesheetListResponse])
def list_self_timesheets(
    status: str | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
    db: Session = Depends(get_db),
    master_db: Session = Depends(get_master_db),
    auth=Depends(require_permissions("timesheets.self.view")),
):
    employee_id = _resolved_employee_id(master_db, db, auth)
    try:
        rows = list_timesheets_for_employee(
            db,
            employee_id=employee_id,
            status=status,
            period_start=period_start,
            period_end=period_end,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    return [_list_response(row) for row in rows]


@router.post("/self", response_model=TimesheetDetailResponse, status_code=201)
def create_self_timesheet(
    data: TimesheetSelfCreateRequest,
    db: Session = Depends(get_db),
    master_db: Session = Depends(get_master_db),
    auth=Depends(require_permissions("timesheets.self.create")),
):
    employee_id = _resolved_employee_id(master_db, db, auth)
    try:
        created = create_timesheet(
            db,
            employee_id=employee_id,
            period_start=data.period_start,
            period_end=data.period_end,
            lines=data.lines,
            actor_user_id=auth.user.id,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    return _detail_response(created)


@router.get("/self/{timesheet_id}", response_model=TimesheetDetailResponse)
def get_self_timesheet(
    timesheet_id: int,
    db: Session = Depends(get_db),
    master_db: Session = Depends(get_master_db),
    auth=Depends(require_permissions("timesheets.self.view")),
):
    employee_id = _resolved_employee_id(master_db, db, auth)
    try:
        timesheet = get_timesheet_for_employee(db, timesheet_id=timesheet_id, employee_id=employee_id)
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    return _detail_response(timesheet)


@router.put("/self/{timesheet_id}", response_model=TimesheetDetailResponse)
def update_self_timesheet(
    timesheet_id: int,
    data: TimesheetUpdateRequest,
    db: Session = Depends(get_db),
    master_db: Session = Depends(get_master_db),
    auth=Depends(require_permissions("timesheets.self.create")),
):
    employee_id = _resolved_employee_id(master_db, db, auth)
    try:
        get_timesheet_for_employee(db, timesheet_id=timesheet_id, employee_id=employee_id)
        updated = update_timesheet(
            db,
            timesheet_id=timesheet_id,
            lines=data.lines,
            actor_user_id=auth.user.id,
        )
    except ValueError as err:
        detail = str(err)
        code = 404 if detail == "Timesheet not found" else 400
        raise HTTPException(status_code=code, detail=detail) from err
    return _detail_response(updated)


@router.post("/self/{timesheet_id}/submit", response_model=TimesheetDetailResponse)
def submit_self_timesheet(
    timesheet_id: int,
    db: Session = Depends(get_db),
    master_db: Session = Depends(get_master_db),
    auth=Depends(require_permissions("timesheets.self.submit")),
):
    employee_id = _resolved_employee_id(master_db, db, auth)
    try:
        get_timesheet_for_employee(db, timesheet_id=timesheet_id, employee_id=employee_id)
        submitted = submit_timesheet(db, timesheet_id=timesheet_id, actor_user_id=auth.user.id)
    except ValueError as err:
        detail = str(err)
        code = 404 if detail == "Timesheet not found" else 400
        raise HTTPException(status_code=code, detail=detail) from err
    return _detail_response(submitted)


@router.get("/self/{timesheet_id}/csv")
def export_self_timesheet_csv(
    timesheet_id: int,
    db: Session = Depends(get_db),
    master_db: Session = Depends(get_master_db),
    auth=Depends(require_permissions("timesheets.self.view")),
):
    employee_id = _resolved_employee_id(master_db, db, auth)
    try:
        timesheet = get_timesheet_for_employee(db, timesheet_id=timesheet_id, employee_id=employee_id)
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err

    csv_content = export_timesheet_csv(timesheet)
    filename = f"Timesheet_{timesheet.id}_{timesheet.period_start.isoformat()}_{timesheet.period_end.isoformat()}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/periods", response_model=TimesheetReadinessResponse)
def get_timesheet_period_readiness(
    period_start: date,
    period_end: date,
    status: str | None = None,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("timesheets.manage")),
):
    try:
        timesheets = list_timesheets_for_period(db, period_start=period_start, period_end=period_end, status=status)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    return _readiness_response(period_start=period_start, period_end=period_end, timesheets=timesheets)


@router.get("/pay-runs/{pay_run_id}", response_model=TimesheetReadinessResponse)
def get_timesheet_pay_run_readiness(
    pay_run_id: int,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("timesheets.manage")),
):
    pay_run = _load_pay_run(db, pay_run_id)
    timesheets = list_timesheets_for_period(
        db,
        period_start=pay_run.period_start,
        period_end=pay_run.period_end,
    )
    return _readiness_response(
        period_start=pay_run.period_start,
        period_end=pay_run.period_end,
        timesheets=timesheets,
        pay_run_id=pay_run.id,
    )


@router.get("/{timesheet_id}", response_model=TimesheetDetailResponse)
def get_timesheet(
    timesheet_id: int,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("timesheets.manage")),
):
    timesheet = _load_timesheet(db, timesheet_id)
    return _detail_response(timesheet)


@router.put("/{timesheet_id}", response_model=TimesheetDetailResponse)
def correct_timesheet_route(
    timesheet_id: int,
    data: TimesheetCorrectionRequest,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("timesheets.manage")),
):
    try:
        corrected = correct_timesheet(
            db,
            timesheet_id=timesheet_id,
            lines=data.lines,
            reason=data.reason,
            actor_user_id=auth.user.id,
        )
    except ValueError as err:
        detail = str(err)
        code = 404 if detail == "Timesheet not found" else 400
        raise HTTPException(status_code=code, detail=detail) from err
    return _detail_response(corrected)


@router.post("/{timesheet_id}/approve", response_model=TimesheetDetailResponse)
def approve_timesheet_route(
    timesheet_id: int,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("timesheets.approve")),
):
    try:
        approved = approve_timesheet(db, timesheet_id=timesheet_id, actor_user_id=auth.user.id)
    except ValueError as err:
        detail = str(err)
        code = 404 if detail == "Timesheet not found" else 400
        raise HTTPException(status_code=code, detail=detail) from err
    return _detail_response(approved)


@router.post("/{timesheet_id}/reject", response_model=TimesheetDetailResponse)
def reject_timesheet_route(
    timesheet_id: int,
    data: TimesheetStatusActionRequest,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("timesheets.approve")),
):
    try:
        rejected = reject_timesheet(
            db,
            timesheet_id=timesheet_id,
            reason=data.reason,
            actor_user_id=auth.user.id,
        )
    except ValueError as err:
        detail = str(err)
        code = 404 if detail == "Timesheet not found" else 400
        raise HTTPException(status_code=code, detail=detail) from err
    return _detail_response(rejected)


@router.post("/bulk-approve", response_model=list[TimesheetDetailResponse])
def bulk_approve_timesheets_route(
    data: TimesheetBulkApproveRequest,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("timesheets.approve")),
):
    try:
        approved = bulk_approve_timesheets(db, timesheet_ids=data.timesheet_ids, actor_user_id=auth.user.id)
    except ValueError as err:
        detail = str(err)
        code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=code, detail=detail) from err
    return [_detail_response(timesheet) for timesheet in approved]


@router.get("/{timesheet_id}/audit", response_model=list[TimesheetAuditEventResponse])
def get_timesheet_audit(
    timesheet_id: int,
    db: Session = Depends(get_db),
    master_db: Session = Depends(get_master_db),
    auth=Depends(require_permissions("timesheets.manage")),
):
    try:
        events = get_timesheet_audit_events(db, timesheet_id=timesheet_id)
        actor_ids = {event.actor_user_id for event in events if event.actor_user_id is not None}
        actor_map = {
            user.id: user
            for user in master_db.query(User).filter(User.id.in_(actor_ids)).all()
        } if actor_ids else {}
        return [_audit_response(event, actor_map) for event in events]
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


@router.get("/export")
def export_timesheets_csv_route(
    period_start: date,
    period_end: date,
    status: str | None = None,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("timesheets.export")),
):
    try:
        timesheets = list_timesheets_for_period(db, period_start=period_start, period_end=period_end, status=status)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    csv_content = export_timesheets_csv(timesheets)
    filename_parts = ["Timesheets", period_start.isoformat(), period_end.isoformat()]
    if status:
        filename_parts.append(status.strip().lower())
    filename = "_".join(filename_parts) + ".csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
