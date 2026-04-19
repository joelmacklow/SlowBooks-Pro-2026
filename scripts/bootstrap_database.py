"""Canonical database bootstrap entry point for migrations + NZ seed data."""
from app.bootstrap_database import run_bootstrap


if __name__ == "__main__":
    run_bootstrap()
