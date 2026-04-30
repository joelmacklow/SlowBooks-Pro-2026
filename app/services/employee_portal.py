from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.auth import EmployeePortalLink, User, UserMembership
from app.models.payroll import Employee
from app.schemas.employee_portal import (
    EmployeePortalEmployeeSummary,
    EmployeePortalLinkCreateRequest,
    EmployeePortalLinkResponse,
    EmployeePortalUserSummary,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _employee_summary(employee: Employee) -> EmployeePortalEmployeeSummary:
    return EmployeePortalEmployeeSummary(
        id=employee.id,
        first_name=employee.first_name,
        last_name=employee.last_name,
        is_active=bool(employee.is_active),
    )


def _user_summary(user: User) -> EmployeePortalUserSummary:
    return EmployeePortalUserSummary(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=bool(user.is_active),
    )


def _load_user(master_db: Session, user_id: int) -> User:
    user = master_db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User is inactive")
    return user


def _load_active_membership(master_db: Session, user: User, company_scope: str) -> UserMembership:
    membership = (
        master_db.query(UserMembership)
        .filter(
            UserMembership.user_id == user.id,
            UserMembership.company_scope == company_scope,
            UserMembership.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="User does not have an active membership for this company")
    return membership


def _load_employee(company_db: Session, employee_id: int) -> Employee:
    employee = (
        company_db.query(Employee)
        .filter(
            Employee.id == employee_id,
            Employee.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


def _link_response(master_db: Session, company_db: Session, link: EmployeePortalLink) -> EmployeePortalLinkResponse:
    user = link.user or _load_user(master_db, link.user_id)
    employee = _load_employee(company_db, link.employee_id)
    return EmployeePortalLinkResponse(
        id=link.id,
        user=_user_summary(user),
        employee=_employee_summary(employee),
        company_scope=link.company_scope,
        is_active=bool(link.is_active),
        created_by_user_id=link.created_by_user_id,
        deactivated_by_user_id=link.deactivated_by_user_id,
        deactivated_at=link.deactivated_at,
        created_at=link.created_at,
        updated_at=link.updated_at,
    )


def create_employee_link(
    master_db: Session,
    company_db: Session,
    auth_context,
    data: EmployeePortalLinkCreateRequest,
) -> EmployeePortalLinkResponse:
    company_scope = auth_context.membership.company_scope
    user = _load_user(master_db, data.user_id)
    _load_active_membership(master_db, user, company_scope)
    employee = _load_employee(company_db, data.employee_id)

    active_user_link = (
        master_db.query(EmployeePortalLink)
        .filter(
            EmployeePortalLink.user_id == user.id,
            EmployeePortalLink.company_scope == company_scope,
            EmployeePortalLink.is_active == True,  # noqa: E712
        )
        .first()
    )
    if active_user_link:
        raise HTTPException(status_code=400, detail="User already has an active employee link for this company")

    active_employee_link = (
        master_db.query(EmployeePortalLink)
        .filter(
            EmployeePortalLink.company_scope == company_scope,
            EmployeePortalLink.employee_id == employee.id,
            EmployeePortalLink.is_active == True,  # noqa: E712
        )
        .first()
    )
    if active_employee_link:
        raise HTTPException(status_code=400, detail="Employee is already linked for this company")

    link = EmployeePortalLink(
        user_id=user.id,
        company_scope=company_scope,
        employee_id=employee.id,
        is_active=True,
        created_by_user_id=auth_context.user.id,
    )
    master_db.add(link)
    try:
        master_db.commit()
    except IntegrityError as exc:  # pragma: no cover - defensive race protection
        master_db.rollback()
        raise HTTPException(status_code=400, detail="Employee link already exists") from exc
    master_db.refresh(link)
    return _link_response(master_db, company_db, link)


def list_employee_links(master_db: Session, company_db: Session, company_scope: str) -> list[EmployeePortalLinkResponse]:
    links = (
        master_db.query(EmployeePortalLink)
        .filter(
            EmployeePortalLink.company_scope == company_scope,
            EmployeePortalLink.is_active == True,  # noqa: E712
        )
        .order_by(EmployeePortalLink.created_at.desc(), EmployeePortalLink.id.desc())
        .all()
    )
    return [_link_response(master_db, company_db, link) for link in links]


def deactivate_employee_link(
    master_db: Session,
    company_db: Session,
    auth_context,
    link_id: int,
) -> EmployeePortalLinkResponse:
    link = (
        master_db.query(EmployeePortalLink)
        .filter(
            EmployeePortalLink.id == link_id,
            EmployeePortalLink.company_scope == auth_context.membership.company_scope,
            EmployeePortalLink.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="Employee link not found")

    link.is_active = False
    link.deactivated_at = _utcnow()
    link.deactivated_by_user_id = auth_context.user.id
    master_db.commit()
    master_db.refresh(link)
    return _link_response(master_db, company_db, link)


def resolve_employee_link(
    master_db: Session,
    company_db: Session,
    auth_context,
    *,
    required: bool = True,
) -> EmployeePortalLinkResponse | None:
    link = (
        master_db.query(EmployeePortalLink)
        .filter(
            EmployeePortalLink.user_id == auth_context.user.id,
            EmployeePortalLink.company_scope == auth_context.membership.company_scope,
            EmployeePortalLink.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not link:
        if required:
            raise HTTPException(status_code=404, detail="Employee link not found for the active company")
        return None
    return _link_response(master_db, company_db, link)
