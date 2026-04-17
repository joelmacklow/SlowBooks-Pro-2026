"""
Seed Slowbooks with a cohesive NZ demo business.

Source material:
- Customer and supplier contacts are derived from Xero Demo Company NZ exports
- Items and transactions are repo-authored NZ demo examples built to fit the
  current NZ chart and product flows
"""
import sys
from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models.accounts import Account
from app.models.banking import BankAccount, BankTransaction
from app.models.bills import Bill, BillLine, BillPayment, BillPaymentAllocation, BillStatus
from app.models.contacts import Customer, Vendor
from app.models.estimates import Estimate, EstimateLine, EstimateStatus
from app.models.invoices import Invoice, InvoiceLine, InvoiceStatus
from app.models.items import Item, ItemType
from app.models.payments import Payment, PaymentAllocation
from app.services.accounting import (
    create_journal_entry,
    get_ap_account_id,
    get_ar_account_id,
    get_default_bank_account_id,
    get_default_expense_account_id,
    get_default_income_account_id,
    get_gst_account_id,
)

GST_RATE = Decimal("0.1500")
ITEM_TYPE_MAP = {
    "service": ItemType.SERVICE,
    "material": ItemType.MATERIAL,
    "labor": ItemType.LABOR,
    "product": ItemType.PRODUCT,
}

VENDORS = [
    {"name": "ABC Furniture", "company": "ABC Furniture", "phone": "800 124578", "email": "", "address1": "", "city": "", "state": "", "zip": "", "country": "NZ", "terms": "Net 30"},
    {"name": "Bayside Club", "company": "Bayside Club", "phone": "02 2024455", "email": "secretarybob@bsclub.co", "address1": "P O Box 3354", "city": "Ridge Heights", "state": "Madeupville", "zip": "6001", "country": "New Zealand", "terms": "Net 30"},
    {"name": "Bayside Wholesale", "company": "Bayside Wholesale", "phone": "850 55669", "email": "", "address1": "", "city": "", "state": "", "zip": "", "country": "NZ", "terms": "Net 30"},
    {"name": "Capital Cab Co", "company": "Capital Cab Holdings", "phone": "800 235689", "email": "", "address1": "", "city": "", "state": "", "zip": "", "country": "NZ", "terms": "Net 30"},
    {"name": "Carlton Functions", "company": "Carlton Functions", "phone": "02 9179945", "email": "", "address1": "", "city": "", "state": "", "zip": "", "country": "NZ", "terms": "Net 30"},
    {"name": "Central Copiers", "company": "Central Copiers", "phone": "800 244844", "email": "", "address1": "", "city": "", "state": "", "zip": "", "country": "NZ", "terms": "Net 30"},
    {"name": "Gateway Motors", "company": "Gateway Motors", "phone": "800 349227", "email": "", "address1": "", "city": "", "state": "", "zip": "", "country": "NZ", "terms": "Net 30"},
    {"name": "Hoyt Productions", "company": "Hoyt Productions", "phone": "02 7411234", "email": "", "address1": "", "city": "", "state": "", "zip": "", "country": "NZ", "terms": "Net 30"},
    {"name": "MCO Cleaning Services", "company": "MCO Cleaning Services", "phone": "02 5119119", "email": "", "address1": "", "city": "", "state": "", "zip": "", "country": "NZ", "terms": "Net 30"},
    {"name": "Net Connect", "company": "Net Connect Holdings", "phone": "800 500998", "email": "", "address1": "P O Box 7900", "city": "Oaktown", "state": "", "zip": "1236", "country": "NZ", "terms": "Net 30"},
    {"name": "PC Complete", "company": "PC Complete", "phone": "800 322600", "email": "", "address1": "", "city": "", "state": "", "zip": "", "country": "NZ", "terms": "Net 30"},
    {"name": "PowerDirect", "company": "PowerDirect Holdings", "phone": "800 887612", "email": "", "address1": "P O Box 8900", "city": "Oaktown", "state": "", "zip": "1288", "country": "NZ", "terms": "Net 30"},
    {"name": "SMART Agency", "company": "SMART Agency", "phone": "02 9159889", "email": "", "address1": "", "city": "", "state": "", "zip": "", "country": "NZ", "terms": "Net 30"},
]

