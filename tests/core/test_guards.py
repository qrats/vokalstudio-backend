from src.domain.core import guards
from tests.support import DomainTestCase


class RequireTextTests(DomainTestCase):
    def test_returns_trimmed(self):
        self.assertEqual("Vokal", guards.require_text("  Vokal  ", "name"))

    def test_keeps_padding_when_strip_disabled(self):
        self.assertEqual(" a ", guards.require_text(" a ", "name", strip=False))

    def test_none_is_rejected(self):
        self.assertField("name", guards.require_text, None, "name")

    def test_non_string_is_rejected(self):
        error = self.assertRaisesCode("validation_failed", guards.require_text, 7, "name")
        self.assertIn("int", error.message)

    def test_empty_after_strip_is_rejected(self):
        self.assertField("name", guards.require_text, "   ", "name")

    def test_min_length(self):
        self.assertField("name", guards.require_text, "ab", "name", 3)

    def test_min_length_boundary(self):
        self.assertEqual("abc", guards.require_text("abc", "name", 3))

    def test_max_length(self):
        self.assertField("name", guards.require_text, "abcd", "name", 1, 3)

    def test_max_length_boundary(self):
        self.assertEqual("abc", guards.require_text("abc", "name", 1, 3))

    def test_zero_min_length_allows_empty(self):
        self.assertEqual("", guards.require_text("", "name", min_length=0))


class RequireIntTests(DomainTestCase):
    def test_passes_through_int(self):
        self.assertEqual(5, guards.require_int(5, "count"))

    def test_parses_string(self):
        self.assertEqual(-12, guards.require_int(" -12 ", "count"))

    def test_bool_is_rejected(self):
        self.assertField("count", guards.require_int, True, "count")

    def test_float_is_rejected(self):
        self.assertField("count", guards.require_int, 1.5, "count")

    def test_garbage_string_is_rejected(self):
        self.assertField("count", guards.require_int, "ten", "count")

    def test_empty_string_is_rejected(self):
        self.assertField("count", guards.require_int, "  ", "count")

    def test_minimum(self):
        self.assertField("count", guards.require_int, 0, "count", 1)

    def test_minimum_boundary(self):
        self.assertEqual(1, guards.require_int(1, "count", 1))

    def test_maximum(self):
        self.assertField("count", guards.require_int, 11, "count", None, 10)

    def test_maximum_boundary(self):
        self.assertEqual(10, guards.require_int(10, "count", None, 10))


class RequireNumberTests(DomainTestCase):
    def test_int_becomes_float(self):
        value = guards.require_number(3, "gain")
        self.assertIsInstance(value, float)
        self.assertEqual(3.0, value)

    def test_parses_string(self):
        self.assertEqual(-1.5, guards.require_number("-1.5", "gain"))

    def test_nan_is_rejected(self):
        self.assertField("gain", guards.require_number, "nan", "gain")

    def test_bool_is_rejected(self):
        self.assertField("gain", guards.require_number, False, "gain")

    def test_range_is_enforced(self):
        self.assertField("gain", guards.require_number, 1.0, "gain", -0.5, 0.5)

    def test_range_boundaries_pass(self):
        self.assertEqual(0.5, guards.require_number(0.5, "gain", -0.5, 0.5))


class RequireBoolTests(DomainTestCase):
    def test_bool_passes(self):
        self.assertTrue(guards.require_bool(True, "enabled"))

    def test_truthy_strings(self):
        for text in ("true", "YES", " on ", "1"):
            self.assertTrue(guards.require_bool(text, "enabled"), text)

    def test_falsey_strings(self):
        for text in ("false", "No", "OFF", "0"):
            self.assertFalse(guards.require_bool(text, "enabled"), text)

    def test_other_values_are_rejected(self):
        self.assertField("enabled", guards.require_bool, "maybe", "enabled")

    def test_int_is_rejected(self):
        self.assertField("enabled", guards.require_bool, 1, "enabled")


class RequireChoiceTests(DomainTestCase):
    def test_normalizes_case(self):
        self.assertEqual("draft", guards.require_choice("DRAFT", "state", {"draft"}))

    def test_rejects_unknown(self):
        error = self.assertRaisesCode(
            "validation_failed", guards.require_choice, "gone", "state", {"draft", "live"}
        )
        self.assertEqual(["draft", "live"], error.details["allowed"])
        self.assertEqual("gone", error.details["given"])

    def test_normalization_can_be_disabled(self):
        self.assertField(
            "state", guards.require_choice, "DRAFT", "state", {"draft"}, False
        )

    def test_non_string_choices(self):
        self.assertEqual(3, guards.require_choice(3, "size", {1, 2, 3}))


class RequireMappingTests(DomainTestCase):
    def test_returns_a_copy(self):
        given = {"a": 1}
        result = guards.require_mapping(given, "payload")
        result["a"] = 2
        self.assertEqual(1, given["a"])

    def test_rejects_non_dict(self):
        self.assertField("payload", guards.require_mapping, [], "payload")

    def test_required_keys(self):
        error = self.assertRaisesCode(
            "validation_failed", guards.require_mapping, {"a": 1}, "payload", ["a", "b"]
        )
        self.assertEqual(["b"], error.details["missing"])

    def test_all_keys_present(self):
        self.assertEqual({"a": 1}, guards.require_mapping({"a": 1}, "payload", ["a"]))


class RequireSequenceTests(DomainTestCase):
    def test_returns_tuple(self):
        self.assertEqual((1, 2), guards.require_sequence([1, 2], "items"))

    def test_string_is_rejected(self):
        self.assertField("items", guards.require_sequence, "ab", "items")

    def test_none_is_rejected(self):
        self.assertField("items", guards.require_sequence, None, "items")

    def test_min_length(self):
        self.assertField("items", guards.require_sequence, [], "items", 1)

    def test_max_length(self):
        self.assertField("items", guards.require_sequence, [1, 2], "items", 0, 1)

    def test_generator_is_accepted(self):
        self.assertEqual((0, 1), guards.require_sequence(iter(range(2)), "items"))


class ForbidUnknownTests(DomainTestCase):
    def test_accepts_declared_keys(self):
        self.assertEqual({"a": 1}, guards.forbid_unknown({"a": 1}, "payload", ["a", "b"]))

    def test_rejects_extra_keys(self):
        error = self.assertRaisesCode(
            "validation_failed", guards.forbid_unknown, {"a": 1, "z": 2}, "payload", ["a"]
        )
        self.assertEqual(["z"], error.details["unknown"])
