from src.domain.catalog.entitlement import Entitlement
from src.domain.catalog.feature import UNLIMITED
from src.domain.catalog import quota as mod
from tests.support import DomainTestCase


class UsageTests(DomainTestCase):
    def test_empty(self):
        self.assertEqual(0, mod.Usage().of("streaming.targets"))

    def test_counts(self):
        self.assertEqual(2, mod.Usage({"streaming.targets": 2}).of("streaming.targets"))

    def test_unknown_key(self):
        self.assertField("counts", mod.Usage, {"no.such": 1})

    def test_switch_cannot_be_counted(self):
        self.assertRaisesCode(
            "quota_exceeded", mod.Usage, {"streaming.custom_rtmp": 1}
        )

    def test_negative_count(self):
        self.assertField("streaming.targets", mod.Usage, {"streaming.targets": -1})

    def test_plus(self):
        self.assertEqual(1, mod.Usage().plus("streaming.targets").of("streaming.targets"))

    def test_plus_amount(self):
        self.assertEqual(3, mod.Usage().plus("streaming.targets", 3).of("streaming.targets"))

    def test_plus_returns_a_copy(self):
        usage = mod.Usage()
        usage.plus("streaming.targets")
        self.assertEqual(0, usage.of("streaming.targets"))

    def test_plus_rejects_negative(self):
        self.assertField("amount", mod.Usage().plus, "streaming.targets", -1)

    def test_reset(self):
        usage = mod.Usage({"streaming.targets": 5}).reset("streaming.targets")
        self.assertEqual(0, usage.of("streaming.targets"))

    def test_reset_of_an_untouched_key(self):
        self.assertEqual({}, mod.Usage().reset("streaming.targets").to_dict())

    def test_to_dict(self):
        self.assertEqual({"streaming.targets": 2}, mod.Usage({"streaming.targets": 2}).to_dict())

    def test_equality(self):
        self.assertEqual(mod.Usage({"streaming.targets": 1}), mod.Usage({"streaming.targets": 1}))

    def test_hashable(self):
        self.assertEqual(1, len({mod.Usage(), mod.Usage()}))

    def test_repr(self):
        self.assertIn("Usage", repr(mod.Usage()))


class HeadroomTests(DomainTestCase):
    def setUp(self):
        self.rights = Entitlement({"streaming.targets": 3, "episodes.monthly": 2})
        self.usage = mod.Usage({"streaming.targets": 1, "episodes.monthly": 2})

    def test_headroom(self):
        report = mod.headroom(self.rights, self.usage)
        self.assertEqual(2, report["streaming.targets"])
        self.assertEqual(0, report["episodes.monthly"])

    def test_headroom_skips_switches(self):
        self.assertNotIn("streaming.custom_rtmp", mod.headroom(self.rights, self.usage))

    def test_headroom_of_unlimited_is_none(self):
        rights = Entitlement({"streaming.targets": UNLIMITED})
        self.assertIsNone(mod.headroom(rights, self.usage)["streaming.targets"])

    def test_exhausted(self):
        self.assertIn("episodes.monthly", mod.exhausted(self.rights, self.usage))

    def test_not_exhausted(self):
        self.assertNotIn("streaming.targets", mod.exhausted(self.rights, self.usage))

    def test_exhausted_is_sorted(self):
        found = mod.exhausted(Entitlement(), mod.Usage())
        self.assertEqual(tuple(sorted(found)), found)


class UtilisationTests(DomainTestCase):
    def test_percentage(self):
        rights = Entitlement({"streaming.targets": 4})
        report = mod.utilisation(rights, mod.Usage({"streaming.targets": 1}))
        self.assertEqual(25.0, report["streaming.targets"])

    def test_over_a_hundred_percent(self):
        rights = Entitlement({"streaming.targets": 2})
        report = mod.utilisation(rights, mod.Usage({"streaming.targets": 3}))
        self.assertEqual(150.0, report["streaming.targets"])

    def test_unlimited_is_omitted(self):
        rights = Entitlement({"streaming.targets": UNLIMITED})
        self.assertNotIn("streaming.targets", mod.utilisation(rights, mod.Usage()))

    def test_zero_allowance_is_omitted(self):
        rights = Entitlement({"streaming.targets": 0})
        self.assertNotIn("streaming.targets", mod.utilisation(rights, mod.Usage()))

    def test_switches_are_omitted(self):
        self.assertNotIn(
            "streaming.custom_rtmp", mod.utilisation(Entitlement(), mod.Usage())
        )

    def test_rounds_to_two_places(self):
        rights = Entitlement({"streaming.targets": 3})
        report = mod.utilisation(rights, mod.Usage({"streaming.targets": 1}))
        self.assertEqual(33.33, report["streaming.targets"])