CUSTOMERS = [
    {"name": "Basket Case", "company": None, "phone": "02 9176665", "email": "shop@basketcase.co", "terms": "Net 30", "bill_address1": "Shop 14 Ridgeway Mall", "bill_city": "Pinehaven", "bill_state": "", "bill_zip": "9877", "bill_country": "NZ"},
    {"name": "Bayside Club", "company": None, "phone": "02 2024455", "email": "secretarybob@bsclub.co", "terms": "Net 30", "bill_address1": "P O Box 3354", "bill_city": "Ridge Heights", "bill_state": "Madeupville", "bill_zip": "6001", "bill_country": "New Zealand"},
    {"name": "Boom FM", "company": None, "phone": "01 555 9191", "email": "", "terms": "Net 30", "bill_address1": "", "bill_city": "", "bill_state": "", "bill_zip": "", "bill_country": "NZ"},
    {"name": "City Agency", "company": None, "phone": "01 9173555", "email": "", "terms": "Net 30", "bill_address1": "", "bill_city": "", "bill_state": "", "bill_zip": "", "bill_country": "NZ"},
    {"name": "City Limousines", "company": None, "phone": "01 8004001", "email": "", "terms": "Net 30", "bill_address1": "", "bill_city": "", "bill_state": "", "bill_zip": "", "bill_country": "NZ"},
    {"name": "DIISR - Small Business Services", "company": None, "phone": "01 8009001", "email": "cad@diisr.govt", "terms": "Net 30", "bill_address1": "GPO 9566", "bill_city": "Pinehaven", "bill_state": "", "bill_zip": "9862", "bill_country": "NZ"},
    {"name": "Hamilton Smith Ltd", "company": None, "phone": "01 2345678", "email": "", "terms": "Net 30", "bill_address1": "", "bill_city": "", "bill_state": "", "bill_zip": "", "bill_country": "NZ"},
    {"name": "Ridgeway University", "company": None, "phone": "01 8005001", "email": "", "terms": "Net 30", "bill_address1": "", "bill_city": "", "bill_state": "", "bill_zip": "", "bill_country": "NZ"},
]

ITEMS = [
    {"name": "Strategy Workshop",         "item_type": "service",  "rate": 950.00,  "description": "Half-day strategic planning workshop", "income_acct": "200"},
    {"name": "Monthly Advisory Retainer", "item_type": "service",  "rate": 650.00,  "description": "Monthly business advisory support",    "income_acct": "200"},
    {"name": "Website Refresh",           "item_type": "service",  "rate": 1800.00, "description": "Website refresh and content update",   "income_acct": "200"},
    {"name": "Payroll Filing Setup",      "item_type": "service",  "rate": 1200.00, "description": "Payroll and filing setup support",     "income_acct": "200"},
    {"name": "Compliance Review",         "item_type": "service",  "rate": 780.00,  "description": "Operational compliance review",        "income_acct": "200"},
    {"name": "Training Session",          "item_type": "service",  "rate": 480.00,  "description": "Staff process and systems training",   "income_acct": "200"},
    {"name": "Content Pack",              "item_type": "service",  "rate": 520.00,  "description": "Campaign or website content package",  "income_acct": "200"},
    {"name": "Travel Recovery",           "item_type": "service",  "rate": 85.00,   "description": "Travel and delivery recovery charge",  "income_acct": "260"},
]

