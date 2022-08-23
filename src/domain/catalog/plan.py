"""Billing plans.

A plan is a product plus a price, a cycle and the feature grants that come with
it.  Trials are modelled as a leading cycle with a zero price so that the cycle
schedule in :mod:`src.domain.billing.cycle` does not need a special case.
"""

from src.domain.catalog.feature import lookup
from src.domain.catalog.product import Product
from src.domain.core.errors import ValidationError
from src.domain.core.guards import (
    require_bool,
    require_choice,
    require_int,
    require_mapping,
    require_text,
)
from src.domain.core.text import slugify
from src.domain.money.amount import Money

INTERVALS = {"day": 1, "week": 7, "month": 30, "year": 365}
STATUSES = ("created", "active", "inactive")


class BillingCycle:
    """One tenure in a plan: a price, an interval and a repeat count."""

    __slots__ = ("price", "interval", "frequency", "cycles", "trial")

    def __init__(self, price, interval="month", frequency=1, cycles=0, trial=False):
        if not isinstance(price, Money):
            raise ValidationError("price must be Money", field="price")
        if price.is_negative():
            raise ValidationError("price must not be negative", field="price")
        self.price = price
        self.interval = require_choice(interval, "interval", tuple(INTERVALS))
        self.frequency = require_int(frequency, "frequency", minimum=1, maximum=365)
        self.cycles = require_int(cycles, "cycles", minimum=0)
        self.trial = require_bool(trial, "trial")
        if self.trial and self.cycles == 0:
            raise ValidationError("a trial must be bounded", field="cycles")

    @property
    def is_infinite(self):
        return self.cycles == 0

    def months_per_cycle(self):
        """Approximate length in months, used when comparing plans."""
        days = INTERVALS[self.interval] * self.frequency
        return max(1, round(days / 30))

    def to_dict(self):
        return {
            "price": self.price.to_dict(),
            "interval": self.interval,
            "frequency": self.frequency,
            "cycles": self.cycles,
            "trial": self.trial,
        }

    def __eq__(self, other):
        return isinstance(other, BillingCycle) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("cycle", self.price.units, self.interval, self.frequency))

    def __repr__(self):
        return "BillingCycle({} / {} {})".format(
            self.price.to_major(), self.frequency, self.interval
        )


class Plan:
    """A named, priced offer built on a :class:`Product`."""

    __slots__ = ("code", "name", "product_code", "cycles", "grants", "status", "quantity_supported")

    def __init__(
        self,
        name,
        product,
        cycles,
        grants=None,
        code=None,
        status="active",
        quantity_supported=False,
    ):
        self.name = require_text(name, "name", max_length=127)
        self.product_code = product.code if isinstance(product, Product) else slugify(
            product, field="product"
        )
        materialised = tuple(cycles)
        if not materialised:
            raise ValidationError("a plan needs at least one cycle", field="cycles")
        if sum(1 for cycle in materialised if cycle.is_infinite) > 1:
            raise ValidationError(
                "only one cycle may repeat forever", field="cycles"
            )
        for index, cycle in enumerate(materialised[:-1]):
            if cycle.is_infinite:
                raise ValidationError(
                    "an endless cycle must come last", field="cycles"
                )
            if index and cycle.trial:
                raise ValidationError("trials must come first", field="cycles")
        self.cycles = materialised
        self.code = slugify(code or name, field="code")
        self.status = require_choice(status, "status", STATUSES)
        self.quantity_supported = require_bool(quantity_supported, "quantity_supported")
        self.grants = self._check_grants(grants or {})

    @staticmethod
    def _check_grants(grants):
        checked = {}
        for key, value in require_mapping(grants, "grants").items():
            feature = lookup(key, "grants")
            checked[feature.key] = feature.coerce(value)
        return checked

    @property
    def currency(self):
        return self.cycles[0].price.currency

    @property
    def regular_cycle(self):
        """The cycle a subscriber settles into once any trial is over."""
        for cycle in reversed(self.cycles):
            if not cycle.trial:
                return cycle
        return self.cycles[-1]

    @property
    def price(self):
        return self.regular_cycle.price

    def has_trial(self):
        return any(cycle.trial for cycle in self.cycles)

    def trial_cycles(self):
        return tuple(cycle for cycle in self.cycles if cycle.trial)

    def is_active(self):
        return self.status == "active"

    def grant_for(self, key):
        """The value this plan grants for ``key``, falling back to the default."""
        feature = lookup(key)
        return self.grants.get(feature.key, feature.default)

    def monthly_equivalent(self):
        """The regular price expressed per month, for plan comparison."""
        cycle = self.regular_cycle
        return cycle.price.divided_by(cycle.months_per_cycle())

    def with_status(self, status):
        return Plan(
            self.name,
            self.product_code,
            self.cycles,
            self.grants,
            self.code,
            status,
            self.quantity_supported,
        )

    def to_dict(self):
        return {
            "code": self.code,
            "name": self.name,
            "product_code": self.product_code,
            "status": self.status,
            "quantity_supported": self.quantity_supported,
            "cycles": [cycle.to_dict() for cycle in self.cycles],
            "grants": dict(self.grants),
        }

    def __eq__(self, other):
        return isinstance(other, Plan) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("plan", self.code))

    def __repr__(self):
        return "Plan({!r}, {})".format(self.code, self.price.to_major())


def cheapest(plans, default=None):
    """The active plan with the lowest monthly equivalent price."""
    active = [plan for plan in plans if plan.is_active()]
    if not active:
        return default
    return sorted(active, key=lambda plan: (plan.monthly_equivalent().units, plan.code))[0]


def upgrades_from(plans, current):
    """Active plans that cost more per month than ``current``."""
    threshold = current.monthly_equivalent().units
    return tuple(
        plan
        for plan in sorted(plans, key=lambda item: item.monthly_equivalent().units)
        if plan.is_active() and plan.monthly_equivalent().units > threshold
    )
