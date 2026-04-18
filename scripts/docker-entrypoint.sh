#!/bin/sh
set -eu

mkdir -p /app/backups /app/app/static/uploads 2>/dev/null || true

if [ -z "${BOOTSTRAP_ADMIN_TOKEN:-}" ]; then
BOOTSTRAP_ADMIN_TOKEN="$(python - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
)"
export BOOTSTRAP_ADMIN_TOKEN
printf '%s\n' 'BOOTSTRAP_ADMIN_TOKEN was not set; generated a startup token for first-admin setup.'
fi

printf '%s %s\n' 'Bootstrap admin token:' "$BOOTSTRAP_ADMIN_TOKEN"

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
        print(f"Database ready: {DATABASE_URL}")
        sys.exit(0)
    except Exception as exc:
        last_error = exc
        print(f"Waiting for database (attempt {attempt + 1}/60): {exc}")
        time.sleep(2)

raise SystemExit(f"Database not reachable after waiting: {last_error}")
PY

python scripts/bootstrap_database.py
exec python run.py
