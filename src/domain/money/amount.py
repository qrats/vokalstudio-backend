"""Money as whole minor units.

Every price in the domain is an integer count of minor units plus a currency
code.  Floats never enter: a plan priced at 99.00 USD is ``Money(9900, "USD")``.
"""

import re

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int
from src.domain.money.currency import (
    DEFAULT_CURRENCY,
    exponent,
    minor_units_per_major,
    normalize_currency,
    symbol,
)
from src.domain.money.rounding import HALF_UP, apply_rate, round_division

_DECIMAL = re.compile(r"^-?\d+(\.\d+)?$")


class Money:
    """An exact amount in one currency."""

    __slots__ = ("units", "currency")

    def __init__(self, units, currency=DEFAULT_CURRENCY):
        self.units = require_int(units, "units")
        self.currency = normalize_currency(currency)

    @classmethod
    def zero(cls, currency=DEFAULT_CURRENCY):
        return cls(0, currency)

    @classmethod
    def from_major(cls, value, currency=DEFAULT_CURRENCY):
        """Build from a decimal string such as ``"99.00"``."""
        code = normalize_currency(currency)
        text = str(value).strip()
        if not _DECIMAL.match(text):
            raise ValidationError("amount must be a decimal number", field="amount")
        negative = text.startswith("-")
        whole, _, fraction = text.lstrip("-").partition(".")
        places = exponent(code)
        if len(fraction) > places:
            raise ValidationError(
                "{} allows at most {} decimal places".format(code, places),
                field="amount",
            )
        units = int(whole or "0", 10) * minor_units_per_major(code)
        if places:
            units += int(fraction.ljust(places, "0") or "0", 10)
        return cls(-units if negative else units, code)

    def to_major(self):
        """Return the decimal string this amount prints as."""
        places = exponent(self.currency)
        sign = "-" if self.units < 0 else ""
        magnitude = abs(self.units)
        if not places:
            return "{}{}".format(sign, magnitude)
        divisor = minor_units_per_major(self.currency)
        return "{}{}.{:0{}d}".format(
            sign, magnitude // divisor, magnitude % divisor, places
        )

    def format(self):
        return "{}{}".format(symbol(self.currency), self.to_major())

    def _check(self, other):
        if not isinstance(other, Money):
            raise ValidationError("value must be Money", field="value")
        if other.currency != self.currency:
            raise ValidationError(
                "cannot mix {} and {}".format(self.currency, other.currency),
                field="currency",
            )
        return other

    def plus(self, other):
        return Money(self.units + self._check(other).units, self.currency)

    def minus(self, other):
        return Money(self.units - self._check(other).units, self.currency)

    def times(self, factor):
        return Money(self.units * require_int(factor, "factor"), self.currency)

    def scaled_by(self, rate, mode=HALF_UP):
        """Multiply by a fractional rate, e.g. a 0.2 tax rate."""
        return Money(apply_rate(self.units, rate, mode), self.currency)

    def divided_by(self, divisor, mode=HALF_UP):
        return Money(
            round_division(self.units, require_int(divisor, "divisor"), mode),
            self.currency,
        )

    def negated(self):
        return Money(-self.units, self.currency)

    def absolute(self):
        return Money(abs(self.units), self.currency)

    def is_zero(self):
        return self.units == 0

    def is_positive(self):
        return self.units > 0

    def is_negative(self):
        return self.units < 0

    def to_dict(self):
        return {
            "units": self.units,
            "currency": self.currency,
            "display": self.to_major(),
        }

    def __eq__(self, other):
        return (
            isinstance(other, Money)
            and other.units == self.units
            and other.currency == self.currency
        )

    def __lt__(self, other):
        return self.units < self._check(other).units

    def __le__(self, other):
        return self.units <= self._check(other).units

    def __gt__(self, other):
        return self.units > self._check(other).units

    def __ge__(self, other):
        return self.units >= self._check(other).units

    def __hash__(self):
        return hash(("money", self.units, self.currency))

    def __repr__(self):
        return "Money({} {})".format(self.to_major(), self.currency)


def total(amounts, currency=DEFAULT_CURRENCY):
    """Sum ``amounts``; every entry must share one currency."""
    code = normalize_currency(currency)
    running = Money.zero(code)
    for amount in amounts:
        running = running.plus(amount)
    return running


def maximum(amounts, default=None):
    ordered = sorted(amounts, key=lambda amount: amount.units)
    return ordered[-1] if ordered else default


def minimum(amounts, default=None):
    ordered = sorted(amounts, key=lambda amount: amount.units)
    return ordered[0] if ordered else default
