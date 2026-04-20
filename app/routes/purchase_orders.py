# ============================================================================
# Purchase Orders — CRUD + convert to bill
# Feature 6: Non-posting vendor documents
# ============================================================================

import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from starlette.requests import Request

from app.database import get_db
from app.models.purchase_orders import PurchaseOrder, PurchaseOrderLine, POStatus
from app.models.contacts import Vendor
from app.schemas.email import DocumentEmailRequest
from app.schemas.bills import BillCreate, BillLineCreate
from app.schemas.purchase_orders import POCreate, POUpdate, POResponse
from app.services.email_service import render_document_email, send_document_email
from app.services.document_sequences import allocate_document_number
from app.services.gst_calculations import calculate_document_gst, prices_include_gst
from app.services.auth import require_permissions
from app.services.gst_lines import resolve_gst_line_inputs, resolve_line_gst
from app.services.pdf_service import generate_purchase_order_pdf
from app.routes.settings import _get_all as get_settings
from app.services.rate_limit import enforce_rate_limit

router = APIRouter(prefix="/api/purchase-orders", tags=["purchase_orders"])


def _join_address_lines(lines: list[str]) -> str:
    return "\n".join(line.strip() for line in lines if line and line.strip())


def _label_for_address(name: str | None, value: str) -> str:
    parts = [part.strip() for part in value.splitlines() if part.strip()]
    if name and name.strip():
        return ", ".join([name.strip(), *parts])
    return ", ".join(parts)


def _approved_delivery_locations(settings: dict) -> list[dict[str, str]]:
    locations: list[dict[str, str]] = []
    seen: set[str] = set()

    company_lines = [
        settings.get("company_address1", ""),
        settings.get("company_address2", ""),
        " ".join(
            part.strip()
            for part in [
                settings.get("company_city", ""),
                settings.get("company_state", ""),
                settings.get("company_zip", ""),
            ]
            if part and part.strip()
        ),
    ]
    company_value = _join_address_lines(company_lines)
    if company_value:
        normalized = company_value.casefold()
        seen.add(normalized)
        locations.append({
            "label": _label_for_address("Company Main Address", company_value),
            "value": company_value,
        })

    raw_locations = (settings.get("purchase_order_delivery_locations") or "").strip()
    if not raw_locations:
        return locations

    for block in re.split(r"(?:\r?\n){2,}", raw_locations):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if len(lines) == 1:
            name = None
            value = lines[0]
        else:
            name = lines[0]
            value = _join_address_lines(lines[1:])
        if not value:
            continue
        normalized = value.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        locations.append({
            "label": _label_for_address(name, value),
            "value": value,
        })
    return locations


def _approved_delivery_location_values(db: Session) -> set[str]:
    return {
        location["value"]
        for location in _approved_delivery_locations(get_settings(db))
    }


def _validate_ship_to(ship_to: str | None, db: Session) -> None:
    if not ship_to:
        return
    approved_values = _approved_delivery_location_values(db)
    if approved_values and ship_to not in approved_values:
        raise HTTPException(status_code=400, detail="Ship-to address must be an approved delivery location")


def _next_po_number(db: Session) -> str:
    return allocate_document_number(
        db,
        model=PurchaseOrder,
        field_name="po_number",
        prefix_key="purchase_order_prefix",
        next_key="purchase_order_next_number",
        default_prefix="PO-",
        default_next_number="0001",
    )


@router.get("", response_model=list[POResponse])
def list_pos(vendor_id: int = None, status: str = None, db: Session = Depends(get_db), auth=Depends(require_permissions("purchasing.view"))):
    q = db.query(PurchaseOrder)
    if vendor_id:
        q = q.filter(PurchaseOrder.vendor_id == vendor_id)
    if status:
        q = q.filter(PurchaseOrder.status == status)
    pos = q.order_by(PurchaseOrder.date.desc()).all()
    results = []
    for po in pos:
        resp = POResponse.model_validate(po)
        if po.vendor:
            resp.vendor_name = po.vendor.name
        results.append(resp)
    return results


@router.get("/delivery-locations")
def list_delivery_locations(db: Session = Depends(get_db), auth=Depends(require_permissions("purchasing.view"))):
    return _approved_delivery_locations(get_settings(db))


@router.get("/{po_id}", response_model=POResponse)
def get_po(po_id: int, db: Session = Depends(get_db), auth=Depends(require_permissions("purchasing.view"))):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    resp = POResponse.model_validate(po)
    if po.vendor:
        resp.vendor_name = po.vendor.name
    return resp


