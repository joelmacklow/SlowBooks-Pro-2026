from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.gst_return import GstReturn, GstReturnStatus
from app.services.gst_return import gst_due_date


def get_confirmed_return(db: Session, start_date: date, end_date: date) -> GstReturn | None:
    return (
        db.query(GstReturn)
        .filter(
            GstReturn.start_date == start_date,
            GstReturn.end_date == end_date,
            GstReturn.status == GstReturnStatus.CONFIRMED,
        )
        .first()
    )


def build_confirmed_return_report(record: GstReturn) -> dict:
    return {
        "report_type": "gst_return",
        "start_date": record.start_date.isoformat(),
        "end_date": record.end_date.isoformat(),
        "gst_basis": record.gst_basis,
        "gst_period": record.gst_period,
        "boxes": {
            "5": float(record.box5),
            "6": float(record.box6),
            "7": float(record.box7),
            "8": float(record.box8),
            "9": float(record.box9),
            "10": float(record.box10),
            "11": float(record.box11),
            "12": float(record.box12),
            "13": float(record.box13),
            "14": float(record.box14),
            "15": float(record.box15),
        },
        "output_gst": float(record.output_gst),
        "input_gst": float(record.input_gst),
        "net_gst": float(record.net_gst),
        "net_position": record.net_position,
        "excluded_totals": {"sales": 0.0, "purchases": 0.0},
        "unallocated_payments_total": 0.0,
        "unallocated_bill_payments_total": 0.0,
        "items": [],
    }


def build_return_confirmation_state(record: GstReturn | None) -> dict:
    if not record:
        return {
            "status": "draft",
            "gst_return_id": None,
            "confirmed_at": None,
            "due_date": None,
            "box9_adjustments": "0.00",
            "box13_adjustments": "0.00",
        }
    return {
        "status": "confirmed",
        "gst_return_id": record.id,
        "confirmed_at": record.confirmed_at.isoformat() if record.confirmed_at else None,
        "due_date": record.due_date.isoformat(),
        "box9_adjustments": f"{Decimal(str(record.box9_adjustments)).quantize(Decimal('0.00'))}",
        "box13_adjustments": f"{Decimal(str(record.box13_adjustments)).quantize(Decimal('0.00'))}",
    }


def confirm_return(
    db: Session,
    *,
    start_date: date,
    end_date: date,
    report: dict,
) -> GstReturn:
    if get_confirmed_return(db, start_date, end_date):
        raise HTTPException(status_code=400, detail="GST return is already confirmed for this period")

    record = GstReturn(
        start_date=start_date,
        end_date=end_date,
        due_date=gst_due_date(end_date),
        gst_basis=report.get("gst_basis") or "",
        gst_period=report.get("gst_period") or "",
        net_position=report.get("net_position") or "nil",
        box5=Decimal(str(report["boxes"]["5"])),
        box6=Decimal(str(report["boxes"]["6"])),
        box7=Decimal(str(report["boxes"]["7"])),
        box8=Decimal(str(report["boxes"]["8"])),
        box9=Decimal(str(report["boxes"]["9"])),
        box10=Decimal(str(report["boxes"]["10"])),
        box11=Decimal(str(report["boxes"]["11"])),
        box12=Decimal(str(report["boxes"]["12"])),
        box13=Decimal(str(report["boxes"]["13"])),
        box14=Decimal(str(report["boxes"]["14"])),
        box15=Decimal(str(report["boxes"]["15"])),
        output_gst=Decimal(str(report.get("output_gst", 0))),
        input_gst=Decimal(str(report.get("input_gst", 0))),
        net_gst=Decimal(str(report.get("net_gst", 0))),
        box9_adjustments=Decimal(str(report["boxes"]["9"])),
        box13_adjustments=Decimal(str(report["boxes"]["13"])),
        status=GstReturnStatus.CONFIRMED,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