INVOICES = [
    {"invoice_number": "2001", "customer": "Basket Case", "day_offset": 3, "terms": "Net 30", "lines": [("Website Refresh", 1, 1800.00), ("Training Session", 1, 480.00)]},
    {"invoice_number": "2002", "customer": "Bayside Club", "day_offset": 5, "terms": "Net 30", "lines": [("Monthly Advisory Retainer", 1, 650.00), ("Travel Recovery", 1, 85.00)]},
    {"invoice_number": "2003", "customer": "Boom FM", "day_offset": 7, "terms": "Net 30", "lines": [("Strategy Workshop", 1, 950.00), ("Content Pack", 1, 520.00)]},
    {"invoice_number": "2004", "customer": "City Agency", "day_offset": 10, "terms": "Net 15", "lines": [("Compliance Review", 1, 780.00), ("Training Session", 1, 480.00)]},
    {"invoice_number": "2005", "customer": "City Limousines", "day_offset": 12, "terms": "Net 30", "lines": [("Payroll Filing Setup", 1, 1200.00)]},
    {"invoice_number": "2006", "customer": "DIISR - Small Business Services", "day_offset": 14, "terms": "Net 30", "lines": [("Monthly Advisory Retainer", 2, 650.00)]},
    {"invoice_number": "2007", "customer": "Hamilton Smith Ltd", "day_offset": 17, "terms": "Net 30", "lines": [("Website Refresh", 1, 1800.00), ("Travel Recovery", 2, 85.00)]},
    {"invoice_number": "2008", "customer": "Ridgeway University", "day_offset": 20, "terms": "Net 45", "lines": [("Strategy Workshop", 2, 950.00)]},
    {"invoice_number": "2009", "customer": "Basket Case", "day_offset": 24, "terms": "Net 30", "lines": [("Monthly Advisory Retainer", 1, 650.00)]},
    {"invoice_number": "2010", "customer": "Boom FM", "day_offset": 27, "terms": "Net 30", "lines": [("Training Session", 2, 480.00), ("Content Pack", 1, 520.00)]},
]

ESTIMATES = [
    {"estimate_number": "E-100", "customer": "City Agency", "day_offset": 5, "lines": [("Website Refresh", 1, 1800.00), ("Content Pack", 2, 520.00)]},
    {"estimate_number": "E-101", "customer": "DIISR - Small Business Services", "day_offset": 8, "lines": [("Payroll Filing Setup", 1, 1200.00), ("Training Session", 2, 480.00)]},
    {"estimate_number": "E-102", "customer": "Hamilton Smith Ltd", "day_offset": 15, "lines": [("Strategy Workshop", 1, 950.00), ("Monthly Advisory Retainer", 3, 650.00)]},
]

PAYMENTS = [
    {"customer": "Basket Case", "invoice_number": "2001", "day_offset": 10, "amount": 1200.00, "method": "EFT", "reference": "RCPT-4501", "statement_reconciled": True},
    {"customer": "Bayside Club", "invoice_number": "2002", "day_offset": 15, "amount": 845.25, "method": "EFT", "reference": "RCPT-4502", "statement_reconciled": False},
    {"customer": "Ridgeway University", "invoice_number": "2008", "day_offset": 21, "amount": 2185.00, "method": "EFT", "reference": "RCPT-4503", "statement_reconciled": True},
    {"customer": "City Limousines", "invoice_number": "2005", "day_offset": 20, "amount": 1380.00, "method": "Credit", "reference": "RCPT-4504", "statement_reconciled": False},
    {"customer": "Boom FM", "invoice_number": "2003", "day_offset": 22, "amount": 900.00, "method": "Cash", "reference": "RCPT-4505", "statement_reconciled": False},
]

BILLS = [
    {"bill_number": "3001", "vendor": "ABC Furniture", "day_offset": 4, "terms": "Net 30", "ref_number": "AF-001", "lines": [("Office seating refresh", 1, 365.00)]},
    {"bill_number": "3002", "vendor": "PowerDirect", "day_offset": 8, "terms": "Net 30", "ref_number": "PD-2201", "lines": [("Electricity account", 1, 162.00)]},
    {"bill_number": "3003", "vendor": "Net Connect", "day_offset": 16, "terms": "Net 30", "ref_number": "NC-7781", "lines": [("Internet and phone services", 1, 113.00)]},
]

