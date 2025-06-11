from src.domain.episodes.chapters import Chapter
from src.domain.episodes import episode as mod
from src.domain.episodes.state import ARCHIVED, DRAFT, PUBLISHED, READY, SCHEDULED
from src.domain.media.asset import Asset
from tests.support import DomainTestCase

ASSET = Asset("u-1", "episode-12.mp3", 5_000_000, duration="30:00")
COVER = Asset("u-1", "cover.png", 400_000, role="artwork")
WHEN = "2021-05-01T10:00:00Z"


def build(**overrides):
    payload = {
        "owner_id": "u-1",
        "series_slug": "vokal-weekly",
        "title": "Episode 12",
        "asset": ASSET,
        "notes": "A good conversation.",
        "number": 12,
    }
    payload.update(overrides)
    return mod.Episode(**payload)


class ConstructionTests(DomainTestCase):
    def test_slug_from_the_title(self):
        self.assertEqual("episode-12", build().slug)

    def test_explicit_slug(self):
        self.assertEqual("twelve", build(slug="Twelve").slug)

    def test_defaults(self):
        episode = build()
        self.assertEqual(DRAFT, episode.state)
        self.assertEqual("full", episode.kind)
        self.assertFalse(episode.explicit)

    def test_notes_are_wrapped(self):
        self.assertEqual("A good conversation.", build().notes.body)

    def test_no_notes(self):
        self.assertTrue(build(notes=None).notes.is_empty)

    def test_image_asset_is_rejected(self):
        self.assertField("asset", build, asset=COVER)

    def test_asset_is_optional(self):
        self.assertIsNone(build(asset=None).asset)

    def test_unknown_kind(self):
        self.assertField("kind", build, kind="interlude")

    def test_number_must_be_positive(self):
        self.assertField("number", build, number=0)

    def test_season_must_be_positive(self):
        self.assertField("season", build, season=0)

    def test_published_state_needs_a_date(self):
        self.assertField("published_at", build, state=PUBLISHED)

    def test_scheduled_state_needs_a_date(self):
        self.assertField("published_at", build, state=SCHEDULED)

    def test_published_with_a_date(self):
        self.assertEqual(PUBLISHED, build(state=PUBLISHED, published_at=WHEN).state)

    def test_chapters_are_validated(self):
        self.assertField("chapters", build, chapters=[Chapter(1000, "late")])

    def test_chapters_past_the_asset_are_rejected(self):
        markers = [Chapter(0, "a"), Chapter(2_000_000, "b")]
        self.assertField("chapters", build, chapters=markers)

    def test_reference_is_stable(self):
        self.assertEqual(build().reference, build().reference)

    def test_reference_depends_on_the_slug(self):
        self.assertNotEqual(build().reference, build(title="Episode 13").reference)

    def test_duration(self):
        self.assertEqual(1_800_000, build().duration_millis)

    def test_duration_without_an_asset(self):
        self.assertEqual(0, build(asset=None).duration_millis)


class ReadinessTests(DomainTestCase):
    def test_complete_episode(self):
        self.assertEqual((), build().missing_for_publication())
        self.assertTrue(build().is_publishable())

    def test_missing_asset(self):
        self.assertEqual(("asset",), build(asset=None).missing_for_publication())

    def test_missing_notes(self):
        self.assertEqual(("show_notes",), build(notes=None).missing_for_publication())

    def test_missing_number(self):
        self.assertEqual(("number",), build(number=None).missing_for_publication())

    def test_several_missing_pieces(self):
        found = build(asset=None, notes=None, number=None).missing_for_publication()
        self.assertEqual(("asset", "number", "show_notes"), found)

    def test_is_editable(self):
        self.assertTrue(build().is_editable())

    def test_published_is_not_editable(self):
        self.assertFalse(build(state=PUBLISHED, published_at=WHEN).is_editable())

    def test_is_visible(self):
        self.assertTrue(build(state=PUBLISHED, published_at=WHEN).is_visible())

    def test_draft_is_not_visible(self):
        self.assertFalse(build().is_visible())


class LifecycleTests(DomainTestCase):
    def test_mark_ready(self):
        self.assertEqual(READY, build().mark_ready().state)

    def test_mark_ready_refuses_an_incomplete_episode(self):
        error = self.assertRaisesCode(
            "validation_failed", build(number=None).mark_ready
        )
        self.assertEqual(["number"], error.details["missing"])

    def test_schedule(self):
        episode = build().mark_ready().schedule(WHEN)
        self.assertEqual(SCHEDULED, episode.state)
        self.assertEqual(WHEN, episode.published_at.to_iso())

    def test_cannot_schedule_a_draft(self):
        self.assertRaisesCode("invalid_state", build().schedule, WHEN)

    def test_publish_from_ready(self):
        self.assertEqual(PUBLISHED, build().mark_ready().publish(WHEN).state)

    def test_publish_uses_the_scheduled_date(self):
        episode = build().mark_ready().schedule(WHEN).publish()
        self.assertEqual(WHEN, episode.published_at.to_iso())

    def test_publish_without_a_date(self):
        self.assertField("at", build().mark_ready().publish)

    def test_archive(self):
        self.assertEqual(ARCHIVED, build().archive().state)

    def test_archived_back_to_draft(self):
        self.assertEqual(DRAFT, build().archive().back_to_draft().state)

    def test_published_cannot_go_back_to_draft(self):
        episode = build().mark_ready().publish(WHEN)
        self.assertRaisesCode("invalid_state", episode.back_to_draft)

    def test_transitions_return_copies(self):
        episode = build()
        episode.mark_ready()
        self.assertEqual(DRAFT, episode.state)


