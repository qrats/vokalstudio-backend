"""Tax computation.

Provider payloads describe tax either as a percentage applied on top of the
price or as a percentage already baked into it; both spellings have to produce
the same three numbers, so both live here.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_bool, require_number, require_text
from src.domain.money.amount import Money
from src.domain.money.rounding import HALF_UP, round_division


class TaxRate:
    """A named percentage, stored in basis points to stay exact."""

    __slots__ = ("name", "basis_points", "inclusive")

    def __init__(self, name, percent, inclusive=False):
        self.name = require_text(name, "name", max_length=60)
        percentage = require_number(percent, "percent", minimum=0, maximum=100)
        self.basis_points = int(round(percentage * 100))
        self.inclusive = require_bool(inclusive, "inclusive")

    @property
    def percent(self):
        return self.basis_points / 100.0

    def tax_on(self, amount, mode=HALF_UP):
        """The tax component for ``amount``."""
        if not isinstance(amount, Money):
            raise ValidationError("amount must be Money", field="amount")
        if self.inclusive:
            units = round_division(
                amount.units * self.basis_points, 10000 + self.basis_points, mode
            )
        else:
            units = round_division(amount.units * self.basis_points, 10000, mode)
        return Money(units, amount.currency)

    def net_of(self, amount, mode=HALF_UP):
        """The amount excluding tax."""
        if self.inclusive:
            return amount.minus(self.tax_on(amount, mode))
        return Money(amount.units, amount.currency)

    def gross_of(self, amount, mode=HALF_UP):
        """The amount including tax."""
        if self.inclusive:
            return Money(amount.units, amount.currency)
        return amount.plus(self.tax_on(amount, mode))

    def breakdown(self, amount, mode=HALF_UP):
        """Return ``{net, tax, gross}`` for ``amount``."""
        tax = self.tax_on(amount, mode)
        return {
            "net": self.net_of(amount, mode),
            "tax": tax,
            "gross": self.gross_of(amount, mode),
        }

    def to_dict(self):
        return {
            "name": self.name,
            "percent": self.percent,
            "inclusive": self.inclusive,
        }

    def __eq__(self, other):
        return (
            isinstance(other, TaxRate)
            and other.name == self.name
            and other.basis_points == self.basis_points
            and other.inclusive == self.inclusive
        )

    def __hash__(self):
        return hash(("tax", self.name, self.basis_points, self.inclusive))

    def __repr__(self):
        return "TaxRate({!r}, {}%)".format(self.name, self.percent)


ZERO_RATE = TaxRate("zero", 0)


def combined(rates, amount, mode=HALF_UP):
    """Apply several exclusive rates to the same net amount."""
    tax = Money.zero(amount.currency)
    for rate in rates:
        if rate.inclusive:
            raise ValidationError(
                "inclusive rates cannot be combined", field="rates"
            )
        tax = tax.plus(rate.tax_on(amount, mode))
    return {"net": amount, "tax": tax, "gross": amount.plus(tax)}
