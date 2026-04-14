# ============================================================================
# Multi-Company Routes — create and list company databases
# Feature 16: Company switching from UI
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.services.company_service import list_companies, create_company
from app.services.auth import require_permissions

router = APIRouter(prefix="/api/companies", tags=["companies"])


class CompanyCreate(BaseModel):
    name: str
    database_name: str
    description: Optional[str] = None


@router.get("")
def get_companies(
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("companies.view")),
):
    return list_companies(db)


@router.post("", status_code=201)
def new_company(
    data: CompanyCreate,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("companies.manage")),
):
    result = create_company(db, data.name, data.database_name, data.description)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create company"))
    return result
