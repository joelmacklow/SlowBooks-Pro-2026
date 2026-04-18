# ============================================================================
# Backup/Restore Service — pg_dump/pg_restore subprocess wrapper
# Feature 11: Database backup and restore accessible from settings
# ============================================================================

import os
import re
import stat
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sqlalchemy.orm import Session

from app.config import DATABASE_URL
from app.models.backups import Backup

BACKUP_DIR = Path(__file__).parent.parent.parent / "backups"
BACKUP_FILENAME_PATTERN = re.compile(r"slowbooks_\d{8}_\d{6}\.sql\Z")


def ensure_backup_dir_permissions() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        current_mode = stat.S_IMODE(BACKUP_DIR.stat().st_mode)
        if current_mode != 0o700:
            BACKUP_DIR.chmod(0o700)
    return BACKUP_DIR


def _validated_backup_filename(filename: str) -> str:
    if not isinstance(filename, str):
        raise ValueError("Invalid backup filename")

    candidate = filename.strip()
    if candidate != filename or not candidate:
        raise ValueError("Invalid backup filename")
    if Path(candidate).is_absolute() or "/" in candidate or "\\" in candidate:
        raise ValueError("Invalid backup filename")
    if not BACKUP_FILENAME_PATTERN.fullmatch(candidate):
        raise ValueError("Invalid backup filename")
    return candidate


def _parse_db_url(url: str) -> dict:
    """Parse PostgreSQL connection URL into components."""
    # postgresql://user:pass@host:port/dbname
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "user": parsed.username or "bookkeeper",
        "password": parsed.password or "",
        "dbname": parsed.path.lstrip("/") or "bookkeeper",
        "sslmode": (query.get("sslmode") or [""])[0],
    }


def resolve_backup_path(filename: str) -> Path:
    """Resolve an existing managed backup filename to a path inside the backup directory."""
    candidate = _validated_backup_filename(filename)
    backup_root = ensure_backup_dir_permissions()
    for entry in backup_root.iterdir():
        if entry.is_file() and entry.name == candidate:
            return entry
    raise FileNotFoundError(candidate)


def backup_output_path(filename: str) -> Path:
    """Build the managed output path for an internally generated backup filename."""
    return ensure_backup_dir_permissions() / _validated_backup_filename(filename)


def ensure_backup_file_permissions(filename: str) -> Path:
    filepath = resolve_backup_path(filename)
    if os.name == "posix":
        current_mode = stat.S_IMODE(filepath.stat().st_mode)
        if current_mode != 0o600:
            filepath.chmod(0o600)
    return filepath


def create_backup(db: Session, notes: str = None, backup_type: str = "manual") -> dict:
    """Create a database backup using pg_dump."""
    params = _parse_db_url(DATABASE_URL)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"slowbooks_{timestamp}.sql"
    filepath = backup_output_path(filename)

    env = {"PGPASSWORD": params["password"]}
    if params["sslmode"]:
        env["PGSSLMODE"] = params["sslmode"]

    try:
        result = subprocess.run(
            ["pg_dump", "-h", params["host"], "-p", params["port"],
             "-U", params["user"], "-F", "c", "-f", str(filepath), params["dbname"]],
            env={**dict(__import__("os").environ), **env},
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            return {"success": False, "error": result.stderr, "public_error": "Backup failed"}

        ensure_backup_file_permissions(filename)
        file_size = filepath.stat().st_size

        backup = Backup(
            filename=filename, file_size=file_size,
            backup_type=backup_type, notes=notes,
        )
        db.add(backup)
        db.commit()

        return {"success": True, "filename": filename, "file_size": file_size}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Backup timed out", "public_error": "Backup timed out"}
    except FileNotFoundError:
        return {
            "success": False,
            "error": "pg_dump not found. Is PostgreSQL client installed?",
            "public_error": "Backup tooling is unavailable",
        }


def restore_backup(db: Session, filename: str) -> dict:
    """Restore a database from a backup file."""
    try:
        filepath = resolve_backup_path(filename)
    except ValueError as exc:
        return {"success": False, "error": str(exc), "public_error": "Invalid backup filename", "status_code": 400}
    except FileNotFoundError:
        return {"success": False, "error": "Backup file not found", "public_error": "Backup file not found", "status_code": 404}

    ensure_backup_file_permissions(filepath.name)

    params = _parse_db_url(DATABASE_URL)
    env = {"PGPASSWORD": params["password"]}
    if params["sslmode"]:
        env["PGSSLMODE"] = params["sslmode"]

    try:
        result = subprocess.run(
            ["pg_restore", "-h", params["host"], "-p", params["port"],
             "-U", params["user"], "-d", params["dbname"], "--clean", "--if-exists",
             str(filepath)],
            env={**dict(__import__("os").environ), **env},
            capture_output=True, text=True, timeout=300,
        )
        # pg_restore may return non-zero even on partial success
        if result.returncode != 0 and "error" in result.stderr.lower():
            return {"success": False, "error": result.stderr[:500], "public_error": "Restore failed"}

        return {"success": True, "message": f"Restored from {filename}"}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Restore timed out", "public_error": "Restore timed out"}
    except FileNotFoundError:
        return {"success": False, "error": "pg_restore not found", "public_error": "Restore tooling is unavailable"}


def list_backup_files() -> list[dict]:
    """List all backup files in the backup directory."""
    files = []
    ensure_backup_dir_permissions()
    for f in sorted(BACKUP_DIR.glob("slowbooks_*.sql"), reverse=True):
        ensure_backup_file_permissions(f.name)
        files.append({
            "filename": f.name,
            "file_size": f.stat().st_size,
            "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })
    return files
