from src.domain.content import post as mod
from tests.support import DomainTestCase

BODY = "Intro paragraph.\n\n## Section\n\nMore text."


def build(**overrides):
    payload = {"title": "Hello world", "body": BODY, "author_id": "u-1"}
    payload.update(overrides)
    return mod.Post(**payload)


def live(**overrides):
    return build(**overrides).publish("2021-05-01T10:00:00Z")


class ConstructionTests(DomainTestCase):
    def test_slug_from_the_title(self):
        self.assertEqual("hello-world", build().slug)

    def test_explicit_slug(self):
        self.assertEqual("intro", build(slug="Intro").slug)

    def test_defaults(self):
        post = build()
        self.assertEqual(mod.DRAFT, post.state)
        self.assertEqual((), post.tags)
        self.assertFalse(post.featured)

    def test_empty_body(self):
        self.assertField("body", build, body="")

    def test_over_long_body(self):
        self.assertField("body", build, body="x" * (mod.MAX_BODY + 1))

    def test_tags_are_slugified(self):
        self.assertEqual(("hot-news",), build(tags=["Hot News"]).tags)

    def test_tags_are_sorted_and_unique(self):
        self.assertEqual(("a", "b"), build(tags=["b", "a", "B"]).tags)

    def test_too_many_tags(self):
        self.assertField("tags", build, tags=["t{}".format(i) for i in range(13)])

    def test_unknown_state(self):
        self.assertField("state", build, state="review")

    def test_published_needs_a_date(self):
        self.assertField("published_at", build, state=mod.PUBLISHED)

    def test_a_draft_cannot_be_featured(self):
        self.assertField("featured", build, featured=True)

    def test_a_published_post_can_be_featured(self):
        post = build(state=mod.PUBLISHED, published_at="2021-05-01T10:00:00Z", featured=True)
        self.assertTrue(post.featured)


class TransitionTests(DomainTestCase):
    def test_publish(self):
        self.assertEqual(mod.PUBLISHED, live().state)

    def test_publish_records_the_date(self):
        self.assertEqual("2021-05-01T10:00:00Z", live().published_at.to_iso())

    def test_unpublish(self):
        self.assertEqual(mod.DRAFT, live().unpublish().state)

    def test_unpublish_clears_featured(self):
        self.assertFalse(live().feature().unpublish().featured)

    def test_archive(self):
        self.assertEqual(mod.ARCHIVED, build().archive().state)

    def test_archived_back_to_draft(self):
        self.assertEqual(mod.DRAFT, build().archive().unpublish().state)

    def test_archived_cannot_be_published_directly(self):
        self.assertRaisesCode(
            "invalid_state", build().archive().publish, "2021-05-01T10:00:00Z"
        )

    def test_feature(self):
        self.assertTrue(live().feature().featured)

    def test_a_draft_cannot_be_featured(self):
        self.assertField("featured", build().feature)

    def test_unfeature(self):
        self.assertFalse(live().feature().unfeature().featured)

    def test_transitions_return_copies(self):
        post = build()
        post.archive()
        self.assertEqual(mod.DRAFT, post.state)

    def test_table_covers_every_state(self):
        self.assertEqual(set(mod.STATES), set(mod.TRANSITIONS))


class TagTests(DomainTestCase):
    def test_tagged(self):
        self.assertTrue(build(tags=["news"]).tagged("News"))

    def test_not_tagged(self):
        self.assertFalse(build(tags=["news"]).tagged("studio"))

    def test_with_tags(self):
        self.assertEqual(("studio",), build().with_tags(["Studio"]).tags)

    def test_with_tags_returns_a_copy(self):
        post = build(tags=["news"])
        post.with_tags(["studio"])
        self.assertEqual(("news",), post.tags)


class VisibilityTests(DomainTestCase):
    def test_a_draft_is_not_visible(self):
        self.assertFalse(build().is_visible())

    def test_a_published_post_is_visible(self):
        self.assertTrue(live().is_visible())

    def test_not_visible_before_its_date(self):
        self.assertFalse(live().is_visible("2021-04-01T00:00:00Z"))

    def test_visible_on_its_date(self):
        self.assertTrue(live().is_visible("2021-05-01T10:00:00Z"))

    def test_archived_is_never_visible(self):
        self.assertFalse(build().archive().is_visible())


class RenderTests(DomainTestCase):
    def test_blocks(self):
        self.assertEqual(3, len(build().blocks()))

    def test_excerpt(self):
        self.assertEqual("Intro paragraph.", build().excerpt())

    def test_table_of_contents(self):
        self.assertEqual(1, len(build().table_of_contents()))

    def test_word_count(self):
        self.assertEqual(6, build().word_count())

    def test_reading_time(self):
        self.assertGreater(build().reading_time_seconds(), 0)


class SerialisationTests(DomainTestCase):
    def test_to_dict(self):
        payload = live(tags=["news"]).to_dict()
        self.assertEqual("hello-world", payload["slug"])
        self.assertEqual(["news"], payload["tags"])

    def test_to_dict_carries_the_excerpt(self):
        self.assertEqual("Intro paragraph.", build().to_dict()["excerpt"])

    def test_equality(self):
        self.assertEqual(build(), build())

    def test_body_matters(self):
        self.assertNotEqual(build(), build(body="Different."))

    def test_hashable(self):
        self.assertEqual(1, len({build(), build()}))

    def test_repr(self):
        self.assertIn("hello-world", repr(build()))


class CollectionTests(DomainTestCase):
    def setUp(self):
        self.draft = build(title="Draft")
        self.live = live(title="Live")
        self.starred = live(title="Starred").feature()

    def test_visible(self):
        found = mod.visible([self.draft, self.live, self.starred])
        self.assertEqual(2, len(found))

    def test_featured(self):
        found = mod.featured([self.draft, self.live, self.starred])
        self.assertEqual((self.starred,), found)

    def test_featured_respects_the_date(self):
        self.assertEqual((), mod.featured([self.starred], "2021-04-01T00:00:00Z"))

    def test_find(self):
        self.assertEqual(self.live, mod.find([self.draft, self.live], "Live"))

    def test_find_default(self):
        self.assertEqual("x", mod.find([self.draft], "nope", "x"))

    def test_no_duplicate_slugs(self):
        self.assertEqual((), mod.duplicate_slugs([self.draft, self.live]))

    def test_duplicate_slugs(self):
        self.assertEqual(("draft",), mod.duplicate_slugs([self.draft, build(title="Draft")]))
