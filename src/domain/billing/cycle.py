"""Turning a plan into the dates it will actually bill on."""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int
from src.domain.money.amount import Money
from src.domain.timeline.calendar import add_days, add_months, parse_date

DAYS_PER_INTERVAL = {"day": 1, "week": 7}


class Charge:
    """One scheduled charge produced by a plan."""

    __slots__ = ("due_on", "amount", "sequence", "trial")

    def __init__(self, due_on, amount, sequence, trial=False):
        self.due_on = parse_date(due_on, "due_on")
        if not isinstance(amount, Money):
            raise ValidationError("amount must be Money", field="amount")
        self.amount = amount
        self.sequence = require_int(sequence, "sequence", minimum=1)
        self.trial = bool(trial)

    def to_dict(self):
        return {
            "due_on": self.due_on.isoformat(),
            "amount": self.amount.to_dict(),
            "sequence": self.sequence,
            "trial": self.trial,
        }

    def __eq__(self, other):
        return isinstance(other, Charge) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("charge", self.due_on, self.amount.units, self.sequence))

    def __repr__(self):
        return "Charge({}, {})".format(self.due_on.isoformat(), self.amount.to_major())


def _advance(day, interval, frequency):
    if interval in DAYS_PER_INTERVAL:
        return add_days(day, DAYS_PER_INTERVAL[interval] * frequency)
    if interval == "month":
        return add_months(day, frequency)
    return add_months(day, 12 * frequency)


def schedule(plan, start_on, count):
    """The first ``count`` charges a plan produces from ``start_on``."""
    total = require_int(count, "count", minimum=0)
    cursor = parse_date(start_on, "start_on")
    charges = []
    sequence = 1
    for cycle in plan.cycles:
        repeats = cycle.cycles if not cycle.is_infinite else total
        for _ in range(repeats):
            if len(charges) >= total:
                return tuple(charges)
            charges.append(Charge(cursor, cycle.price, sequence, cycle.trial))
            cursor = _advance(cursor, cycle.interval, cycle.frequency)
            sequence += 1
    return tuple(charges)


def next_charge(plan, start_on, after):
    """The first charge falling strictly after ``after``, if any."""
    boundary = parse_date(after, "after")
    for charge in schedule(plan, start_on, 240):
        if charge.due_on > boundary:
            return charge
    return None


def total_over(plan, start_on, count):
    """What the customer pays across the first ``count`` charges."""
    charges = schedule(plan, start_on, count)
    running = Money.zero(plan.currency)
    for charge in charges:
        running = running.plus(charge.amount)
    return running


def trial_ends_on(plan, start_on):
    """The day the last trial charge's period ends, or ``None``."""
    if not plan.has_trial():
        return None
    cursor = parse_date(start_on, "start_on")
    for cycle in plan.cycles:
        if not cycle.trial:
            break
        for _ in range(cycle.cycles):
            cursor = _advance(cursor, cycle.interval, cycle.frequency)
    return cursor


def period_length_days(plan, start_on):
    """Length in days of the first regular period, used for proration."""
    cycle = plan.regular_cycle
    start = parse_date(start_on, "start_on")
    return (_advance(start, cycle.interval, cycle.frequency) - start).days
