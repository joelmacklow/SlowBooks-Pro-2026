# ============================================================================
# Multi-Company Routes — create and list company databases
# Feature 16: Company switching from UI
# ============================================================================

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_master_db
from app.services.auth import require_permissions
from app.services.company_service import (
    create_company,
    default_company_entry,
    list_companies,
    update_company_metadata,
    upsert_default_company_metadata,
)

router = APIRouter(prefix="/api/companies", tags=["companies"])


class CompanyCreate(BaseModel):
    name: str
    database_name: str
    description: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    org_lock_date: Optional[date] = None


@router.get("")
def get_companies(
    db: Session = Depends(get_master_db),
    auth=Depends(require_permissions("companies.view")),
):
    companies = list_companies(db)
    default_company = default_company_entry(db)
    for company in companies:
        if company.get("database_name") == default_company["database_name"]:
            company["is_default"] = True
            return companies
    return [default_company, *companies]


@router.post("", status_code=201)
def new_company(
    data: CompanyCreate,
    db: Session = Depends(get_master_db),
    auth=Depends(require_permissions("companies.manage")),
):
    result = create_company(db, data.name, data.database_name, data.description)
    if not result.get("success"):
        raise HTTPException(
            status_code=result.get("status_code", 400),
            detail=result.get("public_error", "Failed to create company"),
        )
    return {
        "success": True,
        "company_id": result.get("company_id"),
        "database_name": result.get("database_name"),
    }


@router.put("/default")
def update_default_company(
    data: CompanyUpdate,
    db: Session = Depends(get_master_db),
    auth=Depends(require_permissions("companies.manage")),
):
    return upsert_default_company_metadata(
        db,
        name=data.name,
        description=data.description,
        org_lock_date=data.org_lock_date,
    )


@router.put("/{company_id}")
def update_company(
    company_id: int,
    data: CompanyUpdate,
    db: Session = Depends(get_master_db),
    auth=Depends(require_permissions("companies.manage")),
):
    try:
        return update_company_metadata(
            db,
            company_id,
            name=data.name,
            description=data.description,
            org_lock_date=data.org_lock_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
