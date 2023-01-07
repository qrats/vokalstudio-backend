"""Payment records.

A payment is the studio's own record of a provider transaction; it is created
from a webhook and never edited afterwards, only superseded.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_choice, require_text
from src.domain.money.amount import Money
from src.domain.timeline.instant import coerce_instant

CREATED = "created"
COMPLETED = "completed"
DECLINED = "declined"
REFUNDED = "refunded"
PARTIALLY_REFUNDED = "partially_refunded"

STATUSES = (CREATED, COMPLETED, DECLINED, REFUNDED, PARTIALLY_REFUNDED)
SETTLED_STATUSES = (COMPLETED, PARTIALLY_REFUNDED)

DECLINE_REASONS = (
    "insufficient_funds",
    "card_expired",
    "card_declined",
    "instrument_declined",
    "currency_mismatch",
    "unknown",
)


class Payment:
    """One attempt to collect money for a subscription."""

    __slots__ = (
        "reference",
        "subscription_reference",
        "amount",
        "refunded",
        "status",
        "captured_at",
        "decline_reason",
    )

    def __init__(
        self,
        reference,
        subscription_reference,
        amount,
        captured_at,
        status=COMPLETED,
        refunded=None,
        decline_reason=None,
    ):
        self.reference = require_text(reference, "reference", max_length=64)
        self.subscription_reference = require_text(
            subscription_reference, "subscription_reference", max_length=64
        )
        if not isinstance(amount, Money):
            raise ValidationError("amount must be Money", field="amount")
        if amount.is_negative():
            raise ValidationError("amount must not be negative", field="amount")
        self.amount = amount
        self.captured_at = coerce_instant(captured_at, "captured_at")
        self.status = require_choice(status, "status", STATUSES)
        self.refunded = refunded if refunded is not None else Money.zero(amount.currency)
        if not isinstance(self.refunded, Money):
            raise ValidationError("refunded must be Money", field="refunded")
        if self.refunded.currency != amount.currency:
            raise ValidationError("refund currency mismatch", field="refunded")
        if self.refunded.is_negative() or self.refunded > amount:
            raise ValidationError("refunded is out of range", field="refunded")
        self.decline_reason = (
            require_choice(decline_reason, "decline_reason", DECLINE_REASONS)
            if decline_reason
            else None
        )
        if self.status == DECLINED and self.decline_reason is None:
            raise ValidationError(
                "a declined payment needs a reason", field="decline_reason"
            )
        if self.status != DECLINED and self.decline_reason is not None:
            raise ValidationError(
                "only a declined payment carries a reason", field="decline_reason"
            )

    @classmethod
    def declined(cls, reference, subscription_reference, amount, captured_at, reason):
        return cls(
            reference,
            subscription_reference,
            amount,
            captured_at,
            DECLINED,
            decline_reason=reason,
        )

    def net(self):
        """What the studio kept after refunds."""
        if self.status == DECLINED:
            return Money.zero(self.amount.currency)
        return self.amount.minus(self.refunded)

    def is_settled(self):
        return self.status in SETTLED_STATUSES

    def is_refundable(self):
        return self.is_settled() and self.refunded < self.amount

    def refund(self, amount=None):
        """Return a copy with ``amount`` (default: everything left) refunded."""
        if not self.is_refundable():
            raise ValidationError("payment cannot be refunded", field="status")
        wanted = amount if amount is not None else self.amount.minus(self.refunded)
        if not isinstance(wanted, Money):
            raise ValidationError("amount must be Money", field="amount")
        if wanted.is_negative() or wanted.is_zero():
            raise ValidationError("refund must be positive", field="amount")
        total = self.refunded.plus(wanted)
        if total > self.amount:
            raise ValidationError("refund exceeds the payment", field="amount")
        status = REFUNDED if total == self.amount else PARTIALLY_REFUNDED
        return Payment(
            self.reference,
            self.subscription_reference,
            self.amount,
            self.captured_at,
            status,
            total,
        )

    def to_dict(self):
        return {
            "reference": self.reference,
            "subscription_reference": self.subscription_reference,
            "amount": self.amount.to_dict(),
            "refunded": self.refunded.to_dict(),
            "status": self.status,
            "captured_at": self.captured_at.to_iso(),
            "decline_reason": self.decline_reason,
        }

    def __eq__(self, other):
        return isinstance(other, Payment) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("payment", self.reference))

    def __repr__(self):
        return "Payment({!r}, {})".format(self.reference, self.status)


def settled_total(payments, currency):
    """Net money collected across ``payments``."""
    running = Money.zero(currency)
    for payment in payments:
        if payment.is_settled():
            running = running.plus(payment.net())
    return running


def declines(payments):
    return tuple(payment for payment in payments if payment.status == DECLINED)


def last_settled(payments, default=None):
    settled = [payment for payment in payments if payment.is_settled()]
    if not settled:
        return default
    return sorted(settled, key=lambda payment: payment.captured_at.millis)[-1]
