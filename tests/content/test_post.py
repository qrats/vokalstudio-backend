from src.domain.content import post as mod
from tests.support import DomainTestCase

WHEN = "2021-05-01T10:00:00Z"
BODY = "# Heading\n\nSome words in a paragraph.\n\n## Second\n\nMore words here."


def build(**overrides):
    payload = {"title": "Going live", "body": BODY, "author_id": "u-1"}
    payload.update(overrides)
    return mod.Post(**payload)


class ConstructionTests(DomainTestCase):
    def test_slug_from_the_title(self):
        self.assertEqual("going-live", build().slug)

    def test_explicit_slug(self):
        self.assertEqual("live", build(slug="Live").slug)

    def test_defaults(self):
        post = build()
        self.assertEqual(mod.DRAFT, post.state)
        self.assertEqual((), post.tags)
        self.assertFalse(post.featured)

    def test_empty_title(self):
        self.assertField("title", build, title="")

    def test_empty_body(self):
        self.assertField("body", build, body="")

    def test_over_long_body(self):
        self.assertField("body", build, body="x" * (mod.MAX_BODY + 1))

    def test_unknown_state(self):
        self.assertField("state", build, state="review")

    def test_published_needs_a_date(self):
        self.assertField("published_at", build, state=mod.PUBLISHED)

    def test_featured_must_be_published(self):
        self.assertField("featured", build, featured=True)

    def test_featured_published_post(self):
        post = build(state=mod.PUBLISHED, published_at=WHEN, featured=True)
        self.assertTrue(post.featured)

    def test_hero_key(self):
        self.assertEqual("k", build(hero_key="k").hero_key)


class TagTests(DomainTestCase):
    def test_tags_are_slugified(self):
        self.assertEqual(("live-streaming",), build(tags=["Live Streaming"]).tags)

    def test_tags_are_sorted(self):
        self.assertEqual(("alpha", "beta"), build(tags=["beta", "alpha"]).tags)

    def test_tags_are_deduplicated(self):
        self.assertEqual(("alpha",), build(tags=["Alpha", "alpha"]).tags)

    def test_too_many_tags(self):
        self.assertField("tags", build, tags=["t{}".format(n) for n in range(13)])

    def test_unusable_tag(self):
        self.assertField("tags", build, tags=["###"])

    def test_tagged(self):
        self.assertTrue(build(tags=["live"]).tagged("Live"))

    def test_not_tagged(self):
        self.assertFalse(build(tags=["live"]).tagged("audio"))

    def test_with_tags(self):
        self.assertEqual(("audio",), build(tags=["live"]).with_tags(["audio"]).tags)

    def test_with_tags_returns_a_copy(self):
        post = build(tags=["live"])
        post.with_tags(["audio"])
        self.assertEqual(("live",), post.tags)


class LifecycleTests(DomainTestCase):
    def test_publish(self):
        post = build().publish(WHEN)
        self.assertEqual(mod.PUBLISHED, post.state)
        self.assertEqual(WHEN, post.published_at.to_iso())

    def test_unpublish(self):
        self.assertEqual(mod.DRAFT, build().publish(WHEN).unpublish().state)

    def test_unpublish_clears_featured(self):
        post = build().publish(WHEN).feature().unpublish()
        self.assertFalse(post.featured)

    def test_archive(self):
        self.assertEqual(mod.ARCHIVED, build().archive().state)

    def test_archived_can_be_reopened(self):
        self.assertEqual(mod.DRAFT, build().archive().unpublish().state)

    def test_archive_clears_featured(self):
        self.assertFalse(build().publish(WHEN).feature().archive().featured)

    def test_cannot_publish_an_archived_post(self):
        self.assertRaisesCode("invalid_state", build().archive().publish, WHEN)

    def test_feature(self):
        self.assertTrue(build().publish(WHEN).feature().featured)

    def test_cannot_feature_a_draft(self):
        self.assertField("featured", build().feature)

    def test_unfeature(self):
        self.assertFalse(build().publish(WHEN).feature().unfeature().featured)

    def test_transitions_return_copies(self):
        post = build()
        post.publish(WHEN)
        self.assertEqual(mod.DRAFT, post.state)

    def test_transition_table_targets_are_known(self):
        for targets in mod.TRANSITIONS.values():
            for target in targets:
                self.assertIn(target, mod.STATES)


class VisibilityTests(DomainTestCase):
    def test_draft_is_not_visible(self):
        self.assertFalse(build().is_visible())

    def test_published_is_visible(self):
        self.assertTrue(build().publish(WHEN).is_visible())

    def test_not_visible_before_the_date(self):
        self.assertFalse(build().publish(WHEN).is_visible("2021-04-01T00:00:00Z"))

    def test_visible_on_the_date(self):
        self.assertTrue(build().publish(WHEN).is_visible(WHEN))

    def test_archived_is_not_visible(self):
        self.assertFalse(build().archive().is_visible())


class RenderTests(DomainTestCase):
    def test_blocks(self):
        self.assertGreater(len(build().blocks()), 1)

    def test_excerpt(self):
        self.assertLessEqual(len(build().excerpt(30)), 30)

    def test_table_of_contents_skips_the_title_level(self):
        entries = build().table_of_contents()
        self.assertEqual(1, len(entries))
        self.assertEqual("Second", entries[0]["text"])

    def test_word_count(self):
        self.assertGreater(build().word_count(), 5)

    def test_reading_time(self):
        self.assertGreater(build().reading_time_seconds(), 0)


class SerialisationTests(DomainTestCase):
    def test_to_dict(self):
        payload = build(tags=["live"]).to_dict()
        self.assertEqual("going-live", payload["slug"])
        self.assertEqual(["live"], payload["tags"])

    def test_to_dict_omits_the_body(self):
        self.assertNotIn("body", build().to_dict())

    def test_equality(self):
        self.assertEqual(build(), build())

    def test_body_matters_for_equality(self):
        self.assertNotEqual(build(), build(body="Different words entirely."))

    def test_hashable(self):
        self.assertEqual(1, len({build(), build()}))

    def test_repr(self):
        self.assertIn("going-live", repr(build()))


class CollectionTests(DomainTestCase):
    def setUp(self):
        self.draft = build()
        self.live = build(title="Second").publish(WHEN)
        self.star = build(title="Third").publish(WHEN).feature()

    def test_visible(self):
        found = mod.visible([self.draft, self.live, self.star])
        self.assertEqual((self.live, self.star), found)

    def test_featured(self):
        self.assertEqual((self.star,), mod.featured([self.live, self.star]))

    def test_featured_respects_the_date(self):
        self.assertEqual((), mod.featured([self.star], "2021-01-01T00:00:00Z"))

    def test_no_duplicate_slugs(self):
        self.assertEqual((), mod.duplicate_slugs([self.draft, self.live]))

    def test_duplicate_slugs(self):
        self.assertEqual(("going-live",), mod.duplicate_slugs([self.draft, build()]))

    def test_find(self):
        self.assertEqual(self.live, mod.find([self.draft, self.live], "second"))

    def test_find_normalises_the_slug(self):
        self.assertEqual(self.live, mod.find([self.live], "Second"))

    def test_find_default(self):
        self.assertEqual("x", mod.find([], "nope", "x"))
