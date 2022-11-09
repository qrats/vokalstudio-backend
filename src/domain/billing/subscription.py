"""The subscription state machine.

PayPal drives most of the transitions through webhooks, but the studio has to
decide what each one means locally -- in particular, a cancelled subscription
keeps serving until the end of the period it has already been paid for, which
is why ``CANCELLED`` and ``EXPIRED`` are separate states.
"""

from src.domain.core.errors import StateError, ValidationError
from src.domain.core.guards import require_choice, require_text
from src.domain.timeline.calendar import next_anniversary, parse_date

APPROVAL_PENDING = "approval_pending"
APPROVED = "approved"
ACTIVE = "active"
SUSPENDED = "suspended"
CANCELLED = "cancelled"
EXPIRED = "expired"

STATES = (APPROVAL_PENDING, APPROVED, ACTIVE, SUSPENDED, CANCELLED, EXPIRED)

TRANSITIONS = {
    APPROVAL_PENDING: (APPROVED, CANCELLED, EXPIRED),
    APPROVED: (ACTIVE, CANCELLED, EXPIRED),
    ACTIVE: (SUSPENDED, CANCELLED, EXPIRED),
    SUSPENDED: (ACTIVE, CANCELLED, EXPIRED),
    CANCELLED: (EXPIRED,),
    EXPIRED: (),
}

SERVING_STATES = (ACTIVE, SUSPENDED, CANCELLED)
BILLABLE_STATES = (ACTIVE,)


def can_transition(current, target):
    """Whether ``current`` may move to ``target``."""
    return require_choice(target, "target", STATES) in TRANSITIONS[
        require_choice(current, "current", STATES)
    ]


def transition(current, target):
    """Return ``target`` or raise :class:`StateError`."""
    if not can_transition(current, target):
        raise StateError(
            "cannot move a {} subscription to {}".format(current, target),
            current=current,
            attempted=target,
        )
    return target


class Subscription:
    """One customer's ongoing agreement to a plan."""

    __slots__ = (
        "reference",
        "user_id",
        "plan_code",
        "state",
        "started_on",
        "anchor_day",
        "cancelled_on",
        "period_end_on",
    )

    def __init__(
        self,
        reference,
        user_id,
        plan_code,
        started_on,
        state=APPROVAL_PENDING,
        cancelled_on=None,
        period_end_on=None,
    ):
        self.reference = require_text(reference, "reference", max_length=64)
        self.user_id = require_text(user_id, "user_id", max_length=64)
        self.plan_code = require_text(plan_code, "plan_code", max_length=64)
        self.started_on = parse_date(started_on, "started_on")
        self.state = require_choice(state, "state", STATES)
        self.anchor_day = self.started_on.day
        self.cancelled_on = (
            parse_date(cancelled_on, "cancelled_on") if cancelled_on else None
        )
        self.period_end_on = (
            parse_date(period_end_on, "period_end_on") if period_end_on else None
        )
        if self.cancelled_on and self.cancelled_on < self.started_on:
            raise ValidationError(
                "cancelled_on precedes started_on", field="cancelled_on"
            )

    def _copy(self, **changes):
        payload = {
            "reference": self.reference,
            "user_id": self.user_id,
            "plan_code": self.plan_code,
            "started_on": self.started_on,
            "state": self.state,
            "cancelled_on": self.cancelled_on,
            "period_end_on": self.period_end_on,
        }
        payload.update(changes)
        return Subscription(**payload)

    def moved_to(self, target):
        return self._copy(state=transition(self.state, target))

    def approve(self):
        return self.moved_to(APPROVED)

    def activate(self):
        return self.moved_to(ACTIVE)

    def suspend(self):
        return self.moved_to(SUSPENDED)

    def cancel(self, on, period_end_on=None):
        """Cancel; the customer keeps access until the period they paid for ends."""
        day = parse_date(on, "on")
        end = parse_date(period_end_on, "period_end_on") if period_end_on else (
            self.current_period_end(day)
        )
        return self._copy(
            state=transition(self.state, CANCELLED), cancelled_on=day, period_end_on=end
        )

    def expire(self, on=None):
        end = parse_date(on, "on") if on else self.period_end_on
        return self._copy(state=transition(self.state, EXPIRED), period_end_on=end)

    def current_period_end(self, on, months=1):
        """The next renewal date strictly after ``on``."""
        return next_anniversary(self.started_on, on, months)

    def is_serving(self, on=None):
        """Whether the account still has access."""
        if self.state not in SERVING_STATES:
            return False
        if self.state == CANCELLED:
            if self.period_end_on is None or on is None:
                return True
            return parse_date(on, "on") < self.period_end_on
        return True

    def is_billable(self):
        return self.state in BILLABLE_STATES

    def is_terminal(self):
        return self.state == EXPIRED

    def days_served(self, on):
        return (parse_date(on, "on") - self.started_on).days

    def to_dict(self):
        return {
            "reference": self.reference,
            "user_id": self.user_id,
            "plan_code": self.plan_code,
            "state": self.state,
            "started_on": self.started_on.isoformat(),
            "anchor_day": self.anchor_day,
            "cancelled_on": self.cancelled_on.isoformat() if self.cancelled_on else None,
            "period_end_on": (
                self.period_end_on.isoformat() if self.period_end_on else None
            ),
        }

    @classmethod
    def from_dict(cls, payload):
        return cls(
            payload["reference"],
            payload["user_id"],
            payload["plan_code"],
            payload["started_on"],
            payload.get("state", APPROVAL_PENDING),
            payload.get("cancelled_on"),
            payload.get("period_end_on"),
        )

    def __eq__(self, other):
        return isinstance(other, Subscription) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("subscription", self.reference))

    def __repr__(self):
        return "Subscription({!r}, {})".format(self.reference, self.state)