class MutationTests(DomainTestCase):
    def test_with_asset(self):
        other = Asset("u-1", "other.mp3", 1_000_000, duration="10:00")
        self.assertEqual(other, build().with_asset(other).asset)

    def test_with_asset_clears_the_chapters(self):
        episode = build(chapters=[Chapter(0, "a")])
        other = Asset("u-1", "other.mp3", 1_000_000, duration="10:00")
        self.assertEqual((), episode.with_asset(other).chapters)

    def test_with_notes(self):
        self.assertEqual("New", build().with_notes("New").notes.body)

    def test_with_chapters(self):
        episode = build().with_chapters([Chapter(0, "a")])
        self.assertEqual(1, len(episode.chapters))

    def test_with_chapters_validates(self):
        self.assertField("chapters", build().with_chapters, [Chapter(5, "a")])

    def test_numbered(self):
        self.assertEqual(9, build().numbered(9).number)

    def test_numbered_with_a_season(self):
        episode = build().numbered(9, 2)
        self.assertEqual(2, episode.season)

    def test_mutations_return_copies(self):
        episode = build()
        episode.with_notes("New")
        self.assertEqual("A good conversation.", episode.notes.body)


class DueTests(DomainTestCase):
    def setUp(self):
        self.scheduled = build().mark_ready().schedule(WHEN)

    def test_before_the_time(self):
        self.assertFalse(self.scheduled.is_due("2021-05-01T09:59:59Z"))

    def test_at_the_time(self):
        self.assertTrue(self.scheduled.is_due(WHEN))

    def test_after_the_time(self):
        self.assertTrue(self.scheduled.is_due("2021-06-01T00:00:00Z"))

    def test_a_draft_is_never_due(self):
        self.assertFalse(build().is_due(WHEN))

    def test_a_published_episode_is_not_due(self):
        published = build().mark_ready().publish(WHEN)
        self.assertFalse(published.is_due(WHEN))


class SerialisationTests(DomainTestCase):
    def test_to_dict(self):
        payload = build(chapters=[Chapter(0, "a")]).to_dict()
        self.assertEqual("episode-12", payload["slug"])
        self.assertEqual(1, len(payload["chapters"]))
        self.assertEqual(ASSET.key, payload["asset_key"])

    def test_to_dict_without_an_asset(self):
        self.assertIsNone(build(asset=None).to_dict()["asset_key"])

    def test_equality(self):
        self.assertEqual(build(), build())

    def test_inequality(self):
        self.assertNotEqual(build(), build().mark_ready())

    def test_hashable(self):
        self.assertEqual(1, len({build(), build()}))

    def test_repr(self):
        self.assertIn("episode-12", repr(build()))


class CollectionTests(DomainTestCase):
    def setUp(self):
        self.draft = build()
        self.scheduled = build(title="Episode 13").mark_ready().schedule(WHEN)
        self.published = build(title="Episode 14").mark_ready().publish(WHEN)

    def test_due_for_publication(self):
        found = mod.due_for_publication([self.draft, self.scheduled], WHEN)
        self.assertEqual((self.scheduled,), found)

    def test_none_due_yet(self):
        found = mod.due_for_publication([self.scheduled], "2021-04-01T00:00:00Z")
        self.assertEqual((), found)

    def test_visible(self):
        found = mod.visible([self.draft, self.scheduled, self.published])
        self.assertEqual((self.published,), found)

    def test_published_in_month(self):
        found = mod.published_in_month([self.published, self.draft], 2021, 5)
        self.assertEqual((self.published,), found)

    def test_published_in_another_month(self):
        self.assertEqual((), mod.published_in_month([self.published], 2021, 6))

    def test_no_duplicate_slugs(self):
        self.assertEqual((), mod.duplicate_slugs([self.draft, self.scheduled]))

    def test_duplicate_slugs(self):
        self.assertEqual(("episode-12",), mod.duplicate_slugs([self.draft, build()]))

    def test_same_slug_in_another_series_is_fine(self):
        other = build(series_slug="other-show")
        self.assertEqual((), mod.duplicate_slugs([self.draft, other]))
