from src.domain.billing import dunning as mod
from src.domain.billing.payment import Payment
from src.domain.money.amount import Money
from tests.support import DomainTestCase


class PolicyConstructionTests(DomainTestCase):
    def test_defaults(self):
        policy = mod.DunningPolicy()
        self.assertEqual((3, 5, 7), policy.offsets)
        self.assertEqual(14, policy.grace_days)

    def test_max_attempts(self):
        self.assertEqual(4, mod.DunningPolicy().max_attempts)

    def test_no_retries(self):
        self.assertEqual(1, mod.DunningPolicy([]).max_attempts)

    def test_offsets_must_increase(self):
        self.assertField("offsets", mod.DunningPolicy, [5, 3])

    def test_offsets_must_be_distinct(self):
        self.assertField("offsets", mod.DunningPolicy, [3, 3])

    def test_offsets_must_be_positive(self):
        self.assertField("offsets", mod.DunningPolicy, [0, 3])

    def test_grace_days_cannot_be_negative(self):
        self.assertField("grace_days", mod.DunningPolicy, [3], -1)

    def test_to_dict(self):
        self.assertEqual(
            {"offsets": [3, 5, 7], "grace_days": 14}, mod.DunningPolicy().to_dict()
        )

    def test_equality(self):
        self.assertEqual(mod.DunningPolicy(), mod.DunningPolicy())

    def test_inequality(self):
        self.assertNotEqual(mod.DunningPolicy(), mod.DunningPolicy([1]))

    def test_hashable(self):
        self.assertEqual(1, len({mod.DunningPolicy(), mod.DunningPolicy()}))

    def test_repr(self):
        self.assertIn("grace", repr(mod.DunningPolicy()))


class ScheduleTests(DomainTestCase):
    def setUp(self):
        self.policy = mod.DunningPolicy()

    def test_retry_schedule(self):
        days = [day.isoformat() for day in self.policy.retry_schedule("2021-05-01")]
        self.assertEqual(["2021-05-04", "2021-05-06", "2021-05-08"], days)

    def test_no_retries(self):
        self.assertEqual((), mod.DunningPolicy([]).retry_schedule("2021-05-01"))

    def test_next_retry_after_one_attempt(self):
        self.assertEqual(
            "2021-05-04", self.policy.next_retry("2021-05-01", 1).isoformat()
        )

    def test_next_retry_after_three_attempts(self):
        self.assertEqual(
            "2021-05-08", self.policy.next_retry("2021-05-01", 3).isoformat()
        )

    def test_no_retry_left(self):
        self.assertIsNone(self.policy.next_retry("2021-05-01", 4))

    def test_attempts_start_at_one(self):
        self.assertField("attempts", self.policy.next_retry, "2021-05-01", 0)

    def test_give_up_day(self):
        self.assertEqual("2021-05-15", self.policy.give_up_on("2021-05-01").isoformat())


class SuspensionTests(DomainTestCase):
    def setUp(self):
        self.policy = mod.DunningPolicy()

    def test_not_yet(self):
        self.assertFalse(self.policy.should_suspend("2021-05-01", "2021-05-05", 1))

    def test_after_the_grace_period(self):
        self.assertTrue(self.policy.should_suspend("2021-05-01", "2021-05-15", 1))

    def test_on_the_grace_boundary(self):
        self.assertTrue(self.policy.should_suspend("2021-05-01", "2021-05-15", 1))

    def test_one_day_before_the_boundary(self):
        self.assertFalse(self.policy.should_suspend("2021-05-01", "2021-05-14", 1))

    def test_attempts_exhausted(self):
        self.assertTrue(self.policy.should_suspend("2021-05-01", "2021-05-02", 4))

    def test_hard_decline_suspends_at_once(self):
        self.assertTrue(
            self.policy.should_suspend("2021-05-01", "2021-05-02", 1, "card_expired")
        )

    def test_soft_decline_does_not(self):
        self.assertFalse(
            self.policy.should_suspend(
                "2021-05-01", "2021-05-02", 1, "insufficient_funds"
            )
        )

    def test_negative_attempts(self):
        self.assertField(
            "attempts", self.policy.should_suspend, "2021-05-01", "2021-05-02", -1
        )


class RecoverableTests(DomainTestCase):
    def test_soft_decline(self):
        self.assertTrue(mod.is_recoverable("insufficient_funds"))

    def test_hard_decline(self):
        self.assertFalse(mod.is_recoverable("card_expired"))

    def test_currency_mismatch_is_hard(self):
        self.assertFalse(mod.is_recoverable("currency_mismatch"))

    def test_unknown_reason_is_worth_retrying(self):
        self.assertTrue(mod.is_recoverable("unknown"))


class AttemptsForTests(DomainTestCase):
    def setUp(self):
        self.first = Payment.declined(
            "P1", "I-1", Money(9900), "2021-05-01T00:00:00Z", "insufficient_funds"
        )
        self.second = Payment.declined(
            "P2", "I-1", Money(9900), "2021-05-04T00:00:00Z", "insufficient_funds"
        )
        self.other = Payment.declined(
            "P3", "I-2", Money(9900), "2021-05-02T00:00:00Z", "unknown"
        )
        self.good = Payment("P4", "I-1", Money(9900), "2021-05-06T00:00:00Z")

    def test_only_the_named_subscription(self):
        found = mod.attempts_for([self.first, self.other], "I-1")
        self.assertEqual((self.first,), found)

    def test_only_declines(self):
        found = mod.attempts_for([self.first, self.good], "I-1")
        self.assertEqual((self.first,), found)

    def test_sorted_oldest_first(self):
        found = mod.attempts_for([self.second, self.first], "I-1")
        self.assertEqual((self.first, self.second), found)

    def test_nothing_matches(self):
        self.assertEqual((), mod.attempts_for([self.good], "I-9"))

    def test_default_policy_is_shared(self):
        self.assertEqual(mod.DunningPolicy(), mod.DEFAULT_POLICY)
