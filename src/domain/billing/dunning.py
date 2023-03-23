"""What happens after a payment is declined.

The provider retries on its own schedule, but the studio has to decide when to
suspend the account and when to give up; both are pure functions of the attempt
history so they can be replayed against past data.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int, require_sequence
from src.domain.timeline.calendar import add_days, parse_date

RETRY_OFFSETS = (3, 5, 7)
GRACE_DAYS = 14

HARD_DECLINES = ("card_expired", "currency_mismatch")


class DunningPolicy:
    """How many times to retry a failed payment and when to give up."""

    __slots__ = ("offsets", "grace_days")

    def __init__(self, offsets=RETRY_OFFSETS, grace_days=GRACE_DAYS):
        values = require_sequence(offsets, "offsets", min_length=0)
        numbers = [require_int(offset, "offsets", minimum=1) for offset in values]
        if numbers != sorted(numbers):
            raise ValidationError("offsets must increase", field="offsets")
        if len(set(numbers)) != len(numbers):
            raise ValidationError("offsets must be distinct", field="offsets")
        self.offsets = tuple(numbers)
        self.grace_days = require_int(grace_days, "grace_days", minimum=0)

    @property
    def max_attempts(self):
        return len(self.offsets) + 1

    def retry_schedule(self, failed_on):
        """The days the provider should retry after a failure."""
        day = parse_date(failed_on, "failed_on")
        return tuple(add_days(day, offset) for offset in self.offsets)

    def next_retry(self, failed_on, attempts):
        """The next retry date, or ``None`` once the attempts are spent."""
        count = require_int(attempts, "attempts", minimum=1)
        if count > len(self.offsets):
            return None
        return add_days(parse_date(failed_on, "failed_on"), self.offsets[count - 1])

    def give_up_on(self, failed_on):
        return add_days(parse_date(failed_on, "failed_on"), self.grace_days)

    def should_suspend(self, failed_on, on, attempts, reason=None):
        """Whether the subscription should be suspended by ``on``."""
        if reason in HARD_DECLINES:
            return True
        if require_int(attempts, "attempts", minimum=0) >= self.max_attempts:
            return True
        return parse_date(on, "on") >= self.give_up_on(failed_on)

    def to_dict(self):
        return {"offsets": list(self.offsets), "grace_days": self.grace_days}

    def __eq__(self, other):
        return (
            isinstance(other, DunningPolicy)
            and other.offsets == self.offsets
            and other.grace_days == self.grace_days
        )

    def __hash__(self):
        return hash(("dunning", self.offsets, self.grace_days))

    def __repr__(self):
        return "DunningPolicy({}, grace={})".format(list(self.offsets), self.grace_days)


DEFAULT_POLICY = DunningPolicy()


def attempts_for(payments, subscription_reference):
    """Declined payments for one subscription, oldest first."""
    matching = [
        payment
        for payment in payments
        if payment.subscription_reference == subscription_reference
        and payment.status == "declined"
    ]
    return tuple(sorted(matching, key=lambda payment: payment.captured_at.millis))


def is_recoverable(reason):
    """Whether retrying a decline could plausibly succeed."""
    return reason not in HARD_DECLINES
