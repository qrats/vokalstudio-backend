from src.domain.billing import cycle as mod
from src.domain.catalog.plan import BillingCycle
from src.domain.money.amount import Money
from tests.billing.factories import make_plan, trial_plan
from tests.support import DomainTestCase


class ChargeTests(DomainTestCase):
    def test_fields(self):
        charge = mod.Charge("2021-05-01", Money.from_major("99.00"), 1)
        self.assertEqual("2021-05-01", charge.due_on.isoformat())
        self.assertEqual(1, charge.sequence)
        self.assertFalse(charge.trial)

    def test_amount_must_be_money(self):
        self.assertField("amount", mod.Charge, "2021-05-01", "99.00", 1)

    def test_sequence_starts_at_one(self):
        self.assertField("sequence", mod.Charge, "2021-05-01", Money(1), 0)

    def test_bad_date(self):
        self.assertField("due_on", mod.Charge, "01/05/2021", Money(1), 1)

    def test_to_dict(self):
        payload = mod.Charge("2021-05-01", Money(9900), 2, True).to_dict()
        self.assertEqual(2, payload["sequence"])
        self.assertTrue(payload["trial"])

    def test_equality(self):
        one = mod.Charge("2021-05-01", Money(1), 1)
        self.assertEqual(one, mod.Charge("2021-05-01", Money(1), 1))

    def test_hashable(self):
        one = mod.Charge("2021-05-01", Money(1), 1)
        self.assertEqual(1, len({one, mod.Charge("2021-05-01", Money(1), 1)}))

    def test_repr(self):
        self.assertIn("2021-05-01", repr(mod.Charge("2021-05-01", Money(1), 1)))


class ScheduleTests(DomainTestCase):
    def test_monthly_plan(self):
        charges = mod.schedule(make_plan(), "2021-01-31", 3)
        self.assertEqual(
            ["2021-01-31", "2021-02-28", "2021-03-28"],
            [charge.due_on.isoformat() for charge in charges],
        )

    def test_sequences_increment(self):
        charges = mod.schedule(make_plan(), "2021-05-01", 3)
        self.assertEqual([1, 2, 3], [charge.sequence for charge in charges])

    def test_zero_count(self):
        self.assertEqual((), mod.schedule(make_plan(), "2021-05-01", 0))

    def test_trial_comes_first(self):
        charges = mod.schedule(trial_plan(), "2021-05-01", 3)
        self.assertTrue(charges[0].trial)
        self.assertFalse(charges[1].trial)

    def test_trial_price(self):
        charges = mod.schedule(trial_plan(), "2021-05-01", 2)
        self.assertTrue(charges[0].amount.is_zero())
        self.assertEqual(Money.from_major("99.00"), charges[1].amount)

    def test_two_trial_cycles(self):
        charges = mod.schedule(trial_plan(trial_cycles=2), "2021-05-01", 3)
        self.assertEqual([True, True, False], [charge.trial for charge in charges])

    def test_weekly_interval(self):
        plan = make_plan(cycles=[BillingCycle(Money(100), "week")])
        charges = mod.schedule(plan, "2021-05-01", 2)
        self.assertEqual("2021-05-08", charges[1].due_on.isoformat())

    def test_daily_interval(self):
        plan = make_plan(cycles=[BillingCycle(Money(100), "day", 10)])
        charges = mod.schedule(plan, "2021-05-01", 2)
        self.assertEqual("2021-05-11", charges[1].due_on.isoformat())

    def test_yearly_interval(self):
        plan = make_plan(cycles=[BillingCycle(Money(100), "year")])
        charges = mod.schedule(plan, "2021-05-01", 2)
        self.assertEqual("2022-05-01", charges[1].due_on.isoformat())

    def test_bounded_plan_stops_early(self):
        plan = make_plan(cycles=[BillingCycle(Money(100), cycles=2)])
        self.assertEqual(2, len(mod.schedule(plan, "2021-05-01", 9)))

    def test_negative_count(self):
        self.assertField("count", mod.schedule, make_plan(), "2021-05-01", -1)


class NextChargeTests(DomainTestCase):
    def test_finds_the_next_one(self):
        charge = mod.next_charge(make_plan(), "2021-01-31", "2021-02-01")
        self.assertEqual("2021-02-28", charge.due_on.isoformat())

    def test_boundary_is_exclusive(self):
        charge = mod.next_charge(make_plan(), "2021-01-31", "2021-01-31")
        self.assertEqual("2021-02-28", charge.due_on.isoformat())

    def test_none_once_a_bounded_plan_ends(self):
        plan = make_plan(cycles=[BillingCycle(Money(100), cycles=1)])
        self.assertIsNone(mod.next_charge(plan, "2021-05-01", "2021-06-01"))


class TotalTests(DomainTestCase):
    def test_three_months(self):
        self.assertEqual(
            Money.from_major("297.00"), mod.total_over(make_plan(), "2021-05-01", 3)
        )

    def test_trial_is_free(self):
        self.assertEqual(
            Money.from_major("99.00"), mod.total_over(trial_plan(), "2021-05-01", 2)
        )

    def test_zero_charges(self):
        self.assertTrue(mod.total_over(make_plan(), "2021-05-01", 0).is_zero())


class TrialEndTests(DomainTestCase):
    def test_no_trial(self):
        self.assertIsNone(mod.trial_ends_on(make_plan(), "2021-05-01"))

    def test_one_month_trial(self):
        self.assertEqual(
            "2021-06-01", mod.trial_ends_on(trial_plan(), "2021-05-01").isoformat()
        )

    def test_two_month_trial(self):
        self.assertEqual(
            "2021-07-01",
            mod.trial_ends_on(trial_plan(trial_cycles=2), "2021-05-01").isoformat(),
        )


class PeriodLengthTests(DomainTestCase):
    def test_january_is_thirty_one_days(self):
        self.assertEqual(31, mod.period_length_days(make_plan(), "2021-01-01"))

    def test_february_is_shorter(self):
        self.assertEqual(28, mod.period_length_days(make_plan(), "2021-02-01"))

    def test_yearly_plan(self):
        plan = make_plan(cycles=[BillingCycle(Money(100), "year")])
        self.assertEqual(365, mod.period_length_days(plan, "2021-01-01"))

    def test_ignores_the_trial(self):
        self.assertEqual(31, mod.period_length_days(trial_plan(), "2021-01-01"))
