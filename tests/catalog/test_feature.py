from src.domain.catalog import feature as mod
from tests.support import DomainTestCase


class FeatureTests(DomainTestCase):
    def test_key_is_lowercased(self):
        self.assertEqual("a.b", mod.Feature("A.B", mod.SWITCH).key)

    def test_label_defaults_to_key(self):
        self.assertEqual("a.b", mod.Feature("a.b", mod.SWITCH).label)

    def test_switch_default_is_false(self):
        self.assertFalse(mod.Feature("a.b", mod.SWITCH).default)

    def test_limit_default_is_zero(self):
        self.assertEqual(0, mod.Feature("a.b", mod.LIMIT).default)

    def test_explicit_switch_default(self):
        self.assertTrue(mod.Feature("a.b", mod.SWITCH, default=True).default)

    def test_switch_rejects_a_number(self):
        self.assertField("a.b", mod.Feature, "a.b", mod.SWITCH, None, 1)

    def test_limit_rejects_a_bool(self):
        self.assertField("a.b", mod.Feature, "a.b", mod.LIMIT, None, True)

    def test_limit_rejects_below_unlimited(self):
        self.assertField("a.b", mod.Feature, "a.b", mod.LIMIT, None, -2)

    def test_unknown_kind(self):
        self.assertField("kind", mod.Feature, "a.b", "counter")

    def test_coerce_switch(self):
        self.assertTrue(mod.Feature("a.b", mod.SWITCH).coerce(True))

    def test_coerce_limit_parses_text(self):
        self.assertEqual(4, mod.Feature("a.b", mod.LIMIT).coerce("4"))

    def test_is_unlimited(self):
        self.assertTrue(mod.Feature("a.b", mod.LIMIT).is_unlimited(mod.UNLIMITED))

    def test_switch_is_never_unlimited(self):
        self.assertFalse(mod.Feature("a.b", mod.SWITCH).is_unlimited(True))

    def test_to_dict(self):
        payload = mod.Feature("a.b", mod.LIMIT, "A B", 3).to_dict()
        self.assertEqual({"key": "a.b", "kind": "limit", "label": "A B", "default": 3}, payload)

    def test_equality_is_by_key(self):
        self.assertEqual(mod.Feature("a.b", mod.SWITCH), mod.Feature("a.b", mod.LIMIT))

    def test_hashable(self):
        self.assertEqual(1, len({mod.Feature("a.b", mod.SWITCH)} | {mod.Feature("a.b", mod.SWITCH)}))

    def test_repr(self):
        self.assertIn("a.b", repr(mod.Feature("a.b", mod.SWITCH)))


class CatalogueTests(DomainTestCase):
    def test_lookup(self):
        self.assertEqual("media.storage_gb", mod.lookup("media.storage_gb").key)

    def test_lookup_is_case_insensitive(self):
        self.assertEqual("media.storage_gb", mod.lookup("MEDIA.STORAGE_GB").key)

    def test_unknown_key(self):
        error = self.assertRaisesCode("validation_failed", mod.lookup, "no.such")
        self.assertIn("media.storage_gb", error.details["known"])

    def test_lookup_field_name(self):
        self.assertField("grants", mod.lookup, "no.such", "grants")

    def test_defaults_cover_the_catalogue(self):
        self.assertEqual(len(mod.CATALOGUE), len(mod.default_values()))

    def test_defaults_match_the_features(self):
        defaults = mod.default_values()
        for feature in mod.CATALOGUE:
            self.assertEqual(feature.default, defaults[feature.key])

    def test_switch_keys(self):
        self.assertIn("streaming.custom_rtmp", mod.switch_keys())

    def test_limit_keys(self):
        self.assertIn("streaming.targets", mod.limit_keys())

    def test_keys_do_not_overlap(self):
        self.assertEqual(set(), set(mod.switch_keys()) & set(mod.limit_keys()))

    def test_every_key_is_unique(self):
        keys = [feature.key for feature in mod.CATALOGUE]
        self.assertEqual(len(keys), len(set(keys)))
