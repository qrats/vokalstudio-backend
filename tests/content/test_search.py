from src.domain.content.post import Post
from src.domain.content import search as mod
from tests.support import DomainTestCase

MAY = "2021-05-01T10:00:00Z"
JUNE = "2021-06-01T10:00:00Z"


def post(title, body="Some words about broadcasting.", tags=(), at=MAY):
    return Post(title, body, "u-1", tags=tags).publish(at)


class QueryTests(DomainTestCase):
    def test_defaults(self):
        query = mod.Query()
        self.assertIsNone(query.text)
        self.assertEqual(mod.NEWEST, query.order)
        self.assertEqual(1, query.page)
        self.assertEqual(mod.DEFAULT_PAGE_SIZE, query.page_size)

    def test_text_is_lowercased(self):
        self.assertEqual("live", mod.Query(text="LIVE").text)

    def test_text_whitespace_is_collapsed(self):
        self.assertEqual("a b", mod.Query(text="a   b").text)

    def test_empty_text_becomes_none(self):
        self.assertIsNone(mod.Query(text="").text)

    def test_tags_are_slugified_and_sorted(self):
        self.assertEqual(("audio", "live"), mod.Query(tags=["Live", "Audio"]).tags)

    def test_tags_are_deduplicated(self):
        self.assertEqual(("live",), mod.Query(tags=["live", "Live"]).tags)

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

    def test_first_page_offset(self):
        self.assertEqual(0, mod.Query().offset)

    def test_to_dict(self):
        payload = mod.Query(text="live", tags=["audio"], page=2).to_dict()
        self.assertEqual("live", payload["text"])
        self.assertEqual(["audio"], payload["tags"])

    def test_equality(self):
        self.assertEqual(mod.Query(text="a"), mod.Query(text="a"))

    def test_hashable(self):
        self.assertEqual(1, len({mod.Query(), mod.Query()}))

    def test_repr(self):
        self.assertIn("page 1", repr(mod.Query()))


class RunTests(DomainTestCase):
    def setUp(self):
        self.first = post("Alpha", "Talking about audio gear.", ["audio"], MAY)
        self.second = post("Beta", "Talking about live video.", ["live", "video"], JUNE)
        self.draft = Post("Gamma", "Not out yet.", "u-1")
        self.posts = [self.first, self.second, self.draft]

    def test_drafts_are_excluded(self):
        result = mod.run(self.posts, mod.Query())
        self.assertEqual(2, result["total"])

    def test_newest_first(self):
        result = mod.run(self.posts, mod.Query())
        self.assertEqual(self.second, result["items"][0])

    def test_oldest_first(self):
        result = mod.run(self.posts, mod.Query(order=mod.OLDEST))
        self.assertEqual(self.first, result["items"][0])

    def test_by_title(self):
        result = mod.run(self.posts, mod.Query(order=mod.TITLE))
        self.assertEqual(self.first, result["items"][0])

    def test_text_matches_the_title(self):
        result = mod.run(self.posts, mod.Query(text="beta"))
        self.assertEqual((self.second,), result["items"])

    def test_text_matches_the_body(self):
        result = mod.run(self.posts, mod.Query(text="audio gear"))
        self.assertEqual((self.first,), result["items"])

    def test_text_that_matches_nothing(self):
        self.assertEqual(0, mod.run(self.posts, mod.Query(text="zebra"))["total"])

    def test_tag_filter(self):
        result = mod.run(self.posts, mod.Query(tags=["live"]))
        self.assertEqual((self.second,), result["items"])

    def test_tags_are_combined_with_and(self):
        result = mod.run(self.posts, mod.Query(tags=["live", "audio"]))
        self.assertEqual(0, result["total"])

    def test_text_and_tags_together(self):
        result = mod.run(self.posts, mod.Query(text="video", tags=["live"]))
        self.assertEqual(1, result["total"])

    def test_visibility_date(self):
        result = mod.run(self.posts, mod.Query(), now="2021-05-15T00:00:00Z")
        self.assertEqual((self.first,), result["items"])


