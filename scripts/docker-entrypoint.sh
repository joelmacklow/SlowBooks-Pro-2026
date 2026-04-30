#!/bin/sh
set -eu

mkdir -p /app/backups /tmp/slowbooks/uploads 2>/dev/null || true

BOOTSTRAP_SETUP_URL="$(python - <<'PY'
import os

port = os.environ.get("APP_PORT", "3001").strip() or "3001"
print(f"http://localhost:{port}/#/login")
PY
)"

printf '%s %s\n' 'Bootstrap admin setup URL:' "$BOOTSTRAP_SETUP_URL"
printf '%s\n' 'Set BOOTSTRAP_ADMIN_TOKEN in .env before remote first-admin setup; the token is never printed to logs.'
printf '%s\n' 'If accessing SlowBooks remotely, replace localhost with your Docker host name or IP before opening the URL.'

python - <<'PY'
import sys
import time
from sqlalchemy import create_engine, text
from app.config import DATABASE_URL

last_error = None
for attempt in range(60):
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database ready")
        sys.exit(0)
    except Exception as exc:
        last_error = exc
        print(f"Waiting for database (attempt {attempt + 1}/60): {exc}")
        time.sleep(2)

raise SystemExit(f"Database not reachable after waiting: {last_error}")
PY

python scripts/bootstrap_database.py
exec python run.py
