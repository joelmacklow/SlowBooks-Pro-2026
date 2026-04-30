# ============================================================================
# File Uploads — company logo and other file uploads
# Feature 15: Infrastructure D (UploadFile pattern, static/uploads/)
# ============================================================================

import base64
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.database import get_db
from app.config import UPLOADS_DIR
from app.models.settings import Settings
from app.services.auth import require_permissions
from app.services.rate_limit import enforce_rate_limit
from app.services.upload_limits import LOGO_UPLOAD_MAX_BYTES, enforce_upload_size

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

UPLOAD_DIR = Path(UPLOADS_DIR)

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif"}


def _detect_logo_image(content: bytes) -> tuple[str, str]:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png", "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "jpg", "image/jpeg"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "gif", "image/gif"
    raise HTTPException(status_code=400, detail="Uploaded logo content is not a supported image type")


def _logo_data_uri(content: bytes, content_type: str) -> str:
    encoded = base64.b64encode(content).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def ensure_upload_dir() -> Path:
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        raise HTTPException(status_code=500, detail="Upload storage is not writable") from exc
    return UPLOAD_DIR


@router.post("/logo")
async def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("settings.manage")),
    request: Request = None,
):
    enforce_rate_limit(
        request,
        scope="upload:logo",
        limit=10,
        window_seconds=60,
        detail="Too many logo upload requests. Please wait and try again.",
    )
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only PNG, JPG/JPEG, or GIF images are allowed")

    content = enforce_upload_size(
        await file.read(),
        max_bytes=LOGO_UPLOAD_MAX_BYTES,
        detail="Logo image is too large",
    )
    ext, detected_content_type = _detect_logo_image(content)
    if file.content_type and file.content_type != detected_content_type:
        raise HTTPException(status_code=400, detail="Uploaded logo content does not match its declared image type")

    filename = f"company_logo.{ext}"
    filepath = ensure_upload_dir() / filename
    logo_path = f"/static/uploads/{filename}"
    logo_data_uri = _logo_data_uri(content, detected_content_type)

    try:
        with open(filepath, "wb") as f:
            f.write(content)
    except PermissionError as exc:
        raise HTTPException(status_code=500, detail="Upload storage is not writable") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Upload storage is not writable") from exc

    row = db.query(Settings).filter(Settings.key == "company_logo_path").first()
    if row:
        row.value = logo_path
    else:
        db.add(Settings(key="company_logo_path", value=logo_path))
    data_row = db.query(Settings).filter(Settings.key == "company_logo_data_uri").first()
    if data_row:
        data_row.value = logo_data_uri
    else:
        db.add(Settings(key="company_logo_data_uri", value=logo_data_uri))
    db.commit()

    return {"path": logo_path, "message": "Logo uploaded successfully"}
