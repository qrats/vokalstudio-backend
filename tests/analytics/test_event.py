from src.domain.analytics import event as mod
from tests.support import DomainTestCase


def build(**overrides):
    payload = {
        "episode_reference": "e-1",
        "session_id": "s-1",
        "kind": mod.START,
        "at": "2021-05-01T10:00:00Z",
    }
    payload.update(overrides)
    return mod.PlayEvent(**payload)


class ConstructionTests(DomainTestCase):
    def test_defaults(self):
        one = build()
        self.assertEqual(0, one.position_millis)
        self.assertEqual("unknown", one.source)

    def test_unknown_kind(self):
        self.assertField("kind", build, kind="pause")

    def test_unknown_source(self):
        self.assertField("source", build, source="carrier-pigeon")

    def test_negative_position(self):
        self.assertField("position_millis", build, position_millis=-1)

    def test_download_has_no_position(self):
        self.assertField(
            "position_millis", build, kind=mod.DOWNLOAD, position_millis=100
        )

    def test_download_at_zero_is_fine(self):
        self.assertEqual(mod.DOWNLOAD, build(kind=mod.DOWNLOAD).kind)

    def test_empty_session(self):
        self.assertField("session_id", build, session_id="")

    def test_is_listen(self):
        self.assertTrue(build().is_listen)

    def test_download_is_not_a_listen(self):
        self.assertFalse(build(kind=mod.DOWNLOAD).is_listen)

    def test_day(self):
        self.assertEqual("2021-05-01", build().day())


class FingerprintTests(DomainTestCase):
    def test_stable(self):
        self.assertEqual(build().fingerprint, build().fingerprint)

    def test_ignores_the_timestamp(self):
        later = build(at="2021-05-01T11:00:00Z")
        self.assertEqual(build().fingerprint, later.fingerprint)

    def test_depends_on_the_position(self):
        self.assertNotEqual(build().fingerprint, build(position_millis=1).fingerprint)

    def test_depends_on_the_session(self):
        self.assertNotEqual(build().fingerprint, build(session_id="s-2").fingerprint)

    def test_depends_on_the_kind(self):
        self.assertNotEqual(build().fingerprint, build(kind=mod.COMPLETE).fingerprint)


class SerialisationTests(DomainTestCase):
    def test_to_dict(self):
        payload = build().to_dict()
        self.assertEqual("start", payload["kind"])
        self.assertEqual(build().fingerprint, payload["fingerprint"])

    def test_equality(self):
        self.assertEqual(build(), build())

    def test_hashable(self):
        self.assertEqual(1, len({build(), build()}))

    def test_repr(self):
        self.assertIn("start", repr(build()))


class DeduplicateTests(DomainTestCase):
    def test_drops_repeats(self):
        later = build(at="2021-05-01T11:00:00Z")
        self.assertEqual((build(),), mod.deduplicate([build(), later]))

    def test_keeps_the_earliest(self):
        later = build(at="2021-05-01T11:00:00Z")
        kept = mod.deduplicate([later, build()])
        self.assertEqual("2021-05-01T10:00:00Z", kept[0].at.to_iso())

    def test_keeps_distinct_events(self):
        other = build(position_millis=1000, kind=mod.PROGRESS)
        self.assertEqual(2, len(mod.deduplicate([build(), other])))

    def test_sorts_by_time(self):
        first = build(kind=mod.PROGRESS, position_millis=10, at="2021-05-01T09:00:00Z")
        kept = mod.deduplicate([build(), first])
        self.assertEqual(first, kept[0])

    def test_empty(self):
        self.assertEqual((), mod.deduplicate([]))


class QueryTests(DomainTestCase):
    def setUp(self):
        self.mine = build()
        self.theirs = build(episode_reference="e-2")
        self.other_session = build(session_id="s-2")

    def test_for_episode(self):
        found = mod.for_episode([self.mine, self.theirs], "e-1")
        self.assertEqual((self.mine,), found)

    def test_sessions_are_sorted_and_unique(self):
        found = mod.sessions([self.other_session, self.mine, self.mine])
        self.assertEqual(("s-1", "s-2"), found)

    def test_furthest_position(self):
        events = [
            build(),
            build(kind=mod.PROGRESS, position_millis=1000),
            build(kind=mod.PROGRESS, position_millis=500),
        ]
        self.assertEqual(1000, mod.furthest_position(events, "s-1"))

    def test_furthest_position_of_an_unknown_session(self):
        self.assertEqual(0, mod.furthest_position([build()], "s-9"))

    def test_downloads_do_not_count_as_position(self):
        events = [build(kind=mod.DOWNLOAD)]
        self.assertEqual(0, mod.furthest_position(events, "s-1"))
