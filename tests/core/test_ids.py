from src.domain.core import ids
from tests.support import DomainTestCase


class UuidTests(DomainTestCase):
    def test_recognises_uuid(self):
        self.assertTrue(ids.is_uuid_like("2f1c9a3e-4b5d-4e6f-8a90-1234567890ab"))

    def test_rejects_uppercase(self):
        self.assertFalse(ids.is_uuid_like("2F1C9A3E-4B5D-4E6F-8A90-1234567890AB"))

    def test_rejects_short(self):
        self.assertFalse(ids.is_uuid_like("2f1c9a3e"))

    def test_rejects_non_string(self):
        self.assertFalse(ids.is_uuid_like(None))


class DeriveIdTests(DomainTestCase):
    def test_is_stable(self):
        self.assertEqual(ids.derive_id("job", 1, "a"), ids.derive_id("job", 1, "a"))

    def test_depends_on_namespace(self):
        self.assertNotEqual(ids.derive_id("job", 1), ids.derive_id("task", 1))

    def test_depends_on_part_order(self):
        self.assertNotEqual(ids.derive_id("job", "a", "b"), ids.derive_id("job", "b", "a"))

    def test_separator_prevents_collisions(self):
        self.assertNotEqual(ids.derive_id("job", "ab", "c"), ids.derive_id("job", "a", "bc"))

    def test_length(self):
        self.assertEqual(32, len(ids.derive_id("job", 1)))

    def test_namespace_is_required(self):
        self.assertField("namespace", ids.derive_id, "")


class ShortIdTests(DomainTestCase):
    def test_length(self):
        self.assertEqual(10, len(ids.short_id("job", 1)))

    def test_custom_length(self):
        self.assertEqual(16, len(ids.short_id("job", 1, length=16)))

    def test_alphabet_is_unambiguous(self):
        value = ids.short_id("job", "seed", length=26)
        self.assertNotIn("l", value)
        self.assertNotIn("o", value)
        self.assertNotIn("0", value)
        self.assertNotIn("1", value)

    def test_is_stable(self):
        self.assertEqual(ids.short_id("job", 1), ids.short_id("job", 1))

    def test_too_short_is_rejected(self):
        self.assertField("length", ids.short_id, "job", length=3)

    def test_too_long_is_rejected(self):
        self.assertField("length", ids.short_id, "job", length=27)


class ExternalRefTests(DomainTestCase):
    def test_lowercases_provider(self):
        self.assertEqual("paypal", ids.ExternalRef("PayPal", "P-1").provider)

    def test_value_is_not_lowercased(self):
        self.assertEqual("P-1", ids.ExternalRef("paypal", "P-1").value)

    def test_parse(self):
        ref = ids.ExternalRef.parse("podbean:show-9")
        self.assertEqual("podbean", ref.provider)
        self.assertEqual("show-9", ref.value)

    def test_parse_keeps_colons_in_value(self):
        self.assertEqual("a:b", ids.ExternalRef.parse("x:a:b").value)

    def test_parse_requires_separator(self):
        self.assertField("ref", ids.ExternalRef.parse, "nope")

    def test_to_string_round_trips(self):
        ref = ids.ExternalRef("paypal", "P-1")
        self.assertEqual(ref, ids.ExternalRef.parse(ref.to_string()))

    def test_to_dict(self):
        self.assertEqual(
            {"provider": "paypal", "value": "P-1"},
            ids.ExternalRef("paypal", "P-1").to_dict(),
        )

    def test_equality(self):
        self.assertEqual(ids.ExternalRef("a", "b"), ids.ExternalRef("a", "b"))

    def test_hashable(self):
        self.assertEqual(1, len({ids.ExternalRef("a", "b"), ids.ExternalRef("a", "b")}))

    def test_repr(self):
        self.assertIn("ExternalRef", repr(ids.ExternalRef("a", "b")))

    def test_empty_value_is_rejected(self):
        self.assertField("value", ids.ExternalRef, "paypal", "")


class ChecksumTests(DomainTestCase):
    def test_string_and_bytes_agree(self):
        self.assertEqual(ids.checksum("abc"), ids.checksum(b"abc"))

    def test_length(self):
        self.assertEqual(64, len(ids.checksum("abc")))

    def test_rejects_other_types(self):
        self.assertField("data", ids.checksum, 1)


class IdempotencyKeyTests(DomainTestCase):
    def test_is_stable(self):
        self.assertEqual(
            ids.idempotency_key("publish", "u-1", "e-1"),
            ids.idempotency_key("publish", "u-1", "e-1"),
        )

    def test_differs_by_actor(self):
        self.assertNotEqual(
            ids.idempotency_key("publish", "u-1"),
            ids.idempotency_key("publish", "u-2"),
        )

    def test_length(self):
        self.assertEqual(16, len(ids.idempotency_key("publish", "u-1")))