BILL_PAYMENTS = [
    {"vendor": "ABC Furniture", "bill_number": "3001", "day_offset": 11, "amount": 419.75, "method": "EFT", "check_number": "BP-7001", "statement_reconciled": True},
    {"vendor": "PowerDirect", "bill_number": "3002", "day_offset": 13, "amount": 186.30, "method": "EFT", "check_number": "BP-7002", "statement_reconciled": False},
    {"vendor": "Net Connect", "bill_number": "3003", "day_offset": 23, "amount": 129.95, "method": "EFT", "check_number": "BP-7003", "statement_reconciled": False},
]

BANK_ACCOUNT = {"name": "ANZ Business Account", "bank_name": "ANZ", "last_four": "1208"}


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def get_account_by_number(db, num):
    return db.query(Account).filter(Account.account_number == num).first()


def due_date_from_terms(doc_date: date, terms: str) -> date:
    terms_days = {"Net 15": 15, "Net 30": 30, "Net 45": 45, "Due on Receipt": 0}.get(terms, 30)
    return doc_date + timedelta(days=terms_days)


def build_lines(lines_data, item_map):
    subtotal = Decimal("0")
    built = []
    for index, (item_name, qty, rate) in enumerate(lines_data):
        item = item_map[item_name]
        quantity = Decimal(str(qty))
        line_rate = Decimal(str(rate))
        amount = (quantity * line_rate).quantize(Decimal("0.01"))
        subtotal += amount
        built.append({
            "item_id": item.id,
            "description": item.description,
            "quantity": quantity,
            "rate": line_rate,
            "amount": amount,
            "line_order": index,
        })
    tax_amount = (subtotal * GST_RATE).quantize(Decimal("0.01"))
    total = subtotal + tax_amount
    return subtotal, tax_amount, total, built


