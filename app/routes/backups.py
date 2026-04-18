# ============================================================================
# Backup/Restore Routes — accessible from settings page
# Feature 11: Create, list, download, restore backups
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.backups import Backup
from app.services.auth import require_permissions
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
):
    result = create_backup(db, notes=data.notes)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Backup failed"))
    return result


@router.get("/download/{filename}")
def download_backup(
    filename: str,
    auth=Depends(require_permissions("backups.view")),
):
    if not BACKUP_FILENAME_PATTERN.fullmatch(filename):
        raise HTTPException(status_code=400, detail="Invalid backup filename")

    try:
        filepath = resolve_backup_path(filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")
    ensure_backup_file_permissions(filepath)
    return FileResponse(str(filepath), filename=filepath.name, media_type="application/octet-stream")


@router.post("/restore")
def restore(
    data: RestoreRequest,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("backups.manage")),
):
    result = restore_backup(db, data.filename)
    if not result.get("success"):
        raise HTTPException(
            status_code=result.get("status_code", 500),
            detail=result.get("error", "Restore failed"),
        )
    return result
