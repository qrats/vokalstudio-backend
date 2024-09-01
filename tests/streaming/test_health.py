from src.domain.streaming import health as mod
from tests.support import DomainTestCase


class SignalTests(DomainTestCase):
    def test_healthy(self):
        self.assertEqual(mod.HEALTHY, mod.rate_signal("dropped_frames_percent", 0.2))

    def test_degraded_on_the_boundary(self):
        self.assertEqual(mod.DEGRADED, mod.rate_signal("dropped_frames_percent", 1.0))

    def test_unhealthy_on_the_boundary(self):
        self.assertEqual(mod.UNHEALTHY, mod.rate_signal("dropped_frames_percent", 5.0))

    def test_just_below_degraded(self):
        self.assertEqual(mod.HEALTHY, mod.rate_signal("dropped_frames_percent", 0.999))

    def test_round_trip_time(self):
        self.assertEqual(mod.DEGRADED, mod.rate_signal("round_trip_millis", 200))

    def test_buffer_fill(self):
        self.assertEqual(mod.UNHEALTHY, mod.rate_signal("buffer_fill_percent", 95))

    def test_unknown_signal(self):
        error = self.assertRaisesCode("validation_failed", mod.rate_signal, "jitter", 1)
        self.assertIn("round_trip_millis", error.details["known"])

    def test_negative_reading(self):
        self.assertField("dropped_frames_percent", mod.rate_signal, "dropped_frames_percent", -1)

    def test_thresholds_increase(self):
        for name, (warn, fail) in mod.THRESHOLDS.items():
            self.assertLess(warn, fail, name)


class WorstTests(DomainTestCase):
    def test_picks_the_most_severe(self):
        self.assertEqual(mod.UNHEALTHY, mod.worst([mod.HEALTHY, mod.UNHEALTHY]))

    def test_degraded_beats_healthy(self):
        self.assertEqual(mod.DEGRADED, mod.worst([mod.HEALTHY, mod.DEGRADED]))

    def test_empty_is_the_default(self):
        self.assertEqual(mod.HEALTHY, mod.worst([]))

    def test_custom_default(self):
        self.assertEqual(mod.DEGRADED, mod.worst([], mod.DEGRADED))

    def test_unknown_level(self):
        self.assertField("levels", mod.worst, ["broken"])


class AssessTests(DomainTestCase):
    def test_all_healthy(self):
        report = mod.assess({"dropped_frames_percent": 0.1, "round_trip_millis": 40})
        self.assertEqual(mod.HEALTHY, report["status"])
        self.assertEqual((), report["degraded"])

    def test_one_bad_signal_decides(self):
        report = mod.assess(
            {"dropped_frames_percent": 0.1, "buffer_fill_percent": 95}
        )
        self.assertEqual(mod.UNHEALTHY, report["status"])

    def test_degraded_signals_are_listed(self):
        report = mod.assess(
            {"dropped_frames_percent": 2.0, "buffer_fill_percent": 95}
        )
        self.assertEqual(
            ("buffer_fill_percent", "dropped_frames_percent"), report["degraded"]
        )

    def test_signals_are_classified_individually(self):
        report = mod.assess({"dropped_frames_percent": 2.0, "round_trip_millis": 40})
        self.assertEqual(mod.DEGRADED, report["signals"]["dropped_frames_percent"])
        self.assertEqual(mod.HEALTHY, report["signals"]["round_trip_millis"])

    def test_empty_readings(self):
        self.assertEqual(mod.HEALTHY, mod.assess({})["status"])

    def test_unknown_signal(self):
        self.assertField("name", mod.assess, {"jitter": 1})


class ActionTests(DomainTestCase):
    def test_no_reduction_when_healthy(self):
        self.assertFalse(mod.should_reduce_bitrate({"round_trip_millis": 40}))

    def test_reduce_when_degraded(self):
        self.assertTrue(mod.should_reduce_bitrate({"round_trip_millis": 200}))

    def test_healthy_keeps_the_rate(self):
        self.assertEqual(4000, mod.recommended_kbps(4000, {"round_trip_millis": 40}))

    def test_degraded_backs_off_a_quarter(self):
        self.assertEqual(3000, mod.recommended_kbps(4000, {"round_trip_millis": 200}))

    def test_unhealthy_halves(self):
        self.assertEqual(2000, mod.recommended_kbps(4000, {"round_trip_millis": 500}))

    def test_never_below_the_floor(self):
        self.assertEqual(400, mod.recommended_kbps(500, {"round_trip_millis": 500}))

    def test_custom_floor(self):
        self.assertEqual(
            1000, mod.recommended_kbps(1500, {"round_trip_millis": 500}, floor=1000)
        )

    def test_zero_rate_is_rejected(self):
        self.assertField("current_kbps", mod.recommended_kbps, 0, {})
