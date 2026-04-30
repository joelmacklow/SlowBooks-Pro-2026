from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db, get_master_db
from app.schemas.employee_portal import EmployeePortalLinkCreateRequest, EmployeePortalLinkResponse
from app.services.auth import require_permissions
from app.services.employee_portal import (
    create_employee_link,
    deactivate_employee_link,
    list_employee_links,
    resolve_employee_link,
)

router = APIRouter(prefix="/api/employee-portal", tags=["employee-portal"])


@router.get("/links", response_model=list[EmployeePortalLinkResponse])
def list_links(
    db: Session = Depends(get_db),
    master_db: Session = Depends(get_master_db),
    auth=Depends(require_permissions("users.manage")),
):
    return list_employee_links(master_db, db, auth.membership.company_scope)


@router.post("/links", response_model=EmployeePortalLinkResponse, status_code=201)
def create_link(
    data: EmployeePortalLinkCreateRequest,
    db: Session = Depends(get_db),
    master_db: Session = Depends(get_master_db),
    auth=Depends(require_permissions("users.manage")),
):
    return create_employee_link(master_db, db, auth, data)


@router.post("/links/{link_id}/deactivate", response_model=EmployeePortalLinkResponse)
def deactivate_link(
    link_id: int,
    db: Session = Depends(get_db),
    master_db: Session = Depends(get_master_db),
    auth=Depends(require_permissions("users.manage")),
):
    return deactivate_employee_link(master_db, db, auth, link_id)


@router.get("/self", response_model=EmployeePortalLinkResponse)
def get_self(
    db: Session = Depends(get_db),
    master_db: Session = Depends(get_master_db),
    auth=Depends(require_permissions("timesheets.self.view")),
):
    return resolve_employee_link(master_db, db, auth)
