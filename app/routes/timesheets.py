from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db, get_master_db
from app.schemas.timesheets import (
    TimesheetDetailResponse,
    TimesheetListResponse,
    TimesheetSelfCreateRequest,
    TimesheetUpdateRequest,
)
from app.services.auth import require_permissions
from app.services.employee_portal import resolve_employee_link
from app.services.timesheets import (
    create_timesheet,
    export_timesheet_csv,
    get_timesheet_for_employee,
    list_timesheets_for_employee,
    submit_timesheet,
    update_timesheet,
)

router = APIRouter(prefix="/api/timesheets", tags=["timesheets"])


def _resolved_employee_id(master_db: Session, db: Session, auth) -> int:
    link = resolve_employee_link(master_db, db, auth)
    return link.employee.id


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
    return [TimesheetListResponse.model_validate(row) for row in rows]


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
    return TimesheetDetailResponse.model_validate(created)


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
    return TimesheetDetailResponse.model_validate(timesheet)


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
    return TimesheetDetailResponse.model_validate(updated)


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
    return TimesheetDetailResponse.model_validate(submitted)


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
