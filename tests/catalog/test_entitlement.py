from src.domain.catalog import entitlement as mod
from src.domain.catalog.feature import UNLIMITED
from src.domain.catalog.plan import BillingCycle, Plan
from src.domain.catalog.product import Product
from src.domain.money.amount import Money
from tests.support import DomainTestCase

PRODUCT = Product("PRO", "Everything the studio offers.")


def plan(grants):
    return Plan("PRO", PRODUCT, [BillingCycle(Money.from_major("99.00"))], grants)


class ConstructionTests(DomainTestCase):
    def test_free_uses_catalogue_defaults(self):
        self.assertEqual(1, mod.Entitlement.free().limit("streaming.targets"))

    def test_overrides_are_applied(self):
        self.assertEqual(5, mod.Entitlement({"streaming.targets": 5}).limit("streaming.targets"))

    def test_unknown_key(self):
        self.assertField("values", mod.Entitlement, {"no.such": 1})

    def test_values_are_coerced(self):
        self.assertEqual(5, mod.Entitlement({"streaming.targets": "5"}).limit("streaming.targets"))

    def test_for_plan(self):
        rights = mod.Entitlement.for_plan(plan({"streaming.targets": 4}))
        self.assertEqual(4, rights.limit("streaming.targets"))

    def test_for_plan_with_overrides(self):
        rights = mod.Entitlement.for_plan(
            plan({"streaming.targets": 4}), {"streaming.targets": 9}
        )
        self.assertEqual(9, rights.limit("streaming.targets"))

    def test_for_plan_keeps_untouched_defaults(self):
        rights = mod.Entitlement.for_plan(plan({"streaming.targets": 4}))
        self.assertEqual(5, rights.limit("media.storage_gb"))


class AccessorTests(DomainTestCase):
    def setUp(self):
        self.rights = mod.Entitlement(
            {"streaming.custom_rtmp": True, "streaming.targets": 3}
        )

    def test_value(self):
        self.assertEqual(3, self.rights.value("streaming.targets"))

    def test_allows(self):
        self.assertTrue(self.rights.allows("streaming.custom_rtmp"))

    def test_allows_false(self):
        self.assertFalse(self.rights.allows("media.watermark"))

    def test_allows_rejects_a_limit(self):
        self.assertRaisesCode("quota_exceeded", self.rights.allows, "streaming.targets")

    def test_limit(self):
        self.assertEqual(3, self.rights.limit("streaming.targets"))

    def test_limit_rejects_a_switch(self):
        self.assertRaisesCode(
            "quota_exceeded", self.rights.limit, "streaming.custom_rtmp"
        )

    def test_is_unlimited(self):
        unlimited = mod.Entitlement({"streaming.targets": UNLIMITED})
        self.assertTrue(unlimited.is_unlimited("streaming.targets"))

    def test_is_not_unlimited(self):
        self.assertFalse(self.rights.is_unlimited("streaming.targets"))


class RemainingTests(DomainTestCase):
    def setUp(self):
        self.rights = mod.Entitlement({"streaming.targets": 3})

    def test_remaining(self):
        self.assertEqual(1, self.rights.remaining("streaming.targets", 2))

    def test_remaining_never_negative(self):
        self.assertEqual(0, self.rights.remaining("streaming.targets", 9))

    def test_remaining_of_unlimited_is_none(self):
        unlimited = mod.Entitlement({"streaming.targets": UNLIMITED})
        self.assertIsNone(unlimited.remaining("streaming.targets", 100))

    def test_negative_usage_is_rejected(self):
        self.assertField("used", self.rights.remaining, "streaming.targets", -1)


class CheckTests(DomainTestCase):
    def setUp(self):
        self.rights = mod.Entitlement(
            {"streaming.targets": 2, "streaming.custom_rtmp": True}
        )

    def test_switch_on(self):
        self.assertTrue(self.rights.check("streaming.custom_rtmp"))

    def test_switch_off(self):
        error = self.assertRaisesCode("forbidden", self.rights.check, "media.watermark")
        self.assertEqual("media.watermark", error.action)

    def test_within_the_limit(self):
        self.assertTrue(self.rights.check("streaming.targets", used=1))

    def test_exactly_at_the_limit(self):
        error = self.assertRaisesCode(
            "quota_exceeded", self.rights.check, "streaming.targets", 2
        )
        self.assertEqual(2, error.limit)

    def test_wanting_more_than_one(self):
        self.assertRaisesCode(
            "quota_exceeded", self.rights.check, "streaming.targets", 1, 2
        )

    def test_wanting_nothing_always_passes(self):
        self.assertTrue(self.rights.check("streaming.targets", used=2, wanted=0))

    def test_unlimited_always_passes(self):
        unlimited = mod.Entitlement({"streaming.targets": UNLIMITED})
        self.assertTrue(unlimited.check("streaming.targets", used=10 ** 6))

    def test_negative_used_is_rejected(self):
        self.assertField("used", self.rights.check, "streaming.targets", -1)


class MergeTests(DomainTestCase):
    def test_merged_with(self):
        base = mod.Entitlement({"streaming.targets": 1})
        merged = base.merged_with({"streaming.targets": 4})
        self.assertEqual(4, merged.limit("streaming.targets"))

    def test_merge_returns_a_copy(self):
        base = mod.Entitlement({"streaming.targets": 1})
        base.merged_with({"streaming.targets": 4})
        self.assertEqual(1, base.limit("streaming.targets"))

    def test_merge_rejects_unknown_keys(self):
        self.assertField("overrides", mod.Entitlement().merged_with, {"no.such": 1})

    def test_difference(self):
        one = mod.Entitlement({"streaming.targets": 1})
        two = mod.Entitlement({"streaming.targets": 4})
        self.assertEqual({"streaming.targets": (1, 4)}, one.difference(two))

    def test_no_difference(self):
        self.assertEqual({}, mod.Entitlement().difference(mod.Entitlement()))


class ValueSemanticsTests(DomainTestCase):
    def test_to_dict_covers_every_feature(self):
        self.assertIn("media.storage_gb", mod.Entitlement().to_dict())

    def test_equality(self):
        self.assertEqual(mod.Entitlement(), mod.Entitlement())

    def test_inequality(self):
        self.assertNotEqual(mod.Entitlement(), mod.Entitlement({"streaming.targets": 9}))

    def test_hashable(self):
        self.assertEqual(1, len({mod.Entitlement(), mod.Entitlement()}))

    def test_repr(self):
        self.assertIn("Entitlement", repr(mod.Entitlement()))
