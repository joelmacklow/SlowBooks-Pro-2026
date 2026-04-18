from fastapi import HTTPException

LOGO_UPLOAD_MAX_BYTES = 1 * 1024 * 1024
IMPORT_FILE_MAX_BYTES = 2 * 1024 * 1024
XERO_IMPORT_TOTAL_MAX_BYTES = 8 * 1024 * 1024


def enforce_upload_size(content: bytes, *, max_bytes: int, detail: str) -> bytes:
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=detail)
    return content
