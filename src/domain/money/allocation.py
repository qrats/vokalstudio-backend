"""Splitting money without losing a unit.

A 99.00 USD plan shared between three co-hosts is 33.00 each, but a 10.00 USD
plan shared between three is 3.34 / 3.33 / 3.33.  The largest-remainder method
below is the only place in the domain allowed to decide who gets the extra
minor unit, and it is deterministic: earlier entries win ties.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int, require_sequence
from src.domain.money.amount import Money


def split_evenly(amount, parts):
    """Split ``amount`` into ``parts`` shares that add back up exactly."""
    if not isinstance(amount, Money):
        raise ValidationError("amount must be Money", field="amount")
    count = require_int(parts, "parts", minimum=1)
    base, remainder = divmod(abs(amount.units), count)
    sign = -1 if amount.units < 0 else 1
    shares = []
    for index in range(count):
        units = base + (1 if index < remainder else 0)
        shares.append(Money(sign * units, amount.currency))
    return tuple(shares)


def allocate_by_weights(amount, weights):
    """Split ``amount`` in proportion to ``weights`` using largest remainder."""
    if not isinstance(amount, Money):
        raise ValidationError("amount must be Money", field="amount")
    values = require_sequence(weights, "weights", min_length=1)
    numbers = [require_int(weight, "weights", minimum=0) for weight in values]
    denominator = sum(numbers)
    if denominator == 0:
        raise ValidationError("weights must not all be zero", field="weights")
    sign = -1 if amount.units < 0 else 1
    magnitude = abs(amount.units)
    floors = []
    remainders = []
    for index, weight in enumerate(numbers):
        product = magnitude * weight
        share, rest = divmod(product, denominator)
        floors.append(share)
        remainders.append((rest, -index))
    leftover = magnitude - sum(floors)
    for _, negative_index in sorted(remainders, reverse=True)[:leftover]:
        floors[-negative_index] += 1
    return tuple(Money(sign * share, amount.currency) for share in floors)


def allocate_by_ratios(amount, ratios, scale=10000):
    """Like :func:`allocate_by_weights` but for fractional ratios."""
    values = require_sequence(ratios, "ratios", min_length=1)
    weights = []
    for ratio in values:
        number = float(ratio)
        if number < 0:
            raise ValidationError("ratios must not be negative", field="ratios")
        weights.append(int(round(number * scale)))
    return allocate_by_weights(amount, weights)


def prorate(amount, elapsed_days, total_days):
    """The share of ``amount`` earned after ``elapsed_days`` of a period."""
    if not isinstance(amount, Money):
        raise ValidationError("amount must be Money", field="amount")
    span = require_int(total_days, "total_days", minimum=1)
    used = require_int(elapsed_days, "elapsed_days", minimum=0)
    if used > span:
        raise ValidationError(
            "elapsed_days must not exceed total_days", field="elapsed_days"
        )
    if used == span:
        return Money(amount.units, amount.currency)
    return allocate_by_weights(amount, [used, span - used])[0]


def remaining_credit(amount, elapsed_days, total_days):
    """The unearned part of ``amount``; the complement of :func:`prorate`."""
    earned = prorate(amount, elapsed_days, total_days)
    return amount.minus(earned)


def reconcile(shares, expected):
    """Check that ``shares`` add up to ``expected`` and return the difference."""
    running = Money.zero(expected.currency)
    for share in shares:
        running = running.plus(share)
    return running.minus(expected)
