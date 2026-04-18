from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.database import get_db
from app.schemas.xero_import import XeroImportDryRunResponse, XeroImportExecuteResponse
from app.services.auth import require_permissions
from app.services.chart_setup_status import CHART_SETUP_SOURCE_XERO_IMPORT, mark_chart_setup_ready
from app.services.rate_limit import enforce_rate_limit
from app.services.xero_import import detect_file_type, dry_run_import, execute_import
from app.services.upload_limits import (
    IMPORT_FILE_MAX_BYTES,
    XERO_IMPORT_TOTAL_MAX_BYTES,
    enforce_upload_size,
)

router = APIRouter(prefix="/api/xero-import", tags=["xero_import"])


def _load_files(files: list[UploadFile]) -> dict[str, tuple[str, str]]:
    file_map = {}
    total_bytes = 0
    for file in files:
        file_type = detect_file_type(file.filename or '')
        if not file_type:
            continue
        content_bytes = enforce_upload_size(
            file.file.read(),
            max_bytes=IMPORT_FILE_MAX_BYTES,
            detail="Xero import file is too large",
        )
        total_bytes += len(content_bytes)
        if total_bytes > XERO_IMPORT_TOTAL_MAX_BYTES:
            raise HTTPException(status_code=413, detail="Xero import bundle is too large")
        try:
            text = content_bytes.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = content_bytes.decode('cp1252', errors='replace')
        file_map[file_type] = (file.filename, text)
    return file_map


@router.post('/dry-run', response_model=XeroImportDryRunResponse)
async def dry_run_xero_import(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions('accounts.manage')),
    request: Request = None,
):
    enforce_rate_limit(
        request,
        scope="import:xero",
        limit=10,
        window_seconds=60,
        detail="Too many Xero import requests. Please wait and try again.",
    )
    return dry_run_import(_load_files(files))


@router.post('/import', response_model=XeroImportExecuteResponse)
async def import_xero_bundle(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions('accounts.manage')),
    request: Request = None,
):
    enforce_rate_limit(
        request,
        scope="import:xero",
        limit=10,
        window_seconds=60,
        detail="Too many Xero import requests. Please wait and try again.",
    )
    result = execute_import(db, _load_files(files))
    mark_chart_setup_ready(db, CHART_SETUP_SOURCE_XERO_IMPORT)
    db.commit()
    return result
