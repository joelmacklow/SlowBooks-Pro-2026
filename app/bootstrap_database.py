"""Canonical database bootstrap entry point for migrations + NZ seed data."""
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from .config import resolve_database_url


def bootstrap_env(database_url: str) -> dict:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    existing_pythonpath = env.get("PYTHONPATH", "").strip()
    path_parts = [str(REPO_ROOT)]
    if existing_pythonpath:
        path_parts.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(path_parts)
    return env


def run_bootstrap(database_url: str | None = None) -> None:
    target_url = database_url or resolve_database_url()
    env = bootstrap_env(target_url)

    commands = [
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        [sys.executable, "scripts/seed_database.py"],
    ]
    for command in commands:
        subprocess.run(command, cwd=REPO_ROOT, env=env, check=True)
