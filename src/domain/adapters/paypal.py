"""Reading PayPal payloads.

The webhook bodies are nested and the money is a decimal string, so the two
conversions the rest of the domain needs are gathered here rather than repeated
in every resource.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_mapping, require_text
from src.domain.money.amount import Money

STATUS_MAP = {
    "APPROVAL_PENDING": "approval_pending",
    "APPROVED": "approved",
    "ACTIVE": "active",
    "SUSPENDED": "suspended",
    "CANCELLED": "cancelled",
    "EXPIRED": "expired",
}

EVENT_MAP = {
    "BILLING.SUBSCRIPTION.CREATED": "approval_pending",
    "BILLING.SUBSCRIPTION.ACTIVATED": "active",
    "BILLING.SUBSCRIPTION.UPDATED": None,
    "BILLING.SUBSCRIPTION.SUSPENDED": "suspended",
    "BILLING.SUBSCRIPTION.CANCELLED": "cancelled",
    "BILLING.SUBSCRIPTION.EXPIRED": "expired",
    "PAYMENT.SALE.COMPLETED": None,
    "PAYMENT.SALE.DENIED": None,
}


def dig(payload, *path, default=None):
    """Walk a nested payload without a chain of ``get`` calls."""
    current = payload
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def to_money(payload, field="amount"):
    """Turn ``{"value": "99.00", "currency_code": "USD"}`` into money."""
    body = require_mapping(payload, field, ["value"])
    currency = body.get("currency_code") or body.get("currency") or "USD"
    return Money.from_major(body["value"], currency)


def subscription_status(status, field="status"):
    text = require_text(status, field, max_length=40).upper()
    if text not in STATUS_MAP:
        raise ValidationError(
            "unknown PayPal status {}".format(text),
            field=field,
            details={"known": sorted(STATUS_MAP)},
        )
    return STATUS_MAP[text]


def event_state(event_type, field="event_type"):
    """The subscription state a webhook implies, or ``None``."""
    text = require_text(event_type, field, max_length=80).upper()
    if text not in EVENT_MAP:
        raise ValidationError(
            "unhandled event {}".format(text),
            field=field,
            details={"known": sorted(EVENT_MAP)},
        )
    return EVENT_MAP[text]


def is_known_event(event_type):
    return isinstance(event_type, str) and event_type.upper() in EVENT_MAP


def subscription_reference(payload):
    reference = dig(payload, "resource", "id") or payload.get("id")
    if not reference:
        raise ValidationError("payload has no subscription id", field="resource")
    return str(reference)


def payment_amount(payload):
    body = dig(payload, "resource", "amount") or dig(payload, "resource", "gross_amount")
    if body is None:
        raise ValidationError("payload has no amount", field="resource")
    return to_money(body)


def next_billing_date(payload):
    return dig(payload, "resource", "billing_info", "next_billing_time")


def failed_payments_count(payload):
    value = dig(payload, "resource", "billing_info", "failed_payments_count", default=0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
