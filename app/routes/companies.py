# ============================================================================
# Multi-Company Routes — create and list company databases
# Feature 16: Company switching from UI
# ============================================================================

from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import DATABASE_URL
from app.database import get_db
from app.routes.settings import _get_all as get_settings
from app.services.auth import require_permissions
from app.services.company_service import create_company, list_companies

router = APIRouter(prefix="/api/companies", tags=["companies"])


class CompanyCreate(BaseModel):
    name: str
    database_name: str
    description: Optional[str] = None


def _current_database_name(db: Session) -> str:
    try:
        bind = db.get_bind()
        database_name = getattr(getattr(bind, "url", None), "database", None)
        if database_name:
            return str(database_name)
    except Exception:
        pass
    return urlparse(DATABASE_URL).path.lstrip("/") or "bookkeeper"


def _default_company_entry(db: Session) -> dict:
    settings = get_settings(db)
    return {
        "id": None,
        "name": settings.get("company_name") or "My Company",
        "database_name": _current_database_name(db),
        "description": "Default company",
        "last_accessed": None,
        "is_default": True,
    }


@router.get("")
def get_companies(
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("companies.view")),
):
    companies = list_companies(db)
    default_company = _default_company_entry(db)
    for company in companies:
        if company.get("database_name") == default_company["database_name"]:
            company["is_default"] = True
            return companies
    return [default_company, *companies]


@router.post("", status_code=201)
def new_company(
    data: CompanyCreate,
    db: Session = Depends(get_db),
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
