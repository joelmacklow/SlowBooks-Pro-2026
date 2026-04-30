from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
import re

DEFAULT_PAYMENT_TERMS = [
    ("Net 15", "net:15"),
    ("Net 30", "net:30"),
    ("Net 45", "net:45"),
    ("Net 60", "net:60"),
    ("Due on Receipt", "days:0"),
]

DEFAULT_PAYMENT_TERMS_CONFIG = "\n".join(f"{label}|{rule}" for label, rule in DEFAULT_PAYMENT_TERMS)


def _infer_rule_from_label(label: str) -> str:
    candidate = (label or "").strip()
    match = re.fullmatch(r"net\s+(\d+)", candidate, flags=re.IGNORECASE)
    if match:
        return f"net:{int(match.group(1))}"
    if candidate.casefold() == "due on receipt":
        return "days:0"
    return "manual"


def parse_payment_terms_config(raw: str | None) -> list[dict[str, str]]:
    config_text = (raw or "").strip() or DEFAULT_PAYMENT_TERMS_CONFIG
    results: list[dict[str, str]] = []
    seen: set[str] = set()

    for line in config_text.splitlines():
        candidate = line.strip()
        if not candidate:
            continue

        if "|" in candidate:
            label, rule = [part.strip() for part in candidate.split("|", 1)]
        elif "=" in candidate:
            label, rule = [part.strip() for part in candidate.split("=", 1)]
        else:
            label = candidate
            rule = _infer_rule_from_label(candidate)

        if not label or label in seen:
            continue
        results.append({"label": label, "rule": rule or "manual"})
        seen.add(label)

    if results:
        return results

    return [{"label": label, "rule": rule} for label, rule in DEFAULT_PAYMENT_TERMS]


def payment_terms_labels(raw: str | None) -> list[str]:
    return [entry["label"] for entry in parse_payment_terms_config(raw)]


def resolve_due_date_for_terms(base_date: date, term_label: str | None, config: str | None) -> date:
    rule = None
    label = (term_label or "").strip()
    for entry in parse_payment_terms_config(config):
        if entry["label"] == label:
            rule = entry["rule"]
            break
    if not rule:
        rule = _infer_rule_from_label(label)
    return apply_due_date_rule(base_date, rule)


def apply_due_date_rule(base_date: date, rule: str | None) -> date:
    raw_rule = (rule or "").strip().lower()
    if raw_rule in ("manual", ""):
        return base_date + timedelta(days=30)
    if raw_rule == "receipt":
        return base_date
    if raw_rule.startswith("net:") or raw_rule.startswith("days:"):
        try:
            _, value = raw_rule.split(":", 1)
            return base_date + timedelta(days=int(value))
        except Exception:
            return base_date + timedelta(days=30)
    if raw_rule.startswith("next_month_day:"):
        try:
            _, value = raw_rule.split(":", 1)
            requested_day = int(value)
            year = base_date.year + (1 if base_date.month == 12 else 0)
            month = 1 if base_date.month == 12 else base_date.month + 1
            max_day = monthrange(year, month)[1]
            return date(year, month, min(requested_day, max_day))
        except Exception:
            return base_date + timedelta(days=30)
    return base_date + timedelta(days=30)
