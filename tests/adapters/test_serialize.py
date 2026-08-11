from src.domain.adapters import serialize as mod
from src.domain.core.errors import NotFoundError, ValidationError
from src.domain.media.asset import Asset
from tests.support import DomainTestCase

ASSET = Asset("u-1", "ep.mp3", 500, duration=1000)


class ScrubTests(DomainTestCase):
    def test_removes_a_stream_key(self):
        self.assertEqual({"a": 1}, mod.scrub({"a": 1, "stream_key": "secret"}))

    def test_removes_a_token(self):
        self.assertNotIn("token", mod.scrub({"token": "abc"}))

    def test_removes_nested_secrets(self):
        found = mod.scrub({"target": {"stream_key": "s", "platform": "youtube"}})
        self.assertEqual({"target": {"platform": "youtube"}}, found)

    def test_scrubs_inside_lists(self):
        found = mod.scrub({"targets": [{"stream_key": "s", "id": 1}]})
        self.assertEqual([{"id": 1}], found["targets"])

    def test_leaves_scalars_alone(self):
        self.assertEqual(1, mod.scrub(1))

    def test_tuples_become_lists(self):
        self.assertEqual([1, 2], mod.scrub((1, 2)))

    def test_every_secret_key_is_removed(self):
        payload = {key: "x" for key in mod.SECRET_KEYS}
        self.assertEqual({}, mod.scrub(payload))


class EnvelopeTests(DomainTestCase):
    def test_one_serialises_the_object(self):
        self.assertEqual("audio", mod.one(ASSET)["data"]["kind"])

    def test_one_accepts_a_plain_value(self):
        self.assertEqual({"a": 1}, mod.one({"a": 1})["data"])

    def test_one_without_meta(self):
        self.assertNotIn("meta", mod.one(ASSET))

    def test_one_with_meta(self):
        self.assertEqual({"cached": True}, mod.one(ASSET, {"cached": True})["meta"])

    def test_many_counts(self):
        self.assertEqual(2, mod.many([ASSET, ASSET])["meta"]["count"])

    def test_many_of_nothing(self):
        body = mod.many([])
        self.assertEqual([], body["data"])
        self.assertEqual(0, body["meta"]["count"])

    def test_many_keeps_supplied_meta(self):
        body = mod.many([ASSET], {"source": "cache"})
        self.assertEqual("cache", body["meta"]["source"])

    def test_supplied_count_wins(self):
        self.assertEqual(99, mod.many([ASSET], {"count": 99})["meta"]["count"])


class PageTests(DomainTestCase):
    def setUp(self):
        self.result = {
            "items": [ASSET],
            "total": 5,
            "page": 2,
            "page_size": 1,
            "pages": 5,
            "has_next": True,
            "has_previous": True,
        }

    def test_data(self):
        self.assertEqual(1, len(mod.page(self.result)["data"]))

    def test_paging_meta(self):
        meta = mod.page(self.result)["meta"]
        self.assertEqual(5, meta["total"])
        self.assertEqual(2, meta["page"])
        self.assertTrue(meta["has_next"])

    def test_count_is_the_page_length(self):
        self.assertEqual(1, mod.page(self.result)["meta"]["count"])

    def test_extra_meta_is_kept(self):
        meta = mod.page(self.result, {"query": "live"})["meta"]
        self.assertEqual("live", meta["query"])


class ErrorTests(DomainTestCase):
    def test_domain_error(self):
        body, status = mod.error(ValidationError("bad", field="title"))
        self.assertEqual(422, status)
        self.assertEqual("validation_failed", body["code"])

    def test_details_are_carried(self):
        body, _ = mod.error(ValidationError("bad", field="title"))
        self.assertEqual("title", body["details"]["field"])

    def test_not_found(self):
        _, status = mod.error(NotFoundError("gone"))
        self.assertEqual(404, status)

    def test_unexpected_error(self):
        body, status = mod.error(ValueError("boom"))
        self.assertEqual(500, status)
        self.assertEqual("internal_error", body["code"])

    def test_unexpected_error_hides_the_message(self):
        body, _ = mod.error(ValueError("secret detail"))
        self.assertNotIn("secret", body["message"])


class TruncateTests(DomainTestCase):
    def test_under_the_limit(self):
        found = mod.truncated([1, 2], 5)
        self.assertEqual([1, 2], found["items"])
        self.assertFalse(found["truncated"])

    def test_over_the_limit(self):
        found = mod.truncated([1, 2, 3], 2)
        self.assertEqual([1, 2], found["items"])
        self.assertTrue(found["truncated"])

    def test_total_is_the_whole_input(self):
        self.assertEqual(3, mod.truncated([1, 2, 3], 2)["total"])

    def test_exactly_the_limit(self):
        self.assertFalse(mod.truncated([1, 2], 2)["truncated"])

    def test_empty(self):
        self.assertEqual([], mod.truncated([], 2)["items"])

    def test_limit_floor(self):
        self.assertField("limit", mod.truncated, [1], 0)
