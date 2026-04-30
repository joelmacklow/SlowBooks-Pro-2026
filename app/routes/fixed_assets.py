from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.database import get_db
from app.services.auth import require_permissions
from app.services.fixed_assets import (
    asset_payload,
    create_asset,
    create_asset_type,
    csv_template_text,
    dispose_asset,
    fixed_asset_reconciliation,
    import_assets_from_csv,
    list_asset_types_payload,
    list_assets_payload,
    run_depreciation,
    update_asset,
    update_asset_type,
)
from app.services.rate_limit import enforce_rate_limit
from app.services.upload_limits import IMPORT_FILE_MAX_BYTES, enforce_upload_size

router = APIRouter(prefix="/api/fixed-assets", tags=["fixed_assets"])


async def _read_csv_upload(file: UploadFile) -> str:
    try:
        content = enforce_upload_size(
            await file.read(),
            max_bytes=IMPORT_FILE_MAX_BYTES,
            detail="CSV file is too large",
        )
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV file must be UTF-8 encoded") from exc


@router.get("/types")
def list_asset_types(
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    return list_asset_types_payload(db)


@router.post("/types")
def create_fixed_asset_type(
    data: dict,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    return create_asset_type(db, data)


@router.put("/types/{asset_type_id}")
def update_fixed_asset_type(
    asset_type_id: int,
    data: dict,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    return update_asset_type(db, asset_type_id, data)


@router.get("")
def list_fixed_assets(
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    return list_assets_payload(db, status=status)


@router.get("/import-template")
def download_import_template(
    auth=Depends(require_permissions("import_export.view")),
):
    return Response(
        content=csv_template_text(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=fixed_assets_import_template.csv"},
    )


@router.post("/import")
async def import_fixed_assets(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("import_export.manage")),
    request: Request = None,
):
    enforce_rate_limit(
        request,
        scope="import:fixed-assets",
        limit=10,
        window_seconds=60,
        detail="Too many fixed asset import requests. Please wait and try again.",
    )
    content = await _read_csv_upload(file)
    return import_assets_from_csv(db, content)


@router.get("/reconciliation-report")
def get_fixed_asset_reconciliation(
    as_of_date: date | None = None,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    return fixed_asset_reconciliation(db, as_of_date or date.today())


@router.post("")
def create_fixed_asset(
    data: dict,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    return create_asset(db, data)


@router.get("/{asset_id}")
def get_fixed_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    from app.models.fixed_assets import FixedAsset

    asset = db.query(FixedAsset).filter(FixedAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Fixed asset not found")
    return asset_payload(db, asset)


@router.put("/{asset_id}")
def update_fixed_asset(
    asset_id: int,
    data: dict,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    return update_asset(db, asset_id, data)


@router.post("/{asset_id}/dispose")
def dispose_fixed_asset(
    asset_id: int,
    data: dict,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    return dispose_asset(db, asset_id, data)


@router.post("/depreciation/run")
def run_fixed_asset_depreciation(
    run_date: date | None = None,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    return run_depreciation(db, run_date or date.today())
