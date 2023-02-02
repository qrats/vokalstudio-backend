"""Invoices.

The studio does not issue invoices to the payment provider; it renders them for
the customer out of what was actually charged, so an invoice is a pure
projection of lines onto totals.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int, require_text
from src.domain.money.amount import Money
from src.domain.money.taxes import ZERO_RATE
from src.domain.timeline.calendar import parse_date


class LineItem:
    """One priced row on an invoice."""

    __slots__ = ("description", "unit_price", "quantity", "tax_rate")

    def __init__(self, description, unit_price, quantity=1, tax_rate=None):
        self.description = require_text(description, "description", max_length=200)
        if not isinstance(unit_price, Money):
            raise ValidationError("unit_price must be Money", field="unit_price")
        self.unit_price = unit_price
        self.quantity = require_int(quantity, "quantity", minimum=1)
        self.tax_rate = tax_rate or ZERO_RATE

    @property
    def net(self):
        return self.tax_rate.net_of(self.unit_price).times(self.quantity)

    @property
    def tax(self):
        return self.tax_rate.tax_on(self.unit_price).times(self.quantity)

    @property
    def gross(self):
        return self.net.plus(self.tax)

    def to_dict(self):
        return {
            "description": self.description,
            "unit_price": self.unit_price.to_dict(),
            "quantity": self.quantity,
            "tax": self.tax_rate.to_dict(),
            "net": self.net.to_dict(),
            "gross": self.gross.to_dict(),
        }

    def __eq__(self, other):
        return isinstance(other, LineItem) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("line", self.description, self.unit_price.units, self.quantity))

    def __repr__(self):
        return "LineItem({!r} x{})".format(self.description, self.quantity)


class Invoice:
    """A dated set of line items for one customer."""

    __slots__ = ("number", "user_id", "issued_on", "lines", "currency")

    def __init__(self, number, user_id, issued_on, lines):
        self.number = require_text(number, "number", max_length=40)
        self.user_id = require_text(user_id, "user_id", max_length=64)
        self.issued_on = parse_date(issued_on, "issued_on")
        materialised = tuple(lines)
        if not materialised:
            raise ValidationError("an invoice needs at least one line", field="lines")
        currencies = {line.unit_price.currency for line in materialised}
        if len(currencies) > 1:
            raise ValidationError("an invoice is single currency", field="lines")
        self.lines = materialised
        self.currency = currencies.pop()

    def _sum(self, attribute):
        running = Money.zero(self.currency)
        for line in self.lines:
            running = running.plus(getattr(line, attribute))
        return running

    @property
    def net(self):
        return self._sum("net")

    @property
    def tax(self):
        return self._sum("tax")

    @property
    def total(self):
        return self._sum("gross")

    def with_line(self, line):
        return Invoice(self.number, self.user_id, self.issued_on, self.lines + (line,))

    def tax_summary(self):
        """Tax collected per rate name, for the accounting export."""
        summary = {}
        for line in self.lines:
            if line.tax.is_zero():
                continue
            name = line.tax_rate.name
            summary[name] = summary.get(name, Money.zero(self.currency)).plus(line.tax)
        return summary

    def to_dict(self):
        return {
            "number": self.number,
            "user_id": self.user_id,
            "issued_on": self.issued_on.isoformat(),
            "currency": self.currency,
            "lines": [line.to_dict() for line in self.lines],
            "net": self.net.to_dict(),
            "tax": self.tax.to_dict(),
            "total": self.total.to_dict(),
        }

    def __eq__(self, other):
        return isinstance(other, Invoice) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("invoice", self.number))

    def __repr__(self):
        return "Invoice({!r}, {})".format(self.number, self.total.to_major())
