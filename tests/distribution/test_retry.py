from src.domain.distribution import retry as mod
from tests.support import DomainTestCase


class FailureTests(DomainTestCase):
    def test_known_transient(self):
        self.assertEqual("timeout", mod.validate_failure("timeout"))

    def test_known_permanent(self):
        self.assertEqual("rejected", mod.validate_failure("rejected"))

    def test_unknown(self):
        error = self.assertRaisesCode("validation_failed", mod.validate_failure, "hiccup")
        self.assertIn("timeout", error.details["known"])

    def test_field_name(self):
        self.assertField("last_failure", mod.validate_failure, "hiccup", "last_failure")

    def test_is_transient(self):
        self.assertTrue(mod.is_transient("rate_limited"))

    def test_is_not_transient(self):
        self.assertFalse(mod.is_transient("file_too_large"))

    def test_the_two_sets_do_not_overlap(self):
        self.assertEqual(set(), set(mod.TRANSIENT) & set(mod.PERMANENT))

    def test_failures_is_the_union(self):
        self.assertEqual(
            len(mod.TRANSIENT) + len(mod.PERMANENT), len(set(mod.FAILURES))
        )


class DelayTests(DomainTestCase):
    def test_first_attempt(self):
        self.assertEqual(30, mod.delay_seconds(1))

    def test_doubles(self):
        self.assertEqual(60, mod.delay_seconds(2))
        self.assertEqual(120, mod.delay_seconds(3))

    def test_capped(self):
        self.assertEqual(mod.MAX_DELAY_SECONDS, mod.delay_seconds(20))

    def test_custom_base(self):
        self.assertEqual(10, mod.delay_seconds(1, base=10))

    def test_custom_ceiling(self):
        self.assertEqual(45, mod.delay_seconds(5, ceiling=45))

    def test_attempt_starts_at_one(self):
        self.assertField("attempt", mod.delay_seconds, 0)

    def test_base_must_be_positive(self):
        self.assertField("base", mod.delay_seconds, 1, 0)


class ShouldRetryTests(DomainTestCase):
    def test_transient_within_the_budget(self):
        self.assertTrue(mod.should_retry("timeout", 1))

    def test_transient_at_the_budget(self):
        self.assertFalse(mod.should_retry("timeout", 5))

    def test_permanent_never_retries(self):
        self.assertFalse(mod.should_retry("rejected", 1))

    def test_custom_budget(self):
        self.assertFalse(mod.should_retry("timeout", 2, max_attempts=2))

    def test_unknown_reason(self):
        self.assertField("reason", mod.should_retry, "hiccup", 1)

    def test_attempt_must_be_positive(self):
        self.assertField("attempt", mod.should_retry, "timeout", 0)


class ScheduleTests(DomainTestCase):
    def test_returns_a_delay(self):
        self.assertEqual(30, mod.schedule("timeout", 1))

    def test_grows_with_the_attempt(self):
        self.assertEqual(120, mod.schedule("timeout", 3))

    def test_none_when_exhausted(self):
        self.assertIsNone(mod.schedule("timeout", 5))

    def test_none_for_a_permanent_failure(self):
        self.assertIsNone(mod.schedule("unauthorised", 1))

    def test_custom_budget(self):
        self.assertIsNone(mod.schedule("timeout", 3, max_attempts=3))


class TotalWaitTests(DomainTestCase):
    def test_default_budget(self):
        self.assertEqual(30 + 60 + 120 + 240, mod.total_wait_seconds())

    def test_single_attempt(self):
        self.assertEqual(0, mod.total_wait_seconds(1))

    def test_two_attempts(self):
        self.assertEqual(30, mod.total_wait_seconds(2))

    def test_zero_is_rejected(self):
        self.assertField("max_attempts", mod.total_wait_seconds, 0)
