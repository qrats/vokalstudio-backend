from src.domain.adapters import rows as mod
from tests.support import DomainTestCase


class Row:
    def __init__(self, **values):
        for name, value in values.items():
            setattr(self, name, value)

    def save(self):
        return None


class FieldTests(DomainTestCase):
    def test_reads_a_mapping(self):
        self.assertEqual(1, mod.field({"a": 1}, "a"))

    def test_reads_an_object(self):
        self.assertEqual(1, mod.field(Row(a=1), "a"))

    def test_missing_key_raises(self):
        error = self.assertRaisesCode("validation_failed", mod.field, {"a": 1}, "b")
        self.assertEqual(["a"], error.details["available"])

    def test_missing_attribute_raises(self):
        self.assertField("b", mod.field, Row(a=1), "b")

    def test_default_is_returned(self):
        self.assertEqual("x", mod.field({}, "b", "x"))

    def test_none_stored_is_returned(self):
        self.assertIsNone(mod.field({"a": None}, "a", "x"))

    def test_default_none_is_allowed(self):
        self.assertIsNone(mod.field({}, "b", None))


class HasTests(DomainTestCase):
    def test_mapping_key(self):
        self.assertTrue(mod.has({"a": 1}, "a"))

    def test_missing_mapping_key(self):
        self.assertFalse(mod.has({"a": 1}, "b"))

    def test_object_attribute(self):
        self.assertTrue(mod.has(Row(a=1), "a"))

    def test_missing_attribute(self):
        self.assertFalse(mod.has(Row(a=1), "b"))


class AvailableTests(DomainTestCase):
    def test_mapping_keys_are_sorted(self):
        self.assertEqual(["a", "b"], mod.available({"b": 2, "a": 1}))

    def test_object_attributes(self):
        self.assertEqual(["a"], mod.available(Row(a=1)))

    def test_methods_are_excluded(self):
        self.assertNotIn("save", mod.available(Row(a=1)))

    def test_private_names_are_excluded(self):
        row = Row(a=1)
        row._hidden = 2
        self.assertNotIn("_hidden", mod.available(row))


class PickTests(DomainTestCase):
    def test_reads_several(self):
        self.assertEqual({"a": 1, "b": 2}, mod.pick({"a": 1, "b": 2}, "a", "b"))

    def test_defaults(self):
        self.assertEqual({"a": 1, "c": "x"}, mod.pick({"a": 1}, "a", "c", c="x"))

    def test_missing_without_a_default(self):
        self.assertField("c", mod.pick, {"a": 1}, "c")

    def test_no_names(self):
        self.assertEqual({}, mod.pick({"a": 1}))


class RequireFieldsTests(DomainTestCase):
    def test_returns_the_row(self):
        row = {"a": 1, "b": 2}
        self.assertIs(row, mod.require_fields(row, "a", "b"))

    def test_lists_what_is_missing(self):
        error = self.assertRaisesCode(
            "validation_failed", mod.require_fields, {"a": 1}, "b", "c"
        )
        self.assertEqual(["b", "c"], error.details["missing"])

    def test_nothing_required(self):
        self.assertEqual({}, mod.require_fields({}))


class RenameTests(DomainTestCase):
    def test_maps_names(self):
        found = mod.rename({"user_id": "u-1"}, {"owner_id": "user_id"})
        self.assertEqual({"owner_id": "u-1"}, found)

    def test_defaults(self):
        found = mod.rename({}, {"owner_id": "user_id"}, {"owner_id": "anon"})
        self.assertEqual("anon", found["owner_id"])

    def test_missing_without_a_default(self):
        self.assertField("user_id", mod.rename, {}, {"owner_id": "user_id"})

    def test_empty_mapping(self):
        self.assertEqual({}, mod.rename({"a": 1}, {}))


class CoalesceTests(DomainTestCase):
    def test_first_present(self):
        self.assertEqual(1, mod.coalesce({"a": 1, "b": 2}, "a", "b"))

    def test_falls_through(self):
        self.assertEqual(2, mod.coalesce({"b": 2}, "a", "b"))

    def test_skips_none(self):
        self.assertEqual(2, mod.coalesce({"a": None, "b": 2}, "a", "b"))

    def test_default(self):
        self.assertEqual("x", mod.coalesce({}, "a", "b", default="x"))

    def test_default_is_none(self):
        self.assertIsNone(mod.coalesce({}, "a"))
