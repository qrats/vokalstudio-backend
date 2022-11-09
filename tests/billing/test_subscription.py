from src.domain.billing import subscription as mod
from tests.support import DomainTestCase


def build(**overrides):
    payload = {
        "reference": "I-YK3SWC2YXKYA",
        "user_id": "u-1",
        "plan_code": "pro",
        "started_on": "2021-01-31",
    }
    payload.update(overrides)
    return mod.Subscription(**payload)


class TransitionTableTests(DomainTestCase):
    def test_every_state_has_a_row(self):
        self.assertEqual(set(mod.STATES), set(mod.TRANSITIONS))

    def test_expired_is_terminal(self):
        self.assertEqual((), mod.TRANSITIONS[mod.EXPIRED])

    def test_targets_are_known_states(self):
        for targets in mod.TRANSITIONS.values():
            for target in targets:
                self.assertIn(target, mod.STATES)

    def test_can_transition(self):
        self.assertTrue(mod.can_transition(mod.ACTIVE, mod.SUSPENDED))

    def test_cannot_transition(self):
        self.assertFalse(mod.can_transition(mod.CANCELLED, mod.ACTIVE))

    def test_unknown_current_state(self):
        self.assertField("current", mod.can_transition, "paused", mod.ACTIVE)

    def test_unknown_target_state(self):
        self.assertField("target", mod.can_transition, mod.ACTIVE, "paused")

    def test_transition_returns_the_target(self):
        self.assertEqual(mod.ACTIVE, mod.transition(mod.APPROVED, mod.ACTIVE))

    def test_transition_raises(self):
        error = self.assertRaisesCode(
            "invalid_state", mod.transition, mod.EXPIRED, mod.ACTIVE
        )
        self.assertEqual(mod.EXPIRED, error.current)
        self.assertEqual(mod.ACTIVE, error.attempted)


class ConstructionTests(DomainTestCase):
    def test_defaults_to_approval_pending(self):
        self.assertEqual(mod.APPROVAL_PENDING, build().state)

    def test_anchor_day_comes_from_the_start(self):
        self.assertEqual(31, build().anchor_day)

    def test_empty_reference(self):
        self.assertField("reference", build, reference="")

    def test_empty_user(self):
        self.assertField("user_id", build, user_id="")

    def test_bad_start_date(self):
        self.assertField("started_on", build, started_on="31/01/2021")

    def test_unknown_state(self):
        self.assertField("state", build, state="paused")

    def test_cancellation_before_start(self):
        self.assertField(
            "cancelled_on", build, state=mod.CANCELLED, cancelled_on="2020-12-01"
        )

    def test_no_cancellation_by_default(self):
        self.assertIsNone(build().cancelled_on)


class LifecycleTests(DomainTestCase):
    def test_approve(self):
        self.assertEqual(mod.APPROVED, build().approve().state)

    def test_activate(self):
        self.assertEqual(mod.ACTIVE, build().approve().activate().state)

    def test_activate_from_pending_is_rejected(self):
        self.assertRaisesCode("invalid_state", build().activate)

    def test_suspend(self):
        active = build().approve().activate()
        self.assertEqual(mod.SUSPENDED, active.suspend().state)

    def test_resume_from_suspended(self):
        suspended = build().approve().activate().suspend()
        self.assertEqual(mod.ACTIVE, suspended.activate().state)

    def test_transitions_return_copies(self):
        original = build()
        original.approve()
        self.assertEqual(mod.APPROVAL_PENDING, original.state)

    def test_moved_to_is_generic(self):
        self.assertEqual(mod.CANCELLED, build().moved_to(mod.CANCELLED).state)


