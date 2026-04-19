from datetime import date, datetime, timezone

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.blocking import BlockingScheduler

from app.config import DATABASE_URL
from app.database import SessionLocal
from app.services.invoice_reminders import (
    dispatch_due_invoice_reminders,
    get_scheduler_state,
    scheduler_summary_text,
    update_scheduler_state,
)

JOB_ID = "invoice_reminder_dispatch"
JOBSTORE_TABLE = "apscheduler_jobs"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_invoice_reminder_cycle(as_of_date: date | None = None) -> dict:
    db = SessionLocal()
    try:
        state = get_scheduler_state(db)
        started_at = _utc_now_iso()
        update_scheduler_state(
            db,
            invoice_reminder_scheduler_last_run_started_at=started_at,
            invoice_reminder_scheduler_last_heartbeat_at=started_at,
            invoice_reminder_scheduler_last_error="",
        )
        if not state["enabled"]:
            summary = {
                "as_of_date": (as_of_date or date.today()).isoformat(),
                "processed_count": 0,
                "sent_count": 0,
                "failed_count": 0,
                "duplicate_count": 0,
                "status": "disabled",
            }
            update_scheduler_state(
                db,
                invoice_reminder_scheduler_last_run_completed_at=_utc_now_iso(),
                invoice_reminder_scheduler_last_run_status="disabled",
                invoice_reminder_scheduler_last_run_summary=scheduler_summary_text(summary),
            )
            return summary

        summary = dispatch_due_invoice_reminders(db, as_of_date or date.today(), trigger_type="automatic")
        summary["status"] = "ok" if summary["failed_count"] == 0 else "partial_failure"
        update_scheduler_state(
            db,
            invoice_reminder_scheduler_last_run_completed_at=_utc_now_iso(),
            invoice_reminder_scheduler_last_run_status=summary["status"],
            invoice_reminder_scheduler_last_run_summary=scheduler_summary_text(summary),
        )
        return summary
    except Exception as exc:
        error = str(exc)
        update_scheduler_state(
            db,
            invoice_reminder_scheduler_last_run_completed_at=_utc_now_iso(),
            invoice_reminder_scheduler_last_run_status="error",
            invoice_reminder_scheduler_last_run_summary="",
            invoice_reminder_scheduler_last_error=error,
        )
        raise
    finally:
        db.close()


def run_invoice_reminder_scheduler_job() -> dict:
    return run_invoice_reminder_cycle()


def _job_next_run_iso(job) -> str:
    if job is None:
        return ""
    try:
        next_run = getattr(job, "next_run_time")
    except AttributeError:
        return ""
    return next_run.isoformat() if next_run else ""


def _sync_scheduler_metadata(scheduler: BlockingScheduler) -> None:
    db = SessionLocal()
    try:
        state = get_scheduler_state(db)
        interval_minutes = state["interval_minutes"]
        job = scheduler.get_job(JOB_ID)
        if job is not None:
            current_seconds = int(getattr(getattr(job, "trigger", None), "interval", None).total_seconds()) if getattr(getattr(job, "trigger", None), "interval", None) else None
            desired_seconds = interval_minutes * 60
            if current_seconds != desired_seconds:
                scheduler.reschedule_job(JOB_ID, trigger="interval", minutes=interval_minutes)
                job = scheduler.get_job(JOB_ID)
            next_run = _job_next_run_iso(job)
        else:
            next_run = ""
        update_scheduler_state(
            db,
            invoice_reminder_scheduler_last_heartbeat_at=_utc_now_iso(),
            invoice_reminder_scheduler_next_run_at=next_run,
        )
    finally:
        db.close()


def build_invoice_reminder_scheduler() -> BlockingScheduler:
    scheduler = BlockingScheduler(
        jobstores={"default": SQLAlchemyJobStore(url=DATABASE_URL, tablename=JOBSTORE_TABLE)},
        timezone=timezone.utc,
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 300},
    )
    db = SessionLocal()
    try:
        state = get_scheduler_state(db)
        interval_minutes = state["interval_minutes"]
        update_scheduler_state(
            db,
            invoice_reminder_scheduler_last_started_at=_utc_now_iso(),
            invoice_reminder_scheduler_last_heartbeat_at=_utc_now_iso(),
            invoice_reminder_scheduler_last_error="",
        )
    finally:
        db.close()

    scheduler.add_job(
        run_invoice_reminder_scheduler_job,
        trigger="interval",
        minutes=interval_minutes,
        id=JOB_ID,
        replace_existing=True,
    )
    _sync_scheduler_metadata(scheduler)

    def _listener(event):
        _sync_scheduler_metadata(scheduler)
        if event.exception:
            db = SessionLocal()
            try:
                update_scheduler_state(
                    db,
                    invoice_reminder_scheduler_last_run_status="error",
                    invoice_reminder_scheduler_last_error="Scheduler job raised an unhandled exception",
                )
            finally:
                db.close()

    scheduler.add_listener(_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    return scheduler


def run_invoice_reminder_scheduler() -> None:
    scheduler = build_invoice_reminder_scheduler()
    scheduler.start()
