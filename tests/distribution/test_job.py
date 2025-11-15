from src.domain.distribution import job as mod
from tests.support import DomainTestCase

WHEN = "2021-05-01T10:00:00Z"


def build(**overrides):
    payload = {"episode_reference": "ep-1", "destination": "podbean"}
    payload.update(overrides)
    return mod.UploadJob(**payload)


class ConstructionTests(DomainTestCase):
    def test_defaults(self):
        job = build()
        self.assertEqual(mod.PENDING, job.state)
        self.assertEqual(0, job.attempts)
        self.assertIsNone(job.last_failure)

    def test_destination_is_normalised(self):
        self.assertEqual("podbean", build(destination="Podbean").destination)

    def test_unknown_destination(self):
        self.assertField("destination", build, destination="anchor")

    def test_unknown_state(self):
        self.assertField("state", build, state="queued")

    def test_negative_attempts(self):
        self.assertField("attempts", build, attempts=-1)

    def test_failed_needs_a_reason(self):
        self.assertField("last_failure", build, state=mod.FAILED)

    def test_succeeded_needs_an_external_id(self):
        self.assertField("external_id", build, state=mod.SUCCEEDED)

    def test_succeeded_with_an_id(self):
        job = build(state=mod.SUCCEEDED, external_id="pb-99")
        self.assertEqual("pb-99", job.external_id)

    def test_unknown_failure_reason(self):
        self.assertField("last_failure", build, state=mod.FAILED, last_failure="hiccup")

    def test_reference_is_stable(self):
        self.assertEqual(build().reference, build().reference)

    def test_reference_depends_on_the_destination(self):
        self.assertNotEqual(build().reference, build(destination="spotify").reference)


class LifecycleTests(DomainTestCase):
    def test_start_counts_the_attempt(self):
        self.assertEqual(1, build().start().attempts)

    def test_start_sets_running(self):
        self.assertEqual(mod.RUNNING, build().start().state)

    def test_start_records_the_time(self):
        self.assertEqual(WHEN, build().start(WHEN).updated_at.to_iso())

    def test_succeed(self):
        job = build().start().succeed("pb-99")
        self.assertEqual(mod.SUCCEEDED, job.state)
        self.assertEqual("pb-99", job.external_id)

    def test_succeed_clears_the_failure(self):
        job = build().start().fail("timeout").requeue().start().succeed("pb-99")
        self.assertIsNone(job.last_failure)

    def test_fail(self):
        job = build().start().fail("timeout")
        self.assertEqual(mod.FAILED, job.state)
        self.assertEqual("timeout", job.last_failure)

    def test_fail_keeps_the_attempt_count(self):
        self.assertEqual(1, build().start().fail("timeout").attempts)

    def test_requeue(self):
        self.assertEqual(mod.PENDING, build().start().fail("timeout").requeue().state)

    def test_second_attempt_increments(self):
        job = build().start().fail("timeout").requeue().start()
        self.assertEqual(2, job.attempts)

    def test_abandon_from_pending(self):
        self.assertEqual(mod.ABANDONED, build().abandon().state)

    def test_abandon_from_failed(self):
        job = build().start().fail("rejected").abandon()
        self.assertEqual(mod.ABANDONED, job.state)

    def test_cannot_succeed_from_pending(self):
        self.assertRaisesCode("invalid_state", build().succeed, "pb-99")

    def test_cannot_abandon_a_running_job(self):
        self.assertRaisesCode("invalid_state", build().start().abandon)

    def test_succeeded_is_terminal(self):
        job = build().start().succeed("pb-99")
        self.assertRaisesCode("invalid_state", job.requeue)

    def test_transitions_return_copies(self):
        job = build()
        job.start()
        self.assertEqual(0, job.attempts)

    def test_transition_table_targets_are_known(self):
        for targets in mod.TRANSITIONS.values():
            for target in targets:
                self.assertIn(target, mod.STATES)


class RetryTests(DomainTestCase):
    def test_delay_after_a_transient_failure(self):
        self.assertEqual(30, build().start().fail("timeout").next_delay_seconds())

    def test_delay_grows(self):
        job = build().start().fail("timeout").requeue().start().fail("timeout")
        self.assertEqual(60, job.next_delay_seconds())

    def test_no_delay_for_a_permanent_failure(self):
        self.assertIsNone(build().start().fail("rejected").next_delay_seconds())

    def test_no_delay_when_not_failed(self):
        self.assertIsNone(build().start().next_delay_seconds())

    def test_custom_budget_stops_earlier(self):
        job = build().start().fail("timeout")
        self.assertIsNone(job.next_delay_seconds(max_attempts=1))

    def test_is_retryable(self):
        self.assertTrue(build().start().fail("timeout").is_retryable())

    def test_is_not_retryable(self):
        self.assertFalse(build().start().fail("duplicate").is_retryable())

    def test_is_finished(self):
        self.assertTrue(build().start().succeed("pb-99").is_finished())

    def test_pending_is_not_finished(self):
        self.assertFalse(build().is_finished())


class SerialisationTests(DomainTestCase):
    def test_to_dict(self):
        payload = build().start(WHEN).to_dict()
        self.assertEqual("podbean", payload["destination"])
        self.assertEqual(1, payload["attempts"])
        self.assertEqual(WHEN, payload["updated_at"])

    def test_equality(self):
        self.assertEqual(build(), build())

    def test_inequality(self):
        self.assertNotEqual(build(), build().start())

    def test_hashable(self):
        self.assertEqual(1, len({build(), build()}))

    def test_repr(self):
        self.assertIn("podbean", repr(build()))


class CollectionTests(DomainTestCase):
    def setUp(self):
        self.pending = build()
        self.done = build(destination="spotify").start().succeed("sp-1")
        self.failed = build(destination="apple").start().fail("timeout")
        self.dead = build(destination="youtube").start().fail("rejected")

    def test_outstanding(self):
        found = mod.outstanding([self.pending, self.done, self.failed])
        self.assertEqual((self.pending, self.failed), found)

    def test_retryable(self):
        found = mod.retryable([self.failed, self.dead, self.done])
        self.assertEqual((self.failed,), found)

    def test_retryable_with_a_budget(self):
        self.assertEqual((), mod.retryable([self.failed], max_attempts=1))

    def test_by_destination(self):
        self.assertEqual((self.done,), mod.by_destination([self.pending, self.done], "spotify"))

    def test_by_destination_normalises(self):
        self.assertEqual((self.done,), mod.by_destination([self.done], "Spotify"))

    def test_summarise(self):
        counts = mod.summarise([self.pending, self.done, self.failed])
        self.assertEqual(1, counts[mod.PENDING])
        self.assertEqual(1, counts[mod.SUCCEEDED])
        self.assertEqual(0, counts[mod.RUNNING])

    def test_summarise_covers_every_state(self):
        self.assertEqual(set(mod.STATES), set(mod.summarise([])))
