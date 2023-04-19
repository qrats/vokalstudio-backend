"""An account balance built from entries rather than stored.

Every charge, payment, refund and credit becomes a signed entry; the balance is
their sum.  Nothing is ever edited, so a disputed figure can always be traced
back to the entries that produced it.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_choice, require_text
from src.domain.money.amount import Money
from src.domain.timeline.instant import coerce_instant

CHARGE = "charge"
PAYMENT = "payment"
REFUND = "refund"
CREDIT = "credit"
ADJUSTMENT = "adjustment"

KINDS = (CHARGE, PAYMENT, REFUND, CREDIT, ADJUSTMENT)
DEBITS = (CHARGE, REFUND)


class Entry:
    """One signed movement on an account."""

    __slots__ = ("kind", "amount", "occurred_at", "note", "reference")

    def __init__(self, kind, amount, occurred_at, note=None, reference=None):
        self.kind = require_choice(kind, "kind", KINDS)
        if not isinstance(amount, Money):
            raise ValidationError("amount must be Money", field="amount")
        if amount.is_negative():
            raise ValidationError("amount must not be negative", field="amount")
        if amount.is_zero() and self.kind != ADJUSTMENT:
            raise ValidationError("amount must be positive", field="amount")
        self.amount = amount
        self.occurred_at = coerce_instant(occurred_at, "occurred_at")
        self.note = require_text(note, "note", max_length=200) if note else None
        self.reference = (
            require_text(reference, "reference", max_length=64) if reference else None
        )

    @property
    def signed_units(self):
        """Positive when the customer owes more."""
        return self.amount.units if self.kind in DEBITS else -self.amount.units

    def to_dict(self):
        return {
            "kind": self.kind,
            "amount": self.amount.to_dict(),
            "occurred_at": self.occurred_at.to_iso(),
            "note": self.note,
            "reference": self.reference,
            "signed_units": self.signed_units,
        }

    def __eq__(self, other):
        return isinstance(other, Entry) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("entry", self.kind, self.amount.units, self.occurred_at.millis))

    def __repr__(self):
        return "Entry({}, {})".format(self.kind, self.amount.to_major())


class Ledger:
    """The entries for one account, in the order they happened."""

    __slots__ = ("currency", "entries")

    def __init__(self, currency, entries=()):
        self.currency = Money.zero(currency).currency
        materialised = tuple(entries)
        for entry in materialised:
            if entry.amount.currency != self.currency:
                raise ValidationError("entry currency mismatch", field="entries")
        self.entries = tuple(
            sorted(materialised, key=lambda entry: entry.occurred_at.millis)
        )

    def with_entry(self, entry):
        return Ledger(self.currency, self.entries + (entry,))

    def balance(self, until=None):
        """What the customer owes; negative means they are in credit."""
        boundary = coerce_instant(until, "until") if until is not None else None
        units = 0
        for entry in self.entries:
            if boundary is not None and entry.occurred_at > boundary:
                continue
            units += entry.signed_units
        return Money(units, self.currency)

    def of_kind(self, kind):
        wanted = require_choice(kind, "kind", KINDS)
        return tuple(entry for entry in self.entries if entry.kind == wanted)

    def total_of(self, kind):
        running = Money.zero(self.currency)
        for entry in self.of_kind(kind):
            running = running.plus(entry.amount)
        return running

    def is_settled(self):
        return self.balance().is_zero()

    def is_in_arrears(self):
        return self.balance().is_positive()

    def statement(self):
        """Entries with the running balance after each one."""
        rows = []
        units = 0
        for entry in self.entries:
            units += entry.signed_units
            row = entry.to_dict()
            row["balance"] = Money(units, self.currency).to_dict()
            rows.append(row)
        return tuple(rows)

    def to_dict(self):
        return {
            "currency": self.currency,
            "balance": self.balance().to_dict(),
            "entries": [entry.to_dict() for entry in self.entries],
        }

    def __eq__(self, other):
        return isinstance(other, Ledger) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("ledger", self.currency, self.entries))

    def __repr__(self):
        return "Ledger({}, {})".format(self.currency, self.balance().to_major())