def seed():
    db = SessionLocal()
    base_year = date.today().year
    base_date = date(base_year, 1, 1)

    try:
        print("Seeding cohesive NZ demo business from Xero-derived contacts...")

        vendor_map = {}
        created_vendors = 0
        for spec in VENDORS:
            existing = db.query(Vendor).filter(Vendor.name == spec["name"]).first()
            if existing:
                vendor_map[spec["name"]] = existing
                continue
            vendor = Vendor(
                name=spec["name"],
                company=spec["company"],
                email=spec.get("email"),
                phone=spec["phone"],
                terms=spec["terms"],
                address1=spec.get("address1"),
                city=spec.get("city"),
                state=spec.get("state"),
                zip=spec.get("zip"),
                country=spec.get("country") or "NZ",
                is_active=True,
            )
            db.add(vendor)
            db.flush()
            vendor_map[spec["name"]] = vendor
            created_vendors += 1
        print(f"  {created_vendors} vendors created ({len(VENDORS) - created_vendors} existing)")

        customer_map = {}
        created_customers = 0
        for spec in CUSTOMERS:
            existing = db.query(Customer).filter(Customer.name == spec["name"]).first()
            if existing:
                customer_map[spec["name"]] = existing
                continue
            customer = Customer(
                name=spec["name"],
                company=spec.get("company"),
                phone=spec["phone"],
                email=spec["email"],
                terms=spec["terms"],
                bill_address1=spec.get("bill_address1"),
                bill_city=spec.get("bill_city"),
                bill_state=spec.get("bill_state"),
                bill_zip=spec.get("bill_zip"),
                bill_country=spec.get("bill_country") or "NZ",
                is_active=True,
                is_taxable=True,
            )
            db.add(customer)
            db.flush()
            customer_map[spec["name"]] = customer
            created_customers += 1
        print(f"  {created_customers} customers created ({len(CUSTOMERS) - created_customers} existing)")

        item_map = {}
        created_items = 0
        for spec in ITEMS:
            existing = db.query(Item).filter(Item.name == spec["name"]).first()
            if existing:
                item_map[spec["name"]] = existing
                continue
            income_account = get_account_by_number(db, spec["income_acct"])
            item = Item(
                name=spec["name"],
                item_type=ITEM_TYPE_MAP[spec["item_type"]],
                rate=Decimal(str(spec["rate"])),
                description=spec["description"],
                income_account_id=income_account.id if income_account else None,
                is_taxable=True,
                is_active=True,
            )
            db.add(item)
            db.flush()
            item_map[spec["name"]] = item
            created_items += 1
        print(f"  {created_items} items created ({len(ITEMS) - created_items} existing)")

        ar_id = get_ar_account_id(db)
        ap_id = get_ap_account_id(db)
        default_bank_account_id = get_default_bank_account_id(db)
        default_income_account_id = get_default_income_account_id(db)
        default_expense_account_id = get_default_expense_account_id(db)
        gst_account_id = get_gst_account_id(db)

        invoice_map = {}
        created_invoices = 0
        for spec in INVOICES:
            existing = db.query(Invoice).filter(Invoice.invoice_number == spec["invoice_number"]).first()
            if existing:
                invoice_map[spec["invoice_number"]] = existing
                continue

            customer = customer_map[spec["customer"]]
            invoice_date = base_date + timedelta(days=spec["day_offset"] - 1)
            subtotal, tax_amount, total, built_lines = build_lines(spec["lines"], item_map)
            invoice = Invoice(
                invoice_number=spec["invoice_number"],
                customer_id=customer.id,
                date=invoice_date,
                due_date=due_date_from_terms(invoice_date, spec["terms"]),
                terms=spec["terms"],
                status=InvoiceStatus.SENT,
                subtotal=subtotal,
                tax_rate=GST_RATE,
                tax_amount=tax_amount,
                total=total,
                amount_paid=Decimal("0"),
                balance_due=total,
            )
            db.add(invoice)
            db.flush()

            for line_data in built_lines:
                db.add(InvoiceLine(invoice_id=invoice.id, **line_data))

            if ar_id:
                journal_lines = [{
                    "account_id": ar_id,
                    "debit": total,
                    "credit": Decimal("0"),
                    "description": f"Invoice {spec['invoice_number']}",
                }]
                if subtotal > 0 and default_income_account_id:
                    journal_lines.append({
                        "account_id": default_income_account_id,
                        "debit": Decimal("0"),
                        "credit": subtotal,
                        "description": f"Invoice {spec['invoice_number']}",
                    })
                if tax_amount > 0 and gst_account_id:
                    journal_lines.append({
                        "account_id": gst_account_id,
                        "debit": Decimal("0"),
                        "credit": tax_amount,
                        "description": f"Invoice {spec['invoice_number']} tax",
                    })
                txn = create_journal_entry(
                    db,
                    invoice_date,
                    f"Invoice {spec['invoice_number']}",
                    journal_lines,
                    source_type="invoice",
                    source_id=invoice.id,
                )
                invoice.transaction_id = txn.id

            invoice_map[spec["invoice_number"]] = invoice
            created_invoices += 1
        print(f"  {created_invoices} invoices created ({len(INVOICES) - created_invoices} existing)")

        created_estimates = 0
        for spec in ESTIMATES:
            existing = db.query(Estimate).filter(Estimate.estimate_number == spec["estimate_number"]).first()
            if existing:
                continue
            customer = customer_map[spec["customer"]]
            estimate_date = base_date + timedelta(days=spec["day_offset"] - 1)
            subtotal, tax_amount, total, built_lines = build_lines(spec["lines"], item_map)
            estimate = Estimate(
                estimate_number=spec["estimate_number"],
                customer_id=customer.id,
                date=estimate_date,
                expiration_date=estimate_date + timedelta(days=30),
                status=EstimateStatus.PENDING,
                subtotal=subtotal,
                tax_rate=GST_RATE,
                tax_amount=tax_amount,
                total=total,
            )
            db.add(estimate)
            db.flush()
            for line_data in built_lines:
                db.add(EstimateLine(estimate_id=estimate.id, **line_data))
            created_estimates += 1
        print(f"  {created_estimates} estimates created ({len(ESTIMATES) - created_estimates} existing)")

        created_payments = 0
        for spec in PAYMENTS:
            customer = customer_map[spec["customer"]]
            existing = db.query(Payment).filter(
                Payment.customer_id == customer.id,
                Payment.reference == spec["reference"],
            ).first()
            if existing:
                continue
            invoice = invoice_map[spec["invoice_number"]]
            payment_date = base_date + timedelta(days=spec["day_offset"] - 1)
            amount = money(spec["amount"])
            payment = Payment(
                customer_id=customer.id,
                date=payment_date,
                amount=amount,
                method=spec["method"],
                reference=spec["reference"],
                deposit_to_account_id=default_bank_account_id,
            )
            db.add(payment)
            db.flush()

            alloc_amount = min(amount, Decimal(str(invoice.balance_due or 0)))
            if alloc_amount > 0:
                db.add(PaymentAllocation(payment_id=payment.id, invoice_id=invoice.id, amount=alloc_amount))
                invoice.amount_paid = Decimal(str(invoice.amount_paid or 0)) + alloc_amount
                invoice.balance_due = Decimal(str(invoice.total or 0)) - invoice.amount_paid
                if invoice.balance_due <= 0:
                    invoice.status = InvoiceStatus.PAID
                elif invoice.amount_paid > 0:
                    invoice.status = InvoiceStatus.PARTIAL

            if ar_id and default_bank_account_id:
                txn = create_journal_entry(
                    db,
                    payment_date,
                    f"Payment from {spec['customer']}",
                    [
                        {"account_id": default_bank_account_id, "debit": amount, "credit": Decimal("0"), "description": f"Payment from {spec['customer']}"},
                        {"account_id": ar_id, "debit": Decimal("0"), "credit": amount, "description": f"Payment from {spec['customer']}"},
                    ],
                    source_type="payment",
                    source_id=payment.id,
                )
                payment.transaction_id = txn.id
            created_payments += 1
        print(f"  {created_payments} payments created ({len(PAYMENTS) - created_payments} existing)")

        bill_map = {}
        created_bills = 0
        for spec in BILLS:
            existing = db.query(Bill).filter(Bill.bill_number == spec["bill_number"]).first()
            if existing:
                bill_map[spec["bill_number"]] = existing
                continue
            vendor = vendor_map[spec["vendor"]]
            bill_date = base_date + timedelta(days=spec["day_offset"] - 1)
            subtotal = Decimal("0")
            built_lines = []
            for index, (description, qty, rate) in enumerate(spec["lines"]):
                quantity = Decimal(str(qty))
                line_rate = Decimal(str(rate))
                amount = (quantity * line_rate).quantize(Decimal("0.01"))
                subtotal += amount
                built_lines.append({
                    "description": description,
                    "quantity": quantity,
                    "rate": line_rate,
                    "amount": amount,
                    "line_order": index,
                })
            tax_amount = (subtotal * GST_RATE).quantize(Decimal("0.01"))
            total = subtotal + tax_amount
            bill = Bill(
                bill_number=spec["bill_number"],
                vendor_id=vendor.id,
                status=BillStatus.UNPAID,
                date=bill_date,
                due_date=due_date_from_terms(bill_date, spec["terms"]),
                terms=spec["terms"],
                ref_number=spec["ref_number"],
                subtotal=subtotal,
                tax_rate=GST_RATE,
                tax_amount=tax_amount,
                total=total,
                amount_paid=Decimal("0"),
                balance_due=total,
            )
            db.add(bill)
            db.flush()
            for line_data in built_lines:
                db.add(BillLine(
                    bill_id=bill.id,
                    account_id=default_expense_account_id,
                    gst_code="GST15",
                    gst_rate=GST_RATE,
                    **line_data,
                ))
            if ap_id:
                journal_lines = []
                if subtotal > 0 and default_expense_account_id:
                    journal_lines.append({
                        "account_id": default_expense_account_id,
                        "debit": subtotal,
                        "credit": Decimal("0"),
                        "description": f"Bill {spec['bill_number']} - {spec['vendor']}",
                    })
                if tax_amount > 0 and gst_account_id:
                    journal_lines.append({
                        "account_id": gst_account_id,
                        "debit": tax_amount,
                        "credit": Decimal("0"),
                        "description": "GST on bill",
                    })
                journal_lines.append({
                    "account_id": ap_id,
                    "debit": Decimal("0"),
                    "credit": total,
                    "description": f"Bill {spec['bill_number']} - {spec['vendor']}",
                })
                txn = create_journal_entry(
                    db,
                    bill_date,
                    f"Bill {spec['bill_number']} - {spec['vendor']}",
                    journal_lines,
                    source_type="bill",
                    source_id=bill.id,
                    reference=spec["bill_number"],
                )
                bill.transaction_id = txn.id
            bill_map[spec["bill_number"]] = bill
            created_bills += 1
        print(f"  {created_bills} bills created ({len(BILLS) - created_bills} existing)")

        created_bill_payments = 0
        for spec in BILL_PAYMENTS:
            vendor = vendor_map[spec["vendor"]]
            existing = db.query(BillPayment).filter(
                BillPayment.vendor_id == vendor.id,
                BillPayment.check_number == spec["check_number"],
            ).first()
            if existing:
                continue
            bill = bill_map[spec["bill_number"]]
            payment_date = base_date + timedelta(days=spec["day_offset"] - 1)
            amount = money(spec["amount"])
            payment = BillPayment(
                vendor_id=vendor.id,
                date=payment_date,
                amount=amount,
                method=spec["method"],
                check_number=spec["check_number"],
                pay_from_account_id=default_bank_account_id,
            )
            db.add(payment)
            db.flush()
            alloc_amount = min(amount, Decimal(str(bill.balance_due or 0)))
            if alloc_amount > 0:
                db.add(BillPaymentAllocation(bill_payment_id=payment.id, bill_id=bill.id, amount=alloc_amount))
                bill.amount_paid = Decimal(str(bill.amount_paid or 0)) + alloc_amount
                bill.balance_due = Decimal(str(bill.total or 0)) - bill.amount_paid
                bill.status = BillStatus.PAID if bill.balance_due <= 0 else BillStatus.PARTIAL
            if ap_id and default_bank_account_id:
                txn = create_journal_entry(
                    db,
                    payment_date,
                    f"Bill payment to {spec['vendor']}",
                    [
                        {"account_id": ap_id, "debit": amount, "credit": Decimal("0"), "description": f"Bill payment to {spec['vendor']}"},
                        {"account_id": default_bank_account_id, "debit": Decimal("0"), "credit": amount, "description": f"Bill payment to {spec['vendor']}"},
                    ],
                    source_type="bill_payment",
                    source_id=payment.id,
                )
                payment.transaction_id = txn.id
            created_bill_payments += 1
        print(f"  {created_bill_payments} bill payments created ({len(BILL_PAYMENTS) - created_bill_payments} existing)")

        bank_account = db.query(BankAccount).filter(BankAccount.name == BANK_ACCOUNT["name"]).first()
        if not bank_account:
            bank_account = BankAccount(
                name=BANK_ACCOUNT["name"],
                account_id=get_account_by_number(db, "090").id if get_account_by_number(db, "090") else None,
                bank_name=BANK_ACCOUNT["bank_name"],
                last_four=BANK_ACCOUNT["last_four"],
                balance=Decimal("0"),
                is_active=True,
            )
            db.add(bank_account)
            db.flush()
            created_bank_accounts = 1
        else:
            bank_account.account_id = get_account_by_number(db, "090").id if get_account_by_number(db, "090") else bank_account.account_id
            bank_account.bank_name = BANK_ACCOUNT["bank_name"]
            bank_account.last_four = BANK_ACCOUNT["last_four"]
            bank_account.is_active = True
            created_bank_accounts = 0

        created_bank_transactions = 0
        for spec in PAYMENTS:
            payment_date = base_date + timedelta(days=spec["day_offset"] - 1)
            amount = money(spec["amount"])
            description = f"Invoice payment {spec['reference']}"
            existing = db.query(BankTransaction).filter(
                BankTransaction.bank_account_id == bank_account.id,
                BankTransaction.date == payment_date,
                BankTransaction.amount == amount,
                BankTransaction.payee == spec["customer"],
                BankTransaction.description == description,
            ).first()
            if existing:
                existing.reconciled = bool(spec["statement_reconciled"])
                existing.category_account_id = ar_id
                existing.reference = spec["reference"]
                existing.code = spec["invoice_number"]
                continue
            db.add(BankTransaction(
                bank_account_id=bank_account.id,
                date=payment_date,
                amount=amount,
                payee=spec["customer"],
                description=description,
                reference=spec["reference"],
                code=spec["invoice_number"],
                category_account_id=ar_id,
                reconciled=bool(spec["statement_reconciled"]),
            ))
            created_bank_transactions += 1

        for spec in BILL_PAYMENTS:
            payment_date = base_date + timedelta(days=spec["day_offset"] - 1)
            amount = money(spec["amount"]) * Decimal("-1")
            description = f"Bill payment {spec['check_number']}"
            existing = db.query(BankTransaction).filter(
                BankTransaction.bank_account_id == bank_account.id,
                BankTransaction.date == payment_date,
                BankTransaction.amount == amount,
                BankTransaction.payee == spec["vendor"],
                BankTransaction.description == description,
            ).first()
            if existing:
                existing.reconciled = bool(spec["statement_reconciled"])
                existing.category_account_id = ap_id
                existing.reference = spec["check_number"]
                existing.code = spec["bill_number"]
                continue
            db.add(BankTransaction(
                bank_account_id=bank_account.id,
                date=payment_date,
                amount=amount,
                payee=spec["vendor"],
                description=description,
                reference=spec["check_number"],
                code=spec["bill_number"],
                category_account_id=ap_id,
                reconciled=bool(spec["statement_reconciled"]),
            ))
            created_bank_transactions += 1

        db.flush()
        bank_account.balance = sum((Decimal(str(txn.amount)) for txn in db.query(BankTransaction).filter(BankTransaction.bank_account_id == bank_account.id).all()), Decimal("0"))
        print(f"  {created_bank_accounts} ANZ bank accounts created ({1 - created_bank_accounts} existing)")
        print(f"  {created_bank_transactions} bank statement lines created")

        db.commit()

        total_invoiced = sum(Decimal(str(inv.total)) for inv in db.query(Invoice).filter(Invoice.invoice_number.in_([spec["invoice_number"] for spec in INVOICES])).all())
        total_received = sum(Decimal(str(payment.amount)) for payment in db.query(Payment).filter(Payment.reference.in_([spec["reference"] for spec in PAYMENTS])).all())
        total_billed = sum(Decimal(str(bill.total)) for bill in db.query(Bill).filter(Bill.bill_number.in_([spec["bill_number"] for spec in BILLS])).all())
        total_paid_out = sum(Decimal(str(payment.amount)) for payment in db.query(BillPayment).filter(BillPayment.check_number.in_([spec["check_number"] for spec in BILL_PAYMENTS])).all())

        print("\nNZ demo business seeded successfully.")
        print(f"  Total invoiced: ${total_invoiced:,.2f}")
        print(f"  Total received: ${total_received:,.2f}")
        print(f"  Total billed:   ${total_billed:,.2f}")
        print(f"  Total paid out: ${total_paid_out:,.2f}")
        print(f"  ANZ balance:    ${bank_account.balance:,.2f}")

    except Exception as exc:
        db.rollback()
        print(f"Error: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