class CancellationTests(DomainTestCase):
    def setUp(self):
        self.active = build().approve().activate()

    def test_cancel_records_the_day(self):
        cancelled = self.active.cancel("2021-03-05")
        self.assertEqual("2021-03-05", cancelled.cancelled_on.isoformat())

    def test_cancel_computes_the_period_end(self):
        cancelled = self.active.cancel("2021-03-05")
        self.assertEqual("2021-03-31", cancelled.period_end_on.isoformat())

    def test_cancel_accepts_an_explicit_end(self):
        cancelled = self.active.cancel("2021-03-05", "2021-04-15")
        self.assertEqual("2021-04-15", cancelled.period_end_on.isoformat())

    def test_cancel_from_expired_is_rejected(self):
        expired = self.active.cancel("2021-03-05").expire()
        self.assertRaisesCode("invalid_state", expired.cancel, "2021-04-01")

    def test_expire_keeps_the_period_end(self):
        cancelled = self.active.cancel("2021-03-05")
        self.assertEqual(cancelled.period_end_on, cancelled.expire().period_end_on)

    def test_expire_can_set_a_day(self):
        expired = self.active.cancel("2021-03-05").expire("2021-04-01")
        self.assertEqual("2021-04-01", expired.period_end_on.isoformat())


class PeriodTests(DomainTestCase):
    def test_next_renewal_clamps_short_months(self):
        self.assertEqual(
            "2021-02-28", build().current_period_end("2021-02-05").isoformat()
        )

    def test_next_renewal_is_strictly_after(self):
        self.assertEqual(
            "2021-04-30", build().current_period_end("2021-03-31").isoformat()
        )

    def test_yearly_period(self):
        self.assertEqual(
            "2022-01-31", build().current_period_end("2021-06-01", 12).isoformat()
        )

    def test_days_served(self):
        self.assertEqual(28, build().days_served("2021-02-28"))


class ServingTests(DomainTestCase):
    def test_active_is_serving(self):
        self.assertTrue(build().approve().activate().is_serving())

    def test_pending_is_not_serving(self):
        self.assertFalse(build().is_serving())

    def test_suspended_still_serves(self):
        self.assertTrue(build().approve().activate().suspend().is_serving())

    def test_cancelled_serves_until_the_period_end(self):
        cancelled = build().approve().activate().cancel("2021-03-05")
        self.assertTrue(cancelled.is_serving("2021-03-30"))

    def test_cancelled_stops_at_the_period_end(self):
        cancelled = build().approve().activate().cancel("2021-03-05")
        self.assertFalse(cancelled.is_serving("2021-03-31"))

    def test_cancelled_serves_when_no_day_is_given(self):
        cancelled = build().approve().activate().cancel("2021-03-05")
        self.assertTrue(cancelled.is_serving())

    def test_expired_never_serves(self):
        expired = build().approve().activate().cancel("2021-03-05").expire()
        self.assertFalse(expired.is_serving("2021-03-06"))

    def test_only_active_is_billable(self):
        self.assertTrue(build().approve().activate().is_billable())

    def test_suspended_is_not_billable(self):
        self.assertFalse(build().approve().activate().suspend().is_billable())

    def test_is_terminal(self):
        expired = build().approve().activate().cancel("2021-03-05").expire()
        self.assertTrue(expired.is_terminal())

    def test_active_is_not_terminal(self):
        self.assertFalse(build().approve().activate().is_terminal())


class SerialisationTests(DomainTestCase):
    def test_to_dict(self):
        payload = build().to_dict()
        self.assertEqual("2021-01-31", payload["started_on"])
        self.assertIsNone(payload["cancelled_on"])
        self.assertEqual(31, payload["anchor_day"])

    def test_round_trip(self):
        cancelled = build().approve().activate().cancel("2021-03-05")
        self.assertRoundTrips(mod.Subscription.from_dict, cancelled)

    def test_equality(self):
        self.assertEqual(build(), build())

    def test_inequality(self):
        self.assertNotEqual(build(), build().approve())

    def test_hashable(self):
        self.assertEqual(1, len({build(), build()}))

    def test_repr(self):
        self.assertIn("approval_pending", repr(build()))
