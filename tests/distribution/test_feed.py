from src.domain.distribution import feed as mod
from src.domain.episodes.chapters import Chapter
from src.domain.episodes.episode import Episode
from src.domain.episodes.series import Series
from src.domain.media.asset import Asset
from tests.support import DomainTestCase

ASSET = Asset("u-1", "episode-12.mp3", 5_000_000, duration="30:00")
SHOW = Series("u-1", "Vokal Weekly")
BASE = "https://vokalstudio.com"


def episode(title="Episode 12", at="2021-05-01T10:00:00Z", **overrides):
    payload = {
        "owner_id": "u-1",
        "series_slug": "vokal-weekly",
        "title": title,
        "asset": ASSET,
        "notes": "A good conversation.",
        "number": 12,
    }
    payload.update(overrides)
    return Episode(**payload).mark_ready().publish(at)


class BuildTests(DomainTestCase):
    def test_title_and_link(self):
        built = mod.build_feed(SHOW, [episode()], BASE)
        self.assertEqual("Vokal Weekly", built["title"])
        self.assertEqual(BASE + "/vokal-weekly", built["link"])

    def test_trailing_slash_is_trimmed(self):
        built = mod.build_feed(SHOW, [episode()], BASE + "/")
        self.assertEqual(BASE + "/vokal-weekly", built["link"])

    def test_count(self):
        self.assertEqual(1, mod.build_feed(SHOW, [episode()], BASE)["count"])

    def test_only_visible_episodes(self):
        draft = Episode("u-1", "vokal-weekly", "Draft", ASSET, "notes", number=1)
        built = mod.build_feed(SHOW, [episode(), draft], BASE)
        self.assertEqual(1, built["count"])

    def test_only_this_series(self):
        other = episode(title="Elsewhere", series_slug="other-show")
        built = mod.build_feed(SHOW, [episode(), other], BASE)
        self.assertEqual(1, built["count"])

    def test_newest_first_for_an_episodic_show(self):
        older = episode("Older", "2021-04-01T00:00:00Z")
        newer = episode("Newer", "2021-06-01T00:00:00Z")
        built = mod.build_feed(SHOW, [older, newer], BASE)
        self.assertEqual("Newer", built["items"][0]["title"])

    def test_oldest_first_for_a_serial_show(self):
        serial = Series("u-1", "Vokal Weekly", ordering="serial")
        older = episode("Older", "2021-04-01T00:00:00Z")
        newer = episode("Newer", "2021-06-01T00:00:00Z")
        built = mod.build_feed(serial, [newer, older], BASE)
        self.assertEqual("Older", built["items"][0]["title"])

    def test_description_is_optional(self):
        self.assertEqual("", mod.build_feed(SHOW, [], BASE)["description"])

    def test_description_is_carried(self):
        built = mod.build_feed(SHOW, [], BASE, description="A weekly show.")
        self.assertEqual("A weekly show.", built["description"])

    def test_artwork(self):
        built = mod.build_feed(SHOW, [], BASE, artwork_url="https://x.test/a.png")
        self.assertEqual("https://x.test/a.png", built["image"])

    def test_explicit_flag_comes_from_the_show(self):
        explicit = Series("u-1", "Vokal Weekly", explicit=True)
        self.assertTrue(mod.build_feed(explicit, [], BASE)["explicit"])

    def test_empty_base_url(self):
        self.assertField("base_url", mod.build_feed, SHOW, [], "")


class ItemTests(DomainTestCase):
    def setUp(self):
        self.item = mod.build_feed(SHOW, [episode()], BASE)["items"][0]

    def test_guid_is_the_reference(self):
        self.assertEqual(episode().reference, self.item["guid"])

    def test_link(self):
        self.assertEqual(BASE + "/vokal-weekly/episode-12", self.item["link"])

    def test_enclosure_url(self):
        self.assertEqual(BASE + "/media/" + ASSET.key, self.item["enclosure"]["url"])

    def test_enclosure_length(self):
        self.assertEqual(5_000_000, self.item["enclosure"]["length"])

    def test_enclosure_type(self):
        self.assertEqual("audio/mpeg", self.item["enclosure"]["type"])

    def test_duration(self):
        self.assertEqual(1_800_000, self.item["duration_millis"])

    def test_episode_number(self):
        self.assertEqual(12, self.item["episode"])

    def test_season_is_omitted_when_absent(self):
        self.assertNotIn("season", self.item)

    def test_season_is_included(self):
        built = mod.build_feed(SHOW, [episode(season=2)], BASE)
        self.assertEqual(2, built["items"][0]["season"])

    def test_chapters_are_omitted_when_absent(self):
        self.assertNotIn("chapters", self.item)

    def test_chapters_are_included(self):
        one = episode(chapters=[Chapter(0, "Intro")])
        built = mod.build_feed(SHOW, [one], BASE)
        self.assertEqual(1, len(built["items"][0]["chapters"]))

    def test_published_at(self):
        self.assertEqual("2021-05-01T10:00:00Z", self.item["published_at"])

    def test_description(self):
        self.assertEqual("A good conversation.", self.item["description"])


class HelperTests(DomainTestCase):
    def test_latest_item(self):
        built = mod.build_feed(SHOW, [episode()], BASE)
        self.assertEqual("Episode 12", mod.latest_item(built)["title"])

    def test_latest_item_of_an_empty_feed(self):
        self.assertIsNone(mod.latest_item(mod.build_feed(SHOW, [], BASE)))

    def test_total_duration(self):
        built = mod.build_feed(SHOW, [episode(), episode("Other")], BASE)
        self.assertEqual(3_600_000, mod.total_duration_millis(built))

    def test_total_duration_of_an_empty_feed(self):
        self.assertEqual(0, mod.total_duration_millis(mod.build_feed(SHOW, [], BASE)))

    def test_guids(self):
        built = mod.build_feed(SHOW, [episode()], BASE)
        self.assertEqual((episode().reference,), mod.guids(built))


class ValidationTests(DomainTestCase):
    def test_a_complete_feed(self):
        built = mod.build_feed(
            SHOW, [episode()], BASE, "https://x.test/a.png", "A weekly show."
        )
        self.assertEqual((), mod.validate_feed(built))

    def test_missing_description_and_image(self):
        built = mod.build_feed(SHOW, [episode()], BASE)
        self.assertEqual(("description", "image"), mod.validate_feed(built))

    def test_no_items(self):
        built = mod.build_feed(SHOW, [], BASE, "https://x.test/a.png", "A show.")
        self.assertEqual(("items",), mod.validate_feed(built))

    def test_duplicate_guids(self):
        built = mod.build_feed(
            SHOW, [episode(), episode()], BASE, "https://x.test/a.png", "A show."
        )
        self.assertIn("duplicate_guid", mod.validate_feed(built))

    def test_problems_are_sorted(self):
        problems = mod.validate_feed(mod.build_feed(SHOW, [], BASE))
        self.assertEqual(tuple(sorted(problems)), problems)