class PagingTests(DomainTestCase):
    def setUp(self):
        self.posts = [
            post("Post {}".format(index), at="2021-05-{:02d}T00:00:00Z".format(index + 1))
            for index in range(5)
        ]

    def test_page_size(self):
        result = mod.run(self.posts, mod.Query(page_size=2))
        self.assertEqual(2, len(result["items"]))

    def test_total_is_the_whole_match(self):
        self.assertEqual(5, mod.run(self.posts, mod.Query(page_size=2))["total"])

    def test_page_count(self):
        self.assertEqual(3, mod.run(self.posts, mod.Query(page_size=2))["pages"])

    def test_second_page(self):
        result = mod.run(self.posts, mod.Query(page=2, page_size=2))
        self.assertEqual(2, len(result["items"]))

    def test_last_page_is_short(self):
        result = mod.run(self.posts, mod.Query(page=3, page_size=2))
        self.assertEqual(1, len(result["items"]))

    def test_page_beyond_the_end(self):
        result = mod.run(self.posts, mod.Query(page=9, page_size=2))
        self.assertEqual((), result["items"])

    def test_has_next(self):
        self.assertTrue(mod.run(self.posts, mod.Query(page_size=2))["has_next"])

    def test_no_next_on_the_last_page(self):
        self.assertFalse(mod.run(self.posts, mod.Query(page=3, page_size=2))["has_next"])

    def test_has_previous(self):
        self.assertTrue(mod.run(self.posts, mod.Query(page=2, page_size=2))["has_previous"])

    def test_no_previous_on_the_first_page(self):
        self.assertFalse(mod.run(self.posts, mod.Query())["has_previous"])

    def test_empty_result(self):
        result = mod.run([], mod.Query())
        self.assertEqual(0, result["pages"])
        self.assertFalse(result["has_next"])


class TagStatisticsTests(DomainTestCase):
    def setUp(self):
        self.posts = [
            post("A", tags=["live", "audio"]),
            post("B", tags=["live"]),
            post("C", tags=["video"]),
            Post("D", "draft", "u-1", tags=["live"]),
        ]

    def test_counts(self):
        counts = mod.tag_counts(self.posts)
        self.assertEqual(2, counts["live"])
        self.assertEqual(1, counts["audio"])

    def test_drafts_do_not_count(self):
        self.assertEqual(2, mod.tag_counts(self.posts)["live"])

    def test_counts_of_nothing(self):
        self.assertEqual({}, mod.tag_counts([]))

    def test_popular_tags(self):
        self.assertEqual("live", mod.popular_tags(self.posts)[0])

    def test_popular_tags_break_ties_alphabetically(self):
        self.assertEqual(("live", "audio", "video"), mod.popular_tags(self.posts))

    def test_popular_tags_limit(self):
        self.assertEqual(1, len(mod.popular_tags(self.posts, limit=1)))

    def test_popular_tags_limit_floor(self):
        self.assertField("limit", mod.popular_tags, self.posts, 0)


class RelatedTests(DomainTestCase):
    def setUp(self):
        self.subject = post("A", tags=["live", "audio"])
        self.close = post("B", tags=["live", "audio", "video"])
        self.loose = post("C", tags=["live"])
        self.stranger = post("D", tags=["print"])
        self.posts = [self.subject, self.close, self.loose, self.stranger]

    def test_orders_by_shared_tags(self):
        found = mod.related(self.posts, self.subject)
        self.assertEqual((self.close, self.loose), found)

    def test_excludes_the_subject(self):
        self.assertNotIn(self.subject, mod.related(self.posts, self.subject))

    def test_excludes_unrelated_posts(self):
        self.assertNotIn(self.stranger, mod.related(self.posts, self.subject))

    def test_limit(self):
        self.assertEqual(1, len(mod.related(self.posts, self.subject, limit=1)))

    def test_nothing_related(self):
        self.assertEqual((), mod.related([self.stranger], self.subject))

    def test_limit_floor(self):
        self.assertField("limit", mod.related, self.posts, self.subject, 0)
