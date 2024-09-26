from src.domain.streaming import bandwidth as mod
from src.domain.streaming.restream import build_plan
from src.domain.streaming.target import StreamTarget
from tests.support import DomainTestCase

KEY = "abcdefghijklmnopqrstuvwx"


def plan(kbps=3000, count=2):
    platforms = ["youtube", "twitch"][:count]
    targets = [StreamTarget("u-1", name, KEY) for name in platforms]
    return build_plan(targets, kbps)


class BytesTests(DomainTestCase):
    def test_one_second(self):
        self.assertEqual(125_000, mod.bytes_for(1000, 1000))

    def test_one_minute(self):
        self.assertEqual(125_000 * 60, mod.bytes_for(1000, "01:00"))

    def test_zero_duration(self):
        self.assertEqual(0, mod.bytes_for(1000, 0))

    def test_zero_rate_is_rejected(self):
        self.assertField("kbps", mod.bytes_for, 0, 1000)

    def test_gigabytes_round_up(self):
        self.assertEqual(1, mod.gigabytes_for(1000, "01:00"))

    def test_gigabytes_of_a_long_session(self):
        self.assertEqual(3, mod.gigabytes_for(5000, "01:00:00"))

    def test_gigabytes_of_nothing(self):
        self.assertEqual(0, mod.gigabytes_for(1000, 0))


class EgressTests(DomainTestCase):
    def test_two_targets_double_it(self):
        one = mod.session_egress_bytes(plan(3000, 1), "01:00")
        two = mod.session_egress_bytes(plan(3000, 2), "01:00")
        self.assertEqual(one * 2, two)

    def test_empty_plan(self):
        self.assertEqual(0, mod.session_egress_bytes(build_plan([], 3000), "01:00"))


class FitTests(DomainTestCase):
    def test_fits(self):
        self.assertTrue(mod.fits_upstream(plan(3000, 2), 10000))

    def test_does_not_fit(self):
        self.assertFalse(mod.fits_upstream(plan(3000, 2), 5000))

    def test_fits_exactly(self):
        self.assertTrue(mod.fits_upstream(plan(3000, 2), 6000))

    def test_headroom(self):
        self.assertEqual(4000, mod.headroom_kbps(plan(3000, 2), 10000))

    def test_headroom_never_negative(self):
        self.assertEqual(0, mod.headroom_kbps(plan(3000, 2), 1000))

    def test_zero_upstream_is_rejected(self):
        self.assertField("upstream_kbps", mod.fits_upstream, plan(), 0)


class CapacityTests(DomainTestCase):
    def test_how_many_fit(self):
        self.assertEqual(3, mod.max_targets_for(3000, 10000))

    def test_exact_division(self):
        self.assertEqual(2, mod.max_targets_for(3000, 6000))

    def test_none_fit(self):
        self.assertEqual(0, mod.max_targets_for(3000, 1000))

    def test_zero_rate_is_rejected(self):
        self.assertField("kbps", mod.max_targets_for, 0, 10000)
