from src.domain.catalog import plan as mod
from src.domain.catalog.product import Product
from src.domain.money.amount import Money
from tests.support import DomainTestCase

PRODUCT = Product("PRO", "Everything the studio offers.")


def cycle(major="99.00", **overrides):
    payload = {"price": Money.from_major(major)}
    payload.update(overrides)
    return mod.BillingCycle(**payload)


def plan(**overrides):
    payload = {"name": "PRO", "product": PRODUCT, "cycles": [cycle()]}
    payload.update(overrides)
    return mod.Plan(**payload)


class BillingCycleTests(DomainTestCase):
    def test_defaults(self):
        one = cycle()
        self.assertEqual("month", one.interval)
        self.assertEqual(1, one.frequency)
        self.assertTrue(one.is_infinite)
        self.assertFalse(one.trial)

    def test_price_must_be_money(self):
        self.assertField("price", mod.BillingCycle, "99.00")

    def test_negative_price(self):
        self.assertField("price", mod.BillingCycle, Money(-1))

    def test_zero_price_is_allowed(self):
        self.assertTrue(mod.BillingCycle(Money(0)).price.is_zero())

    def test_unknown_interval(self):
        self.assertField("interval", cycle, interval="fortnight")

    def test_frequency_floor(self):
        self.assertField("frequency", cycle, frequency=0)

    def test_frequency_ceiling(self):
        self.assertField("frequency", cycle, frequency=366)

    def test_negative_cycles(self):
        self.assertField("cycles", cycle, cycles=-1)

    def test_trial_must_be_bounded(self):
        self.assertField("cycles", cycle, trial=True)

    def test_bounded_trial(self):
        self.assertTrue(cycle("0.00", cycles=1, trial=True).trial)

    def test_months_per_cycle_monthly(self):
        self.assertEqual(1, cycle().months_per_cycle())

    def test_months_per_cycle_yearly(self):
        self.assertEqual(12, cycle(interval="year").months_per_cycle())

    def test_months_per_cycle_weekly_is_at_least_one(self):
        self.assertEqual(1, cycle(interval="week").months_per_cycle())

    def test_months_per_cycle_quarterly(self):
        self.assertEqual(3, cycle(frequency=3).months_per_cycle())

    def test_to_dict(self):
        payload = cycle().to_dict()
        self.assertEqual("month", payload["interval"])
        self.assertEqual(9900, payload["price"]["units"])

    def test_equality(self):
        self.assertEqual(cycle(), cycle())

    def test_hashable(self):
        self.assertEqual(1, len({cycle(), cycle()}))

    def test_repr(self):
        self.assertIn("99.00", repr(cycle()))


class PlanConstructionTests(DomainTestCase):
    def test_code_from_name(self):
        self.assertEqual("pro", plan().code)

    def test_product_code_from_product(self):
        self.assertEqual("pro", plan().product_code)

    def test_product_code_from_text(self):
        self.assertEqual("studio", plan(product="Studio").product_code)

    def test_no_cycles(self):
        self.assertField("cycles", plan, cycles=[])

    def test_two_endless_cycles(self):
        self.assertField("cycles", plan, cycles=[cycle(), cycle()])

    def test_endless_cycle_must_come_last(self):
        self.assertField(
            "cycles", plan, cycles=[cycle(), cycle("50.00", cycles=3)]
        )

    def test_trial_must_come_first(self):
        trial = cycle("0.00", cycles=1, trial=True)
        self.assertField(
            "cycles", plan, cycles=[cycle("50.00", cycles=2), trial, cycle()]
        )

    def test_unknown_status(self):
        self.assertField("status", plan, status="retired")

    def test_grants_are_validated(self):
        self.assertField("grants", plan, grants={"no.such": 1})

    def test_grants_are_coerced(self):
        self.assertEqual(5, plan(grants={"streaming.targets": "5"}).grants["streaming.targets"])


class PlanBehaviourTests(DomainTestCase):
    def test_currency(self):
        self.assertEqual("USD", plan().currency)

    def test_price_is_the_regular_cycle(self):
        trial = cycle("0.00", cycles=1, trial=True)
        self.assertEqual(Money.from_major("99.00"), plan(cycles=[trial, cycle()]).price)

    def test_has_trial(self):
        trial = cycle("0.00", cycles=1, trial=True)
        self.assertTrue(plan(cycles=[trial, cycle()]).has_trial())

    def test_no_trial(self):
        self.assertFalse(plan().has_trial())

    def test_trial_cycles(self):
        trial = cycle("0.00", cycles=1, trial=True)
        self.assertEqual((trial,), plan(cycles=[trial, cycle()]).trial_cycles())

    def test_is_active(self):
        self.assertTrue(plan().is_active())

    def test_inactive(self):
        self.assertFalse(plan(status="inactive").is_active())

    def test_grant_for_falls_back_to_the_default(self):
        self.assertEqual(1, plan().grant_for("streaming.targets"))

    def test_grant_for_uses_the_plan(self):
        self.assertEqual(9, plan(grants={"streaming.targets": 9}).grant_for("streaming.targets"))

    def test_monthly_equivalent_for_a_yearly_plan(self):
        yearly = plan(cycles=[cycle("1200.00", interval="year")])
        self.assertEqual(Money.from_major("100.00"), yearly.monthly_equivalent())

    def test_with_status_returns_a_copy(self):
        original = plan()
        changed = original.with_status("inactive")
        self.assertTrue(original.is_active())
        self.assertFalse(changed.is_active())

    def test_with_status_keeps_grants(self):
        original = plan(grants={"streaming.targets": 4})
        self.assertEqual(4, original.with_status("inactive").grants["streaming.targets"])


class PlanSerialisationTests(DomainTestCase):
    def test_to_dict(self):
        payload = plan().to_dict()
        self.assertEqual("pro", payload["code"])
        self.assertEqual(1, len(payload["cycles"]))

    def test_equality(self):
        self.assertEqual(plan(), plan())

    def test_inequality(self):
        self.assertNotEqual(plan(), plan(status="inactive"))

    def test_hashable(self):
        self.assertEqual(1, len({plan(), plan()}))

    def test_repr(self):
        self.assertIn("pro", repr(plan()))


class ComparisonTests(DomainTestCase):
    def setUp(self):
        self.basic = plan(name="BASIC", cycles=[cycle("29.00")])
        self.pro = plan(name="PRO", cycles=[cycle("99.00")])
        self.retired = plan(name="OLD", cycles=[cycle("9.00")], status="inactive")

    def test_cheapest(self):
        self.assertEqual(self.basic, mod.cheapest([self.pro, self.basic]))

    def test_cheapest_ignores_inactive(self):
        self.assertEqual(self.basic, mod.cheapest([self.retired, self.basic]))

    def test_cheapest_of_nothing(self):
        self.assertIsNone(mod.cheapest([]))

    def test_cheapest_default(self):
        self.assertEqual("x", mod.cheapest([self.retired], "x"))

    def test_upgrades(self):
        self.assertEqual((self.pro,), mod.upgrades_from([self.basic, self.pro], self.basic))

    def test_no_upgrades_from_the_top(self):
        self.assertEqual((), mod.upgrades_from([self.basic, self.pro], self.pro))

    def test_upgrades_exclude_inactive(self):
        expensive = plan(name="OLDPRO", cycles=[cycle("199.00")], status="inactive")
        self.assertEqual(
            (self.pro,), mod.upgrades_from([self.pro, expensive], self.basic)
        )
