# ============================================================================
# Backup/Restore Routes — accessible from settings page
# Feature 11: Create, list, download, restore backups
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from starlette.requests import Request

from app.database import get_db
from app.models.backups import Backup
from app.services.auth import require_permissions
from app.services.audit import log_event
from app.services.rate_limit import enforce_rate_limit
from app.services.backup_service import (
    BACKUP_FILENAME_PATTERN,
    create_backup,
    ensure_backup_file_permissions,
    resolve_backup_path,
    restore_backup,
)

router = APIRouter(prefix="/api/backups", tags=["backups"])


class BackupCreate(BaseModel):
    notes: Optional[str] = None


class RestoreRequest(BaseModel):
    filename: str


def _actor_user_id(auth) -> int | None:
    if isinstance(auth, dict):
        value = auth.get("user_id")
        return value if isinstance(value, int) else None
    value = getattr(auth, "user_id", None)
    return value if isinstance(value, int) else None


def _log_backup_audit_event(db: Session, *, filename: str, action: str, auth) -> None:
    backup = db.query(Backup).filter(Backup.filename == filename).order_by(Backup.id.desc()).first()
    log_event(
        db,
        table_name="backups",
        record_id=backup.id if backup else 0,
        action=action,
        new_values={
            "filename": filename,
            "actor_user_id": _actor_user_id(auth),
        },
        changed_fields=["filename", "actor_user_id"],
        source="api",
    )
    db.commit()


@router.get("")
def list_backups(
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("backups.view")),
):
    """List only backups whose files still exist on disk."""
    db_backups = db.query(Backup).order_by(Backup.created_at.desc()).all()
    visible_backups = []
    for backup in db_backups:
        try:
            filepath = resolve_backup_path(backup.filename)
        except ValueError:
            continue
        if filepath.exists():
            ensure_backup_file_permissions(filepath)
            visible_backups.append({
                "id": backup.id,
                "filename": backup.filename,
                "file_size": backup.file_size,
                "backup_type": backup.backup_type,
                "notes": backup.notes,
                "created_at": backup.created_at.isoformat() if backup.created_at else None,
            })
    return visible_backups


@router.post("")
def make_backup(
    data: BackupCreate = BackupCreate(),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("backups.manage")),
    request: Request = None,
):
    enforce_rate_limit(
        request,
        scope="backup:create",
        limit=3,
        window_seconds=300,
        detail="Too many backup creation requests. Please wait and try again.",
    )
    result = create_backup(db, notes=data.notes)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Backup failed"))
    _log_backup_audit_event(db, filename=result["filename"], action="CREATE", auth=auth)
    return result


@router.get("/download/{filename}")
def download_backup(
    filename: str,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("backups.view")),
    request: Request = None,
):
    enforce_rate_limit(
        request,
        scope="backup:download",
        limit=10,
        window_seconds=60,
        detail="Too many backup download requests. Please wait and try again.",
    )
    if not BACKUP_FILENAME_PATTERN.fullmatch(filename):
        raise HTTPException(status_code=400, detail="Invalid backup filename")

    try:
        filepath = resolve_backup_path(filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")
    ensure_backup_file_permissions(filepath)
    _log_backup_audit_event(db, filename=filepath.name, action="DOWNLOAD", auth=auth)
    return FileResponse(
        str(filepath),
        filename=filepath.name,
        media_type="application/octet-stream",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/restore")
def restore(
    data: RestoreRequest,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("backups.manage")),
    request: Request = None,
):
    enforce_rate_limit(
        request,
        scope="backup:restore",
        limit=3,
        window_seconds=300,
        detail="Too many backup restore requests. Please wait and try again.",
    )
    result = restore_backup(db, data.filename)
    if not result.get("success"):
        raise HTTPException(
            status_code=result.get("status_code", 500),
            detail=result.get("error", "Restore failed"),
        )
    _log_backup_audit_event(db, filename=data.filename, action="RESTORE", auth=auth)
    return result
