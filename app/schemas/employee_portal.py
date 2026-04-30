from datetime import datetime

from pydantic import BaseModel


class EmployeePortalUserSummary(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool

    model_config = {"from_attributes": True}


class EmployeePortalEmployeeSummary(BaseModel):
    id: int
    first_name: str
    last_name: str
    is_active: bool

    model_config = {"from_attributes": True}


class EmployeePortalLinkCreateRequest(BaseModel):
    user_id: int
    employee_id: int


class EmployeePortalLinkResponse(BaseModel):
    id: int
    user: EmployeePortalUserSummary
    employee: EmployeePortalEmployeeSummary
    company_scope: str
    is_active: bool
    created_by_user_id: int | None = None
    deactivated_by_user_id: int | None = None
    deactivated_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
