from src.domain.content.post import Post
from src.domain.content import search as mod
from tests.support import DomainTestCase


def post(title, body="Some body text.", tags=(), at="2021-05-01T10:00:00Z"):
    return Post(title, body, "u-1", tags=tags).publish(at)


class QueryTests(DomainTestCase):
    def test_defaults(self):
        query = mod.Query()
        self.assertIsNone(query.text)
        self.assertEqual(mod.NEWEST, query.order)
        self.assertEqual(1, query.page)

    def test_text_is_lowercased(self):
        self.assertEqual("studio", mod.Query("  Studio ").text)

    def test_tags_are_slugified_and_sorted(self):
        self.assertEqual(("a", "b"), mod.Query(tags=["B", "a"]).tags)

    def test_unknown_order(self):
        self.assertField("order", mod.Query, None, (), "random")

    def test_page_floor(self):
        self.assertField("page", mod.Query, None, (), mod.NEWEST, 0)

    def test_page_size_ceiling(self):
        self.assertField(
            "page_size", mod.Query, None, (), mod.NEWEST, 1, mod.MAX_PAGE_SIZE + 1
        )

    def test_offset(self):
        self.assertEqual(20, mod.Query(page=3, page_size=10).offset)

    def test_offset_of_the_first_page(self):
        self.assertEqual(0, mod.Query().offset)

    def test_to_dict(self):
        self.assertEqual(10, mod.Query().to_dict()["page_size"])

    def test_equality(self):
        self.assertEqual(mod.Query("a"), mod.Query("a"))

    def test_hashable(self):
        self.assertEqual(1, len({mod.Query(), mod.Query()}))

    def test_repr(self):
        self.assertIn("page 1", repr(mod.Query()))


class RunTests(DomainTestCase):
    def setUp(self):
        self.first = post("Alpha", "About the studio.", ["news"], "2021-01-01T00:00:00Z")
        self.second = post("Beta", "About streaming.", ["news", "studio"], "2021-06-01T00:00:00Z")
        self.draft = Post("Gamma", "Hidden.", "u-1")
        self.posts = [self.first, self.second, self.draft]

    def test_drafts_are_excluded(self):
        self.assertEqual(2, mod.run(self.posts, mod.Query())["total"])

    def test_newest_first(self):
        result = mod.run(self.posts, mod.Query())
        self.assertEqual("Beta", result["items"][0].title)

    def test_oldest_first(self):
        result = mod.run(self.posts, mod.Query(order=mod.OLDEST))
        self.assertEqual("Alpha", result["items"][0].title)

    def test_by_title(self):
        result = mod.run(self.posts, mod.Query(order=mod.TITLE))
        self.assertEqual("Alpha", result["items"][0].title)

    def test_text_matches_the_title(self):
        result = mod.run(self.posts, mod.Query("beta"))
        self.assertEqual(1, result["total"])

    def test_text_matches_the_body(self):
        result = mod.run(self.posts, mod.Query("streaming"))
        self.assertEqual("Beta", result["items"][0].title)

    def test_text_that_matches_nothing(self):
        self.assertEqual(0, mod.run(self.posts, mod.Query("nowhere"))["total"])

    def test_one_tag(self):
        self.assertEqual(2, mod.run(self.posts, mod.Query(tags=["news"]))["total"])

    def test_all_tags_must_match(self):
        result = mod.run(self.posts, mod.Query(tags=["news", "studio"]))
        self.assertEqual(1, result["total"])

    def test_paging(self):
        result = mod.run(self.posts, mod.Query(page_size=1))
        self.assertEqual(1, len(result["items"]))
        self.assertEqual(2, result["pages"])
        self.assertTrue(result["has_next"])
        self.assertFalse(result["has_previous"])

    def test_second_page(self):
        result = mod.run(self.posts, mod.Query(page=2, page_size=1))
        self.assertEqual("Alpha", result["items"][0].title)
        self.assertFalse(result["has_next"])
        self.assertTrue(result["has_previous"])

    def test_page_beyond_the_end(self):
        result = mod.run(self.posts, mod.Query(page=9, page_size=1))
        self.assertEqual((), result["items"])

    def test_visibility_date(self):
        result = mod.run(self.posts, mod.Query(), "2021-03-01T00:00:00Z")
        self.assertEqual(1, result["total"])


class TagTests(DomainTestCase):
    def setUp(self):
        self.posts = [
            post("Alpha", tags=["news"]),
            post("Beta", tags=["news", "studio"]),
            Post("Gamma", "Hidden.", "u-1", tags=["hidden"]),
        ]

    def test_counts(self):
        self.assertEqual({"news": 2, "studio": 1}, mod.tag_counts(self.posts))

    def test_drafts_are_excluded(self):
        self.assertNotIn("hidden", mod.tag_counts(self.posts))

    def test_popular_tags(self):
        self.assertEqual(("news", "studio"), mod.popular_tags(self.posts))

    def test_popular_tags_limit(self):
        self.assertEqual(("news",), mod.popular_tags(self.posts, 1))

    def test_popular_tags_limit_floor(self):
        self.assertField("limit", mod.popular_tags, self.posts, 0)

    def test_no_tags(self):
        self.assertEqual((), mod.popular_tags([post("Alpha")]))


class RelatedTests(DomainTestCase):
    def setUp(self):
        self.subject = post("Alpha", tags=["news", "studio"])
        self.close = post("Beta", tags=["news", "studio"])
        self.loose = post("Gamma", tags=["news"])
        self.unrelated = post("Delta", tags=["other"])

    def test_most_shared_tags_first(self):
        found = mod.related(
            [self.subject, self.loose, self.close, self.unrelated], self.subject
        )
        self.assertEqual("Beta", found[0].title)

    def test_the_subject_is_excluded(self):
        found = mod.related([self.subject, self.close], self.subject)
        self.assertEqual(1, len(found))

    def test_unrelated_posts_are_dropped(self):
        found = mod.related([self.subject, self.unrelated], self.subject)
        self.assertEqual((), found)

    def test_limit(self):
        found = mod.related([self.subject, self.close, self.loose], self.subject, 1)
        self.assertEqual(1, len(found))

    def test_limit_floor(self):
        self.assertField("limit", mod.related, [], self.subject, 0)
