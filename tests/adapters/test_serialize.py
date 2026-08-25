from src.domain.adapters import serialize as mod
from src.domain.core.errors import NotFoundError
from src.domain.money.amount import Money
from tests.support import DomainTestCase


class ScrubTests(DomainTestCase):
    def test_removes_a_secret(self):
        self.assertEqual({"a": 1}, mod.scrub({"a": 1, "stream_key": "x"}))

    def test_removes_every_known_secret(self):
        payload = {key: "x" for key in mod.SECRET_KEYS}
        self.assertEqual({}, mod.scrub(payload))

    def test_recurses_into_nested_dicts(self):
        found = mod.scrub({"a": {"token": "x", "b": 1}})
        self.assertEqual({"a": {"b": 1}}, found)

    def test_recurses_into_lists(self):
        found = mod.scrub([{"token": "x", "b": 1}])
        self.assertEqual([{"b": 1}], found)

    def test_tuples_become_lists(self):
        self.assertEqual([1, 2], mod.scrub((1, 2)))

    def test_scalars_pass_through(self):
        self.assertEqual(1, mod.scrub(1))

    def test_leaves_the_original_alone(self):
        payload = {"a": 1, "token": "x"}
        mod.scrub(payload)
        self.assertIn("token", payload)


class OneTests(DomainTestCase):
    def test_wraps_a_value_object(self):
        self.assertEqual({"data": Money(1).to_dict()}, mod.one(Money(1)))

    def test_wraps_a_plain_value(self):
        self.assertEqual({"data": {"a": 1}}, mod.one({"a": 1}))

    def test_meta_is_optional(self):
        self.assertNotIn("meta", mod.one(Money(1)))

    def test_meta_is_included(self):
        self.assertEqual({"page": 1}, mod.one(Money(1), {"page": 1})["meta"])

    def test_meta_is_copied(self):
        meta = {"page": 1}
        body = mod.one(Money(1), meta)
        meta["page"] = 2
        self.assertEqual(1, body["meta"]["page"])


class ManyTests(DomainTestCase):
    def test_wraps_a_list(self):
        body = mod.many([Money(1), Money(2)])
        self.assertEqual(2, len(body["data"]))

    def test_count_is_added(self):
        self.assertEqual(2, mod.many([Money(1), Money(2)])["meta"]["count"])

    def test_explicit_count_is_kept(self):
        body = mod.many([Money(1)], {"count": 99})
        self.assertEqual(99, body["meta"]["count"])

    def test_empty(self):
        body = mod.many([])
        self.assertEqual([], body["data"])
        self.assertEqual(0, body["meta"]["count"])

    def test_plain_values(self):
        self.assertEqual([{"a": 1}], mod.many([{"a": 1}])["data"])


class PageTests(DomainTestCase):
    def setUp(self):
        self.result = {
            "items": [Money(1)],
            "total": 5,
            "page": 2,
            "page_size": 1,
            "pages": 5,
            "has_next": True,
            "has_previous": True,
        }

    def test_data(self):
        self.assertEqual(1, len(mod.page(self.result)["data"]))

    def test_paging_metadata(self):
        meta = mod.page(self.result)["meta"]
        self.assertEqual(5, meta["total"])
        self.assertEqual(2, meta["page"])
        self.assertTrue(meta["has_next"])

    def test_count_is_the_page_length(self):
        self.assertEqual(1, mod.page(self.result)["meta"]["count"])

    def test_extra_meta_is_kept(self):
        meta = mod.page(self.result, {"query": "x"})["meta"]
        self.assertEqual("x", meta["query"])


class ErrorTests(DomainTestCase):
    def test_domain_error(self):
        body, status = mod.error(NotFoundError("gone", kind="episode"))
        self.assertEqual("not_found", body["code"])
        self.assertEqual(404, status)

    def test_details_are_carried(self):
        body, _ = mod.error(NotFoundError("gone", kind="episode"))
        self.assertEqual("episode", body["details"]["kind"])

    def test_unexpected_error(self):
        body, status = mod.error(ValueError("boom"))
        self.assertEqual(500, status)
        self.assertEqual("internal_error", body["code"])

    def test_unexpected_error_hides_the_message(self):
        body, _ = mod.error(ValueError("secret detail"))
        self.assertNotIn("secret", body["message"])


class TruncatedTests(DomainTestCase):
    def test_under_the_limit(self):
        found = mod.truncated([1, 2], 5)
        self.assertEqual([1, 2], found["items"])
        self.assertFalse(found["truncated"])

    def test_over_the_limit(self):
        found = mod.truncated([1, 2, 3], 2)
        self.assertEqual([1, 2], found["items"])
        self.assertTrue(found["truncated"])

    def test_exactly_at_the_limit(self):
        self.assertFalse(mod.truncated([1, 2], 2)["truncated"])

    def test_total_is_the_full_length(self):
        self.assertEqual(3, mod.truncated([1, 2, 3], 2)["total"])

    def test_empty(self):
        self.assertEqual([], mod.truncated([], 2)["items"])

    def test_zero_limit_is_rejected(self):
        self.assertField("limit", mod.truncated, [1], 0)