@router.post("", response_model=POResponse, status_code=201)
def create_po(data: POCreate, db: Session = Depends(get_db), auth=Depends(require_permissions("purchasing.manage"))):
    vendor = db.query(Vendor).filter(Vendor.id == data.vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    _validate_ship_to(data.ship_to, db)

    po_number = _next_po_number(db)
    gst_inputs = resolve_gst_line_inputs(db, data.lines)
    gst_totals = calculate_document_gst(
        gst_inputs,
        prices_include_gst=prices_include_gst(db),
        gst_context="purchase",
    )

    po = PurchaseOrder(
        po_number=po_number, vendor_id=data.vendor_id, date=data.date,
        expected_date=data.expected_date, ship_to=data.ship_to,
        subtotal=gst_totals.subtotal, tax_rate=gst_totals.effective_tax_rate, tax_amount=gst_totals.tax_amount,
        total=gst_totals.total, notes=data.notes,
    )
    db.add(po)
    db.flush()

    for i, line_data in enumerate(data.lines):
        gst_code, gst_rate = resolve_line_gst(db, line_data)
        line_total = gst_totals.lines[i]
        line = PurchaseOrderLine(
            purchase_order_id=po.id, item_id=line_data.item_id,
            description=line_data.description, quantity=line_data.quantity,
            rate=line_data.rate, amount=line_total.net_amount,
            gst_code=gst_code, gst_rate=gst_rate,
            line_order=line_data.line_order or i,
        )
        db.add(line)

    db.commit()
    db.refresh(po)
    resp = POResponse.model_validate(po)
    resp.vendor_name = vendor.name
    return resp


@router.put("/{po_id}", response_model=POResponse)
def update_po(po_id: int, data: POUpdate, db: Session = Depends(get_db), auth=Depends(require_permissions("purchasing.manage"))):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if "ship_to" in data.model_fields_set:
        _validate_ship_to(data.ship_to, db)

    for key, val in data.model_dump(exclude_unset=True, exclude={"lines"}).items():
        if key == "status":
            setattr(po, key, POStatus(val))
        else:
            setattr(po, key, val)

    if data.lines is not None:
        db.query(PurchaseOrderLine).filter(PurchaseOrderLine.purchase_order_id == po_id).delete()
        gst_inputs = resolve_gst_line_inputs(db, data.lines)
        gst_totals = calculate_document_gst(
            gst_inputs,
            prices_include_gst=prices_include_gst(db),
            gst_context="purchase",
        )
        for i, line_data in enumerate(data.lines):
            gst_code, gst_rate = resolve_line_gst(db, line_data)
            amt = gst_totals.lines[i].net_amount
            db.add(PurchaseOrderLine(
                purchase_order_id=po_id, item_id=line_data.item_id,
                description=line_data.description, quantity=line_data.quantity,
                rate=line_data.rate, amount=amt, gst_code=gst_code, gst_rate=gst_rate,
                line_order=line_data.line_order or i,
            ))
        po.subtotal = gst_totals.subtotal
        po.tax_rate = gst_totals.effective_tax_rate
        po.tax_amount = gst_totals.tax_amount
        po.total = gst_totals.total

    db.commit()
    db.refresh(po)
    resp = POResponse.model_validate(po)
    if po.vendor:
        resp.vendor_name = po.vendor.name
    return resp


@router.get("/{po_id}/pdf")
def purchase_order_pdf(po_id: int, db: Session = Depends(get_db), auth=Depends(require_permissions("purchasing.view"))):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    company = get_settings(db)
    pdf_bytes = generate_purchase_order_pdf(po, company)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=PurchaseOrder_{po.po_number}.pdf"},
    )


@router.post("/{po_id}/email")
def email_purchase_order(po_id: int, data: DocumentEmailRequest, db: Session = Depends(get_db), auth=Depends(require_permissions("purchasing.manage")), request: Request = None):
    enforce_rate_limit(
        request,
        scope="email:documents",
        limit=5,
        window_seconds=60,
        detail="Too many document email requests. Please wait and try again.",
    )
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    company = get_settings(db)
    try:
        pdf_bytes = generate_purchase_order_pdf(po, company)
        html_body = render_document_email(
            document_label="Purchase Order",
            recipient_name=po.vendor.name if po.vendor else None,
            document_number=po.po_number,
            company_settings=company,
            amount=po.total,
            action_label="Expected date",
            action_value=po.expected_date,
        )
        send_document_email(
            db,
            to_email=data.recipient,
            subject=data.subject or f"Purchase Order #{po.po_number}",
            html_body=html_body,
            attachment_bytes=pdf_bytes,
            attachment_name=f"PurchaseOrder_{po.po_number}.pdf",
            entity_type="purchase_order",
            entity_id=po.id,
        )
        return {"status": "sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email failed: {str(e)}")


@router.post("/{po_id}/convert-to-bill")
def convert_to_bill(po_id: int, db: Session = Depends(get_db), auth=Depends(require_permissions("purchasing.manage"))):
    """Convert a PO to a bill — creates bill with PO's line items."""
    from app.routes.bills import create_bill

    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status == POStatus.CLOSED:
        raise HTTPException(status_code=400, detail="PO already closed")

    bill = create_bill(BillCreate(
        bill_number=f"BILL-{po.po_number}",
        vendor_id=po.vendor_id,
        po_id=po.id,
        date=po.date,
        terms=get_settings(db).get("default_terms", "Net 30"),
        tax_rate=po.tax_rate,
        notes=f"From {po.po_number}",
        lines=[
            BillLineCreate(
                item_id=line.item_id,
                description=line.description,
                quantity=line.quantity,
                rate=line.rate,
                gst_code=line.gst_code,
                gst_rate=line.gst_rate,
                line_order=line.line_order,
            )
            for line in po.lines
        ],
    ), db=db)

    po.status = POStatus.CLOSED
    db.commit()
    return {"bill_id": bill.id, "message": f"Bill created from {po.po_number}"}
