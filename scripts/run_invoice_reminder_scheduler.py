#!/usr/bin/env python3
"""Run the dedicated APScheduler service for invoice reminder automation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.invoice_reminder_scheduler import run_invoice_reminder_scheduler


if __name__ == "__main__":
    run_invoice_reminder_scheduler()
