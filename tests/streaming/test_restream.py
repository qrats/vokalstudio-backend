from src.domain.catalog.entitlement import Entitlement
from src.domain.streaming import restream as mod
from src.domain.streaming.target import StreamTarget
from tests.support import DomainTestCase

KEY = "abcdefghijklmnopqrstuvwx"


def youtube(enabled=True):
    return StreamTarget("u-1", "youtube", KEY, enabled=enabled)


def facebook(enabled=True):
    return StreamTarget("u-1", "facebook", KEY, enabled=enabled)


def twitch(enabled=True):
    return StreamTarget("u-1", "twitch", KEY, enabled=enabled)


def custom(host="my.host.test"):
    return StreamTarget("u-1", "custom", "abcdefgh", "rtmp://{}/live".format(host))


class PlanTests(DomainTestCase):
    def test_everything_included(self):
        plan = mod.build_plan([youtube(), twitch()], 3000)
        self.assertEqual(2, len(plan))

    def test_disabled_is_skipped(self):
        plan = mod.build_plan([youtube(enabled=False)], 3000)
        self.assertEqual(mod.SKIPPED_DISABLED, plan.decisions[0][1])

    def test_bitrate_cap_is_respected(self):
        plan = mod.build_plan([facebook()], 9000)
        self.assertEqual(mod.SKIPPED_BITRATE, plan.decisions[0][1])

    def test_plan_limit(self):
        rights = Entitlement({"streaming.targets": 1})
        plan = mod.build_plan([youtube(), twitch()], 3000, rights)
        self.assertEqual(1, len(plan))
        self.assertEqual(mod.SKIPPED_LIMIT, plan.decisions[1][1])

    def test_unlimited_targets(self):
        rights = Entitlement({"streaming.targets": -1, "streaming.custom_rtmp": True})
        plan = mod.build_plan([youtube(), twitch(), custom()], 3000, rights)
        self.assertEqual(3, len(plan))

    def test_custom_needs_the_feature(self):
        rights = Entitlement({"streaming.targets": 5, "streaming.custom_rtmp": False})
        plan = mod.build_plan([custom()], 3000, rights)
        self.assertEqual(mod.SKIPPED_FEATURE, plan.decisions[0][1])

    def test_custom_with_the_feature(self):
        rights = Entitlement({"streaming.targets": 5, "streaming.custom_rtmp": True})
        self.assertEqual(1, len(mod.build_plan([custom()], 3000, rights)))

    def test_no_entitlement_allows_everything(self):
        self.assertEqual(1, len(mod.build_plan([custom()], 3000)))

    def test_skipped_targets_do_not_consume_the_limit(self):
        rights = Entitlement({"streaming.targets": 1})
        plan = mod.build_plan([youtube(enabled=False), twitch()], 3000, rights)
        self.assertEqual(1, len(plan))
        self.assertEqual(mod.INCLUDED, plan.decisions[1][1])

    def test_zero_kbps_is_rejected(self):
        self.assertField("kbps", mod.build_plan, [], 0)


class PlanQueryTests(DomainTestCase):
    def setUp(self):
        self.plan = mod.build_plan([youtube(), facebook(), twitch()], 5000)

    def test_included(self):
        self.assertEqual(2, len(self.plan.included))

    def test_skipped(self):
        self.assertEqual(1, len(self.plan.skipped))

    def test_reason_for(self):
        self.assertEqual(
            mod.SKIPPED_BITRATE, self.plan.reason_for(facebook().reference)
        )

    def test_reason_for_an_unknown_reference(self):
        self.assertIsNone(self.plan.reason_for("nope"))

    def test_total_egress(self):
        self.assertEqual(10000, self.plan.total_egress_kbps())

    def test_is_not_empty(self):
        self.assertFalse(self.plan.is_empty())

    def test_empty_plan(self):
        self.assertTrue(mod.build_plan([], 3000).is_empty())

    def test_to_dict(self):
        payload = self.plan.to_dict()
        self.assertEqual(2, len(payload["included"]))
        self.assertEqual("bitrate_exceeds_platform", payload["skipped"][0]["reason"])

    def test_len(self):
        self.assertEqual(2, len(self.plan))

    def test_equality(self):
        self.assertEqual(self.plan, mod.build_plan([youtube(), facebook(), twitch()], 5000))

    def test_hashable(self):
        self.assertEqual(1, len({self.plan, self.plan}))

    def test_repr(self):
        self.assertIn("2 of 3", repr(self.plan))


class CommonRateTests(DomainTestCase):
    def test_lowest_cap_wins(self):
        self.assertEqual(4000, mod.highest_common_kbps([youtube(), facebook()]))

    def test_ignores_disabled(self):
        self.assertEqual(51000, mod.highest_common_kbps([youtube(), facebook(False)]))

    def test_nothing_enabled(self):
        self.assertIsNone(mod.highest_common_kbps([facebook(False)]))

    def test_no_targets(self):
        self.assertIsNone(mod.highest_common_kbps([]))

    def test_unreachable_at(self):
        found = mod.unreachable_at([youtube(), facebook()], 5000)
        self.assertEqual(1, len(found))

    def test_nothing_unreachable(self):
        self.assertEqual((), mod.unreachable_at([youtube(), facebook()], 3000))

    def test_unreachable_ignores_disabled(self):
        self.assertEqual((), mod.unreachable_at([facebook(False)], 9000))


class ReasonTests(DomainTestCase):
    def test_every_reason_is_described(self):
        for reason in mod.REASONS:
            self.assertTrue(mod.describe_reason(reason))

    def test_unknown_reason(self):
        self.assertField("reason", mod.describe_reason, "because")
