"""Rounding modes.

Proration and tax both have to turn a fraction of a minor unit into a whole
one; which way it goes is a business decision, so it is named rather than left
to Python's default.
"""

from src.domain.core.errors import ValidationError

HALF_UP = "half_up"
HALF_EVEN = "half_even"
DOWN = "down"
UP = "up"
CEILING = "ceiling"
FLOOR = "floor"

MODES = (HALF_UP, HALF_EVEN, DOWN, UP, CEILING, FLOOR)


def validate_mode(mode, field="mode"):
    if mode not in MODES:
        raise ValidationError(
            "{} must be one of {}".format(field, ", ".join(MODES)), field=field
        )
    return mode


def round_division(numerator, denominator, mode=HALF_UP):
    """Divide two integers and round the quotient to a whole number.

    ``HALF_UP`` rounds a tie away from zero, so ``-5/2`` becomes ``-3``;
    ``DOWN`` and ``UP`` are likewise relative to zero rather than to negative
    infinity, which is what ``FLOOR`` and ``CEILING`` are for.
    """
    validate_mode(mode)
    if denominator == 0:
        raise ValidationError("denominator must not be zero", field="denominator")
    if denominator < 0:
        numerator, denominator = -numerator, -denominator
    whole, remainder = divmod(numerator, denominator)
    if remainder == 0:
        return whole
    if mode == FLOOR:
        return whole
    if mode == CEILING:
        return whole + 1
    if mode == DOWN:
        return whole + 1 if numerator < 0 else whole
    if mode == UP:
        return whole if numerator < 0 else whole + 1
    twice = remainder * 2
    if twice > denominator:
        return whole + 1
    if twice < denominator:
        return whole
    if mode == HALF_UP:
        return whole + 1 if numerator > 0 else whole
    return whole + 1 if whole % 2 else whole


def apply_rate(units, rate, mode=HALF_UP, scale=1000000):
    """Multiply ``units`` by a fractional ``rate`` and round the result."""
    if not isinstance(units, int) or isinstance(units, bool):
        raise ValidationError("units must be an integer", field="units")
    scaled = int(round(float(rate) * scale))
    return round_division(units * scaled, scale, mode)
