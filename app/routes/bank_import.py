from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth import require_permissions
from app.services.ofx_import import import_transactions, parse_statement_file

router = APIRouter(prefix="/api/bank-import", tags=["bank_import"])


@router.post("/preview")
async def preview_statement(
    file: UploadFile = File(...),
    auth=Depends(require_permissions("banking.manage")),
):
    content = await file.read()
    try:
        parsed = parse_statement_file(content, filename=file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"transactions": parsed["transactions"], "account_id": None, "format": parsed["format"]}


@router.post("/import/{bank_account_id}")
async def import_statement(
    bank_account_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("banking.manage")),
):
    content = await file.read()
    try:
        parsed = parse_statement_file(content, filename=file.filename)
        result = import_transactions(db, bank_account_id, parsed["transactions"], import_source=parsed["format"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "format": parsed["format"],
        "imported": result["imported"],
        "skipped_duplicates": result["skipped"],
        "total": result["total"],
    }
