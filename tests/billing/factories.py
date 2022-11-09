"""Builders shared by the billing tests."""

from src.domain.catalog.plan import BillingCycle, Plan
from src.domain.catalog.product import Product
from src.domain.money.amount import Money

PRODUCT = Product("PRO", "Everything the studio offers.")


def make_plan(name="PRO", major="99.00", cycles=None, grants=None, **kwargs):
    tenures = cycles or [BillingCycle(Money.from_major(major))]
    return Plan(name, PRODUCT, tenures, grants, **kwargs)


def trial_plan(trial_major="0.00", major="99.00", trial_cycles=1):
    return make_plan(
        cycles=[
            BillingCycle(Money.from_major(trial_major), cycles=trial_cycles, trial=True),
            BillingCycle(Money.from_major(major)),
        ]
    )
