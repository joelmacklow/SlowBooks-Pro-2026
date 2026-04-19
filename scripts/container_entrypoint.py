#!/usr/bin/env python3
"""Container entrypoint for the web app and reminder scheduler services."""
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

from sqlalchemy import create_engine, text

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("APP_ROOT", str(REPO_ROOT))
existing_pythonpath = os.environ.get("PYTHONPATH", "").strip()
pythonpath_parts = [str(REPO_ROOT)]
if existing_pythonpath:
    pythonpath_parts.append(existing_pythonpath)
os.environ["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

from app.config import DATABASE_URL  # noqa: E402
from scripts.bootstrap_database import run_bootstrap  # noqa: E402


def is_scheduler_mode() -> bool:
    return os.environ.get("RUN_INVOICE_REMINDER_SCHEDULER", "false").lower() == "true"


def ensure_runtime_dirs() -> None:
    (REPO_ROOT / "backups").mkdir(parents=True, exist_ok=True)
    (REPO_ROOT / "app" / "static" / "uploads").mkdir(parents=True, exist_ok=True)


def ensure_bootstrap_token() -> None:
    if os.environ.get("BOOTSTRAP_ADMIN_TOKEN", "").strip():
        return
    os.environ["BOOTSTRAP_ADMIN_TOKEN"] = secrets.token_urlsafe(24)
    print("BOOTSTRAP_ADMIN_TOKEN was not set; generated a startup token for first-admin setup.")


def bootstrap_setup_url() -> str:
    port = os.environ.get("APP_PORT", "3001").strip() or "3001"
    token = os.environ.get("BOOTSTRAP_ADMIN_TOKEN", "")
    return f"http://localhost:{port}/#/login?bootstrap_token={quote(token, safe='')}"


def print_startup_banner() -> None:
    if is_scheduler_mode():
        print("Starting invoice reminder scheduler service.")
        return

    ensure_bootstrap_token()
    print(f"Bootstrap admin token: {os.environ['BOOTSTRAP_ADMIN_TOKEN']}")
    print(f"Bootstrap admin setup URL: {bootstrap_setup_url()}")
    print("If accessing SlowBooks remotely, replace localhost with your Docker host name or IP before opening the URL.")


def wait_for_database(max_attempts: int = 60, sleep_seconds: int = 2) -> None:
    last_error = None
    for attempt in range(max_attempts):
        try:
            engine = create_engine(DATABASE_URL, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"Database ready: {DATABASE_URL}")
            return
        except Exception as exc:  # pragma: no cover - exercised in containers
            last_error = exc
            print(f"Waiting for database (attempt {attempt + 1}/{max_attempts}): {exc}")
            time.sleep(sleep_seconds)
    raise SystemExit(f"Database not reachable after waiting: {last_error}")


def exec_target() -> None:
    if is_scheduler_mode():
        os.execvp(sys.executable, [sys.executable, "scripts/run_invoice_reminder_scheduler.py"])
    os.execvp(sys.executable, [sys.executable, "run.py"])


def main() -> None:
    os.chdir(REPO_ROOT)
    ensure_runtime_dirs()
    print_startup_banner()
    wait_for_database()
    run_bootstrap()
    exec_target()


if __name__ == "__main__":
    main()
