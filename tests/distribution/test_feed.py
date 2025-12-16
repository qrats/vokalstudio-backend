from src.domain.distribution import feed as mod
from src.domain.episodes.chapters import Chapter
from src.domain.episodes.episode import Episode
from src.domain.episodes.series import SERIAL, Series
from src.domain.media.asset import Asset
from tests.support import DomainTestCase

BASE = "https://vokalstudio.com"
ASSET = Asset("u-1", "ep.mp3", 5_000_000, duration="30:00")


def episode(title="Episode 12", at="2021-05-01T10:00:00Z", **overrides):
    payload = {
        "owner_id": "u-1",
        "series_slug": "vokal-weekly",
        "title": title,
        "asset": ASSET,
        "notes": "Some notes.",
        "number": 12,
    }
    payload.update(overrides)
    return Episode(**payload).mark_ready().publish(at)


def series(**overrides):
    payload = {"owner_id": "u-1", "title": "Vokal Weekly"}
    payload.update(overrides)
    return Series(**payload)


def feed(episodes=None, **overrides):
    payload = {
        "series": series(),
        "episodes": episodes if episodes is not None else [episode()],
        "base_url": BASE,
        "artwork_url": "https://vokalstudio.com/art.png",
        "description": "A weekly show.",
    }
    payload.update(overrides)
    return mod.build_feed(**payload)


class ShapeTests(DomainTestCase):
    def test_title(self):
        self.assertEqual("Vokal Weekly", feed()["title"])

    def test_link(self):
        self.assertEqual(BASE + "/vokal-weekly", feed()["link"])

    def test_trailing_slash_is_trimmed(self):
        built = feed(base_url=BASE + "/")
        self.assertEqual(BASE + "/vokal-weekly", built["link"])

    def test_count(self):
        self.assertEqual(1, feed()["count"])

    def test_empty_description(self):
        self.assertEqual("", feed(description="")["description"])

    def test_explicit_flag(self):
        self.assertTrue(feed(series=series(explicit=True))["explicit"])

    def test_ordering_is_reported(self):
        self.assertEqual("episodic", feed()["ordering"])


class ItemTests(DomainTestCase):
    def setUp(self):
        self.item = feed()["items"][0]

    def test_guid_is_the_reference(self):
        self.assertEqual(episode().reference, self.item["guid"])

    def test_link(self):
        self.assertEqual(BASE + "/vokal-weekly/episode-12", self.item["link"])

    def test_enclosure_url(self):
        self.assertTrue(self.item["enclosure"]["url"].endswith(ASSET.key))

    def test_enclosure_length(self):
        self.assertEqual(5_000_000, self.item["enclosure"]["length"])

    def test_enclosure_type(self):
        self.assertEqual("audio/mpeg", self.item["enclosure"]["type"])

    def test_duration(self):
        self.assertEqual(1_800_000, self.item["duration_millis"])

    def test_number(self):
        self.assertEqual(12, self.item["episode"])

    def test_season_is_absent_when_unset(self):
        self.assertNotIn("season", self.item)

    def test_season_is_present_when_set(self):
        one = episode(season=2)
        item = mod.build_feed(series(seasons=True), [one], BASE)["items"][0]
        self.assertEqual(2, item["season"])

    def test_chapters_are_absent_by_default(self):
        self.assertNotIn("chapters", self.item)

    def test_chapters_are_included(self):
        one = episode(chapters=[Chapter(0, "Intro")])
        item = mod.build_feed(series(), [one], BASE)["items"][0]
        self.assertEqual(1, len(item["chapters"]))

    def test_published_at(self):
        self.assertEqual("2021-05-01T10:00:00Z", self.item["published_at"])


class SelectionTests(DomainTestCase):
    def test_only_published_episodes(self):
        draft = Episode("u-1", "vokal-weekly", "Draft")
        self.assertEqual(1, feed([episode(), draft])["count"])

    def test_only_this_series(self):
        other = Episode(
            "u-1", "other-show", "Elsewhere", asset=ASSET, notes="N", number=1
        ).mark_ready().publish("2021-05-01T10:00:00Z")
        self.assertEqual(1, feed([episode(), other])["count"])

    def test_newest_first_for_episodic(self):
        older = episode("Older", "2021-04-01T10:00:00Z")
        newer = episode("Newer", "2021-06-01T10:00:00Z")
        built = feed([older, newer])
        self.assertEqual("Newer", built["items"][0]["title"])

    def test_oldest_first_for_serial(self):
        older = episode("Older", "2021-04-01T10:00:00Z")
        newer = episode("Newer", "2021-06-01T10:00:00Z")
        built = feed([newer, older], series=series(ordering=SERIAL))
        self.assertEqual("Older", built["items"][0]["title"])

    def test_no_episodes(self):
        self.assertEqual(0, feed([])["count"])


class HelperTests(DomainTestCase):
    def test_latest_item(self):
        self.assertEqual("Episode 12", mod.latest_item(feed())["title"])

    def test_latest_item_of_an_empty_feed(self):
        self.assertIsNone(mod.latest_item(feed([])))

    def test_total_duration(self):
        built = feed([episode("A", "2021-04-01T10:00:00Z"), episode("B")])
        self.assertEqual(3_600_000, mod.total_duration_millis(built))

    def test_total_duration_of_an_empty_feed(self):
        self.assertEqual(0, mod.total_duration_millis(feed([])))

    def test_guids(self):
        self.assertEqual((episode().reference,), mod.guids(feed()))


class ValidationTests(DomainTestCase):
    def test_a_complete_feed_passes(self):
        self.assertEqual((), mod.validate_feed(feed()))

    def test_missing_description(self):
        self.assertEqual(("description",), mod.validate_feed(feed(description="")))

    def test_missing_image(self):
        self.assertEqual(("image",), mod.validate_feed(feed(artwork_url=None)))

    def test_no_items(self):
        self.assertIn("items", mod.validate_feed(feed([])))

    def test_duplicate_guids(self):
        built = feed([episode(), episode()])
        self.assertIn("duplicate_guid", mod.validate_feed(built))

    def test_problems_are_sorted(self):
        found = mod.validate_feed(feed([], description="", artwork_url=None))
        self.assertEqual(tuple(sorted(found)), found)
