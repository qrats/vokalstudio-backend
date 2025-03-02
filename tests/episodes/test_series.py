from src.domain.episodes import series as mod
from tests.support import DomainTestCase


def build(**overrides):
    payload = {"owner_id": "u-1", "title": "Vokal Weekly"}
    payload.update(overrides)
    return mod.Series(**payload)


class ConstructionTests(DomainTestCase):
    def test_slug_from_the_title(self):
        self.assertEqual("vokal-weekly", build().slug)

    def test_explicit_slug(self):
        self.assertEqual("weekly", build(slug="Weekly").slug)

    def test_defaults(self):
        show = build()
        self.assertEqual(mod.EPISODIC, show.ordering)
        self.assertFalse(show.seasons)
        self.assertFalse(show.explicit)

    def test_empty_title(self):
        self.assertField("title", build, title="")

    def test_unknown_ordering(self):
        self.assertField("ordering", build, ordering="random")

    def test_serial_ordering(self):
        self.assertEqual(mod.SERIAL, build(ordering="serial").ordering)

    def test_seasons_accepts_text(self):
        self.assertTrue(build(seasons="true").seasons)

    def test_newest_first_for_episodic(self):
        self.assertTrue(build().newest_first())

    def test_oldest_first_for_serial(self):
        self.assertFalse(build(ordering="serial").newest_first())


class NumberingTests(DomainTestCase):
    def test_first_episode(self):
        self.assertEqual(1, build().number_for([]))

    def test_next_episode(self):
        self.assertEqual(3, build().number_for([(None, 1), (None, 2)]))

    def test_gaps_do_not_reset_the_counter(self):
        self.assertEqual(10, build().number_for([(None, 9), (None, 1)]))

    def test_seasons_are_counted_separately(self):
        show = build(seasons=True)
        self.assertEqual(3, show.number_for([(1, 1), (1, 2), (2, 1)], season=1))

    def test_new_season_starts_at_one(self):
        show = build(seasons=True)
        self.assertEqual(1, show.number_for([(1, 1), (1, 2)], season=3))

    def test_season_is_required_when_used(self):
        self.assertField("season", build(seasons=True).number_for, [])

    def test_season_is_refused_when_unused(self):
        self.assertField("season", build().number_for, [], 1)

    def test_season_must_be_positive(self):
        self.assertField("season", build(seasons=True).number_for, [], 0)


class LabelTests(DomainTestCase):
    def test_plain_label(self):
        self.assertEqual("#14", build().label_for(14))

    def test_season_label(self):
        self.assertEqual("S2E14", build(seasons=True).label_for(14, 2))

    def test_season_is_refused_without_seasons(self):
        self.assertField("season", build().label_for, 14, 2)

    def test_season_is_required_with_seasons(self):
        self.assertField("season", build(seasons=True).label_for, 14)

    def test_number_must_be_positive(self):
        self.assertField("number", build().label_for, 0)


class SerialisationTests(DomainTestCase):
    def test_to_dict(self):
        payload = build(seasons=True).to_dict()
        self.assertEqual("vokal-weekly", payload["slug"])
        self.assertTrue(payload["seasons"])

    def test_round_trip(self):
        self.assertRoundTrips(mod.Series.from_dict, build(ordering="serial", explicit=True))

    def test_equality(self):
        self.assertEqual(build(), build())

    def test_inequality(self):
        self.assertNotEqual(build(), build(seasons=True))

    def test_hashable(self):
        self.assertEqual(1, len({build(), build()}))

    def test_repr(self):
        self.assertIn("vokal-weekly", repr(build()))
