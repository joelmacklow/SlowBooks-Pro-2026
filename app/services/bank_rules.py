from __future__ import annotations

import re
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.accounts import Account
from app.models.banking import BankRule, BankRuleDirection, BankTransaction


def normalized_bank_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def bank_rule_direction(bank_txn: BankTransaction) -> BankRuleDirection:
    return BankRuleDirection.INFLOW if Decimal(str(bank_txn.amount or 0)) >= 0 else BankRuleDirection.OUTFLOW


def _bank_transaction_text(bank_txn: BankTransaction) -> dict[str, str]:
    return {
        "payee": normalized_bank_text(bank_txn.payee),
        "description": normalized_bank_text(bank_txn.description),
        "reference": normalized_bank_text(bank_txn.reference),
        "code": normalized_bank_text(bank_txn.code),
    }


def _rule_has_match_criteria(rule: BankRule) -> bool:
    return any([
        normalized_bank_text(rule.payee_contains),
        normalized_bank_text(rule.description_contains),
        normalized_bank_text(rule.reference_contains),
        normalized_bank_text(rule.code_equals),
    ])


def _match_reason(rule: BankRule, bank_txn: BankTransaction) -> list[str]:
    fields = _bank_transaction_text(bank_txn)
    reasons: list[str] = []

    payee_contains = normalized_bank_text(rule.payee_contains)
    if payee_contains:
        if payee_contains not in fields["payee"]:
            return []
        reasons.append(f"payee contains '{rule.payee_contains.strip()}'")

    description_contains = normalized_bank_text(rule.description_contains)
    if description_contains:
        if description_contains not in fields["description"]:
            return []
        reasons.append(f"description contains '{rule.description_contains.strip()}'")

    reference_contains = normalized_bank_text(rule.reference_contains)
    if reference_contains:
        if reference_contains not in fields["reference"]:
            return []
        reasons.append(f"reference contains '{rule.reference_contains.strip()}'")

    code_equals = normalized_bank_text(rule.code_equals)
    if code_equals:
        if code_equals != fields["code"]:
            return []
        reasons.append(f"code equals '{rule.code_equals.strip()}'")

    return reasons if reasons and _rule_has_match_criteria(rule) else []


def candidate_bank_rules(db: Session, bank_txn: BankTransaction) -> list[BankRule]:
    direction = bank_rule_direction(bank_txn)
    rules = (
        db.query(BankRule)
        .filter(BankRule.is_active == True)
        .order_by(BankRule.priority.asc(), BankRule.id.asc())
        .all()
    )
    result = []
    for rule in rules:
        if rule.bank_account_id and rule.bank_account_id != bank_txn.bank_account_id:
            continue
        if rule.direction not in (BankRuleDirection.ANY, direction):
            continue
        if not _rule_has_match_criteria(rule):
            continue
        result.append(rule)
    return result


def find_matching_bank_rule(db: Session, bank_txn: BankTransaction) -> tuple[BankRule | None, list[str]]:
    if bank_txn.transaction_id or bank_txn.match_status == "coded":
        return None, []
    for rule in candidate_bank_rules(db, bank_txn):
        reasons = _match_reason(rule, bank_txn)
        if reasons:
            return rule, reasons
    return None, []


def bank_rule_reason_text(reasons: list[str]) -> str | None:
    if not reasons:
        return None
    return ", ".join(reasons)


def bank_rule_payload(rule: BankRule, reasons: list[str] | None = None) -> dict:
    return {
        "id": rule.id,
        "name": rule.name,
        "priority": rule.priority,
        "bank_account_id": rule.bank_account_id,
        "target_account_id": rule.target_account_id,
        "target_account_name": rule.target_account.name if rule.target_account else None,
        "direction": rule.direction.value if hasattr(rule.direction, "value") else str(rule.direction),
        "reason": bank_rule_reason_text(reasons or []),
        "default_description": rule.default_description,
    }


def apply_bank_rule_suggestion(db: Session, bank_txn: BankTransaction, *, persist: bool) -> tuple[BankRule | None, list[str]]:
    rule, reasons = find_matching_bank_rule(db, bank_txn)
    if persist:
        bank_txn.suggested_rule_id = rule.id if rule else None
        bank_txn.suggested_account_id = rule.target_account_id if rule else None
        bank_txn.rule_match_reason = bank_rule_reason_text(reasons)
    return rule, reasons


def validate_bank_rule_target_account(db: Session, account_id: int) -> Account:
    account = db.query(Account).filter(Account.id == account_id, Account.is_active == True).first()
    if not account:
        raise ValueError("Target account not found")
    return account
