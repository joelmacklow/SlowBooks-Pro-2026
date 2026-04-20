from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.database import get_db
from app.services.auth import require_permissions
from app.services.ofx_import import import_transactions, parse_statement_file, statement_summary
from app.services.rate_limit import enforce_rate_limit
from app.services.upload_limits import IMPORT_FILE_MAX_BYTES, enforce_upload_size

router = APIRouter(prefix="/api/bank-import", tags=["bank_import"])


@router.post("/preview")
async def preview_statement(
    file: UploadFile = File(...),
    auth=Depends(require_permissions("banking.manage")),
    request: Request = None,
):
    enforce_rate_limit(
        request,
        scope="import:bank",
        limit=10,
        window_seconds=60,
        detail="Too many bank import requests. Please wait and try again.",
    )
    content = enforce_upload_size(
        await file.read(),
        max_bytes=IMPORT_FILE_MAX_BYTES,
        detail="Statement file is too large",
    )
    try:
        parsed = parse_statement_file(content, filename=file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    summary = statement_summary(parsed["transactions"])
    return {"transactions": parsed["transactions"], "account_id": None, "format": parsed["format"], **summary}


@router.post("/import/{bank_account_id}")
async def import_statement(
    bank_account_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("banking.manage")),
    request: Request = None,
):
    enforce_rate_limit(
        request,
        scope="import:bank",
        limit=10,
        window_seconds=60,
        detail="Too many bank import requests. Please wait and try again.",
    )
    content = enforce_upload_size(
        await file.read(),
        max_bytes=IMPORT_FILE_MAX_BYTES,
        detail="Statement file is too large",
    )
    try:
        parsed = parse_statement_file(content, filename=file.filename)
        result = import_transactions(db, bank_account_id, parsed["transactions"], import_source=parsed["format"])
        summary = statement_summary(parsed["transactions"], import_batch_id=result.get("import_batch_id"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "format": parsed["format"],
        "imported": result["imported"],
        "skipped_duplicates": result["skipped"],
        "total": result["total"],
        **summary,
    }
