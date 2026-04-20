# ============================================================================
# Bank Statement Import Service — parse bank feeds from OFX/QFX and CSV files
# Feature 18+: Import, dedup, preview, and store NZ statement metadata
# ============================================================================

import csv
import hashlib
import io
import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.banking import BankAccount, BankTransaction
from app.services.bank_rules import apply_bank_rule_suggestion

CSV_HEADER = [
    "Type",
    "Details",
    "Particulars",
    "Code",
    "Reference",
    "Amount",
    "Date",
    "ForeignCurrencyAmount",
    "ConversionCharge",
]


def detect_statement_format(content, filename: str | None = None) -> str:
    name = (filename or "").lower()
    if name.endswith(".csv"):
        return "csv"
    if name.endswith(".ofx") or name.endswith(".qfx"):
        return "ofx"

    sample = content.decode("utf-8", errors="ignore") if isinstance(content, (bytes, bytearray)) else str(content)
    sample = sample.lstrip("\ufeff\n\r\t ")
    if sample.startswith(",".join(CSV_HEADER[:6])) or sample.startswith("Type,Details,Particulars"):
        return "csv"
    return "ofx"


def parse_statement_file(content, filename: str | None = None) -> dict:
    statement_format = detect_statement_format(content, filename)
    if statement_format == "csv":
        return {"format": "csv", "transactions": parse_csv_statement(content)}
    return {"format": "ofx", "transactions": parse_ofx(content)}


def parse_csv_statement(content) -> list[dict]:
    text = content.decode("utf-8-sig") if isinstance(content, (bytes, bytearray)) else str(content)
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV file is missing a header row")

    expected = set(CSV_HEADER[:7])
    missing = [name for name in expected if name not in reader.fieldnames]
    if missing:
        raise ValueError(f"CSV file is missing expected columns: {', '.join(sorted(missing))}")

    transactions = []
    for row in reader:
        amount_raw = (row.get("Amount") or "").strip()
        date_raw = (row.get("Date") or "").strip()
        if not amount_raw or not date_raw:
            continue

        amount = Decimal(amount_raw)
        txn_date = datetime.strptime(date_raw, "%d/%m/%Y").date()
        txn_type = (row.get("Type") or "").strip()
        payee = (row.get("Details") or "").strip()
        description = (row.get("Particulars") or "").strip()
        code = (row.get("Code") or "").strip() or None
        reference = (row.get("Reference") or "").strip() or None
        fingerprint = hashlib.sha1(
            "|".join([
                txn_type,
                payee,
                description,
                code or "",
                reference or "",
                amount_raw,
                date_raw,
            ]).encode("utf-8")
        ).hexdigest()
        transactions.append({
            "import_id": fingerprint,
            "date": txn_date,
            "amount": amount,
            "payee": payee,
            "description": description,
            "code": code,
            "reference": reference,
            "type": txn_type,
            "memo": description,
            "source": "csv",
        })
    return transactions


def parse_ofx(content: str) -> list[dict]:
    """Parse OFX/QFX file content into a list of transaction dicts."""
    transactions = []

    try:
        from ofxparse import OfxParser
        from io import BytesIO

        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content

        ofx = OfxParser.parse(BytesIO(content_bytes))

        for account in ofx.accounts:
            for txn in account.statement.transactions:
                transactions.append({
                    "import_id": txn.id,
                    "date": txn.date.date() if hasattr(txn.date, 'date') else txn.date,
                    "amount": Decimal(str(txn.amount)),
                    "payee": txn.payee or txn.memo or "",
                    "description": txn.memo or "",
                    "code": None,
                    "reference": None,
                    "type": txn.type or "",
                    "memo": txn.memo or "",
                    "source": "ofx",
                })
    except ImportError:
        import re
        txn_blocks = re.findall(r'<STMTTRN>(.*?)</STMTTRN>', content if isinstance(content, str) else content.decode('utf-8'), re.DOTALL)
        for block in txn_blocks:
            fitid = _extract_tag(block, "FITID")
            dt = _extract_tag(block, "DTPOSTED")
            amt = _extract_tag(block, "TRNAMT")
            name = _extract_tag(block, "NAME")
            memo = _extract_tag(block, "MEMO")
            txn_type = _extract_tag(block, "TRNTYPE")

            if dt and amt:
                txn_date = date(int(dt[:4]), int(dt[4:6]), int(dt[6:8]))
                transactions.append({
                    "import_id": fitid or hashlib.sha1(f"{dt}|{amt}|{name}|{memo}".encode("utf-8")).hexdigest(),
                    "date": txn_date,
                    "amount": Decimal(amt),
                    "payee": name or "",
                    "description": memo or "",
                    "code": None,
                    "reference": None,
                    "type": txn_type or "",
                    "memo": memo or "",
                    "source": "ofx",
                })

    return transactions


def _extract_tag(block: str, tag: str) -> str:
    import re
    match = re.search(rf'<{tag}>([^<\n]+)', block)
    return match.group(1).strip() if match else ""


def statement_summary(transactions: list[dict], ending_balance: Decimal | None = None, import_batch_id: str | None = None) -> dict:
    statement_date = max((txn.get("date") for txn in transactions), default=None)
    total = sum((Decimal(str(txn.get("amount") or 0)) for txn in transactions), Decimal("0"))
    summary = {
        "statement_date": statement_date.isoformat() if statement_date else None,
        "statement_delta": float(total),
        "statement_total": float(total),
    }
    if ending_balance is not None:
        summary["statement_balance"] = float(ending_balance)
    if import_batch_id is not None:
        summary["import_batch_id"] = import_batch_id
    return summary


def import_transactions(db: Session, bank_account_id: int, transactions: list[dict], import_source: str | None = None) -> dict:
    imported = 0
    skipped = 0
    import_batch_id = uuid.uuid4().hex
    bank_account = db.query(BankAccount).filter(BankAccount.id == bank_account_id).first()
    if not bank_account:
        raise ValueError("Bank account not found")

    for txn in transactions:
        import_id = txn.get("import_id") or txn.get("fitid") or hashlib.sha1(
            "|".join([
                str(txn.get("date") or ""),
                str(txn.get("amount") or ""),
                txn.get("payee") or "",
                txn.get("description") or txn.get("memo") or "",
                txn.get("code") or "",
                txn.get("reference") or "",
            ]).encode("utf-8")
        ).hexdigest()
        existing = db.query(BankTransaction).filter(
            BankTransaction.bank_account_id == bank_account_id,
            BankTransaction.import_id == import_id,
        ).first()
        if existing:
            skipped += 1
            continue

        amount = Decimal(str(txn["amount"]))
        bt = BankTransaction(
            bank_account_id=bank_account_id,
            date=txn["date"],
            amount=amount,
            payee=txn.get("payee", ""),
            description=txn.get("description") or txn.get("memo") or "",
            check_number=None,
            reference=txn.get("reference"),
            code=txn.get("code"),
            import_id=import_id,
            import_source=import_source or txn.get("source") or "ofx",
            import_batch_id=import_batch_id,
            match_status="unmatched",
        )
        db.add(bt)
        db.flush()
        apply_bank_rule_suggestion(db, bt, persist=True)
        imported += 1

    ending_balance = Decimal(str(bank_account.balance or 0))
    db.commit()
    return {"imported": imported, "skipped": skipped, "total": len(transactions), "ending_balance": ending_balance, "import_batch_id": import_batch_id}
