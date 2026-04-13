# ============================================================================
# Employees — CRUD for employee records
# Feature 17: Payroll basics — employee management
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.payroll import Employee
from app.schemas.payroll import EmployeeCreate, EmployeeUpdate, EmployeeResponse
from app.routes.settings import _get_all as get_settings
from app.services.employee_filing import generate_employee_filing_csv

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeResponse])
def list_employees(active_only: bool = False, db: Session = Depends(get_db)):
    q = db.query(Employee)
    if active_only:
        q = q.filter(Employee.is_active == True)
    return q.order_by(Employee.last_name, Employee.first_name).all()


@router.get("/{emp_id}", response_model=EmployeeResponse)
def get_employee(emp_id: int, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


@router.post("", response_model=EmployeeResponse, status_code=201)
def create_employee(data: EmployeeCreate, db: Session = Depends(get_db)):
    emp = Employee(**data.model_dump())
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


@router.put("/{emp_id}", response_model=EmployeeResponse)
def update_employee(emp_id: int, data: EmployeeUpdate, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(emp, key, val)
    db.commit()
    db.refresh(emp)
    return emp


@router.get("/{emp_id}/filing/starter/export")
def export_starter_employee_filing(emp_id: int, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    try:
        content = generate_employee_filing_csv(emp, "starter", get_settings(db))
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="StarterEmployee_{emp_id}.csv"'},
    )


@router.get("/{emp_id}/filing/leaver/export")
def export_leaver_employee_filing(emp_id: int, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    try:
        content = generate_employee_filing_csv(emp, "leaver", get_settings(db))
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="LeaverEmployee_{emp_id}.csv"'},
    )
