from src.domain.streaming import session as mod
from src.domain.timeline.instant import Instant
from src.domain.timeline.interval import Interval
from tests.support import DomainTestCase

OPENED = "2021-05-01T10:00:00Z"


def build(**overrides):
    payload = {"user_id": "u-1", "title": "Drive time", "opened_at": OPENED}
    payload.update(overrides)
    return mod.LiveSession(**payload)


def span(start, end):
    return Interval(Instant.parse(start), Instant.parse(end))


class ConstructionTests(DomainTestCase):
    def test_defaults_to_scheduled(self):
        self.assertEqual(mod.SCHEDULED, build().state)

    def test_no_connections(self):
        self.assertEqual((), build().connections)

    def test_empty_title(self):
        self.assertField("title", build, title="")

    def test_unknown_state(self):
        self.assertField("state", build, state="paused")

    def test_connections_must_be_intervals(self):
        self.assertField("connections", build, connections=[(1, 2)])

    def test_connection_before_the_session(self):
        early = span("2021-05-01T09:00:00Z", "2021-05-01T09:30:00Z")
        self.assertField("connections", build, connections=[early])

    def test_connections_are_sorted(self):
        later = span("2021-05-01T11:00:00Z", "2021-05-01T11:30:00Z")
        earlier = span(OPENED, "2021-05-01T10:30:00Z")
        session = build(state=mod.LIVE, connections=[later, earlier])
        self.assertEqual(earlier, session.connections[0])

    def test_reference_is_stable(self):
        self.assertEqual(build().reference, build().reference)

    def test_reference_depends_on_the_open_time(self):
        self.assertNotEqual(build().reference, build(opened_at="2021-05-01T10:00:01Z").reference)


class LifecycleTests(DomainTestCase):
    def test_go_live(self):
        session = build().go_live(OPENED, "2021-05-01T10:30:00Z")
        self.assertEqual(mod.LIVE, session.state)
        self.assertEqual(1, len(session.connections))

    def test_go_live_returns_a_copy(self):
        session = build()
        session.go_live(OPENED, "2021-05-01T10:30:00Z")
        self.assertEqual(mod.SCHEDULED, session.state)

    def test_cannot_go_live_twice_without_interrupting(self):
        session = build().go_live(OPENED, "2021-05-01T10:30:00Z")
        self.assertRaisesCode(
            "invalid_state", session.go_live, "2021-05-01T10:35:00Z", "2021-05-01T11:00:00Z"
        )

    def test_reconnect_after_an_interruption(self):
        session = build().go_live(OPENED, "2021-05-01T10:30:00Z").interrupt()
        session = session.go_live("2021-05-01T10:35:00Z", "2021-05-01T11:00:00Z")
        self.assertEqual(2, len(session.connections))

    def test_zero_length_connection(self):
        self.assertField("until", build().go_live, OPENED, OPENED)

    def test_connection_before_the_session_is_rejected(self):
        self.assertField(
            "at", build().go_live, "2021-05-01T09:00:00Z", "2021-05-01T09:30:00Z"
        )

    def test_end(self):
        session = build().go_live(OPENED, "2021-05-01T10:30:00Z").end()
        self.assertEqual(mod.ENDED, session.state)

    def test_abandon_a_scheduled_session(self):
        self.assertEqual(mod.ABANDONED, build().abandon().state)

    def test_cannot_abandon_a_live_session(self):
        session = build().go_live(OPENED, "2021-05-01T10:30:00Z")
        self.assertRaisesCode("invalid_state", session.abandon)

    def test_cannot_end_a_scheduled_session(self):
        self.assertRaisesCode("invalid_state", build().end)

    def test_ended_is_terminal(self):
        session = build().go_live(OPENED, "2021-05-01T10:30:00Z").end()
        self.assertRaisesCode("invalid_state", session.interrupt)

    def test_is_finished(self):
        self.assertTrue(build().abandon().is_finished())

    def test_scheduled_is_not_finished(self):
        self.assertFalse(build().is_finished())

    def test_transition_table_targets_are_known(self):
        for targets in mod.TRANSITIONS.values():
            for target in targets:
                self.assertIn(target, mod.STATES)


class DurationTests(DomainTestCase):
    def setUp(self):
        session = build().go_live(OPENED, "2021-05-01T10:30:00Z").interrupt()
        self.session = session.go_live("2021-05-01T10:35:00Z", "2021-05-01T11:00:00Z")

    def test_connected_duration_skips_the_gap(self):
        self.assertEqual(55 * 60 * 1000, self.session.connected_duration().millis)

    def test_no_connections(self):
        self.assertTrue(build().connected_duration().is_zero())

    def test_billable_minutes_round_up(self):
        session = build().go_live(OPENED, "2021-05-01T10:00:30Z")
        self.assertEqual(1, session.billable_minutes())

    def test_billable_minutes(self):
        self.assertEqual(55, self.session.billable_minutes())

    def test_overlapping_connections_count_once(self):
        session = build().go_live(OPENED, "2021-05-01T10:30:00Z").interrupt()
        session = session.go_live("2021-05-01T10:20:00Z", "2021-05-01T10:40:00Z")
        self.assertEqual(40, session.billable_minutes())

    def test_span_covers_everything(self):
        self.assertEqual("2021-05-01T11:00:00Z", self.session.span().end.to_iso())

    def test_span_of_nothing(self):
        self.assertIsNone(build().span())

    def test_drop_count(self):
        self.assertEqual(1, self.session.drop_count())

    def test_no_drops(self):
        session = build().go_live(OPENED, "2021-05-01T10:30:00Z")
        self.assertEqual(0, session.drop_count())

    def test_no_connections_means_no_drops(self):
        self.assertEqual(0, build().drop_count())


class SerialisationTests(DomainTestCase):
    def test_to_dict(self):
        payload = build().go_live(OPENED, "2021-05-01T10:30:00Z").to_dict()
        self.assertEqual(30, payload["billable_minutes"])
        self.assertEqual(1, len(payload["connections"]))

    def test_equality(self):
        self.assertEqual(build(), build())

    def test_inequality(self):
        self.assertNotEqual(build(), build().abandon())

    def test_hashable(self):
        self.assertEqual(1, len({build(), build()}))

    def test_repr(self):
        self.assertIn("Drive time", repr(build()))


class AggregateTests(DomainTestCase):
    def setUp(self):
        self.may = build().go_live(OPENED, "2021-05-01T10:30:00Z").end()
        self.june = mod.LiveSession("u-1", "June", "2021-06-01T10:00:00Z").go_live(
            "2021-06-01T10:00:00Z", "2021-06-01T10:10:00Z"
        )

    def test_monthly_minutes(self):
        self.assertEqual(30, mod.monthly_minutes([self.may, self.june], 2021, 5))

    def test_monthly_minutes_of_another_month(self):
        self.assertEqual(10, mod.monthly_minutes([self.may, self.june], 2021, 6))

    def test_monthly_minutes_of_an_empty_month(self):
        self.assertEqual(0, mod.monthly_minutes([self.may], 2021, 7))

    def test_longest(self):
        self.assertEqual(self.may, mod.longest([self.may, self.june]))

    def test_longest_of_nothing(self):
        self.assertIsNone(mod.longest([]))

    def test_longest_default(self):
        self.assertEqual("x", mod.longest([], "x"))
