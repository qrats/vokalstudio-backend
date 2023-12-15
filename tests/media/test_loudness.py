from src.domain.media import loudness as mod
from tests.support import DomainTestCase


class TargetTests(DomainTestCase):
    def test_podcast(self):
        self.assertEqual(-16.0, mod.target_for("podcast"))

    def test_broadcast(self):
        self.assertEqual(-23.0, mod.target_for("broadcast"))

    def test_unknown_profile(self):
        error = self.assertRaisesCode("validation_failed", mod.target_for, "cinema")
        self.assertIn("podcast", error.details["allowed"])

    def test_field_name(self):
        self.assertField("delivery", mod.target_for, "cinema", "delivery")

    def test_default_profile_is_known(self):
        self.assertIn(mod.DEFAULT_TARGET, mod.TARGETS)


class GainTests(DomainTestCase):
    def test_quiet_material_needs_positive_gain(self):
        self.assertEqual(4.0, mod.gain_to_target(-20.0))

    def test_loud_material_needs_negative_gain(self):
        self.assertEqual(-2.0, mod.gain_to_target(-14.0))

    def test_already_on_target(self):
        self.assertEqual(0.0, mod.gain_to_target(-16.0))

    def test_other_profile(self):
        self.assertEqual(-3.0, mod.gain_to_target(-20.0, "broadcast"))

    def test_rounds_to_two_places(self):
        self.assertEqual(3.33, mod.gain_to_target(-19.33))

    def test_too_quiet_is_rejected(self):
        self.assertField("measured_lufs", mod.gain_to_target, -71.0)

    def test_positive_lufs_is_rejected(self):
        self.assertField("measured_lufs", mod.gain_to_target, 1.0)


class ClampTests(DomainTestCase):
    def test_gain_fits_under_the_ceiling(self):
        self.assertEqual(2.0, mod.clamp_gain(2.0, -6.0))

    def test_gain_is_reduced_to_the_headroom(self):
        self.assertEqual(2.0, mod.clamp_gain(6.0, -3.0))

    def test_exactly_at_the_ceiling(self):
        self.assertEqual(2.0, mod.clamp_gain(2.0, -3.0))

    def test_negative_gain_is_untouched(self):
        self.assertEqual(-4.0, mod.clamp_gain(-4.0, -0.5))

    def test_custom_ceiling(self):
        self.assertEqual(1.0, mod.clamp_gain(6.0, -3.0, -2.0))

    def test_gain_beyond_the_maximum(self):
        self.assertField("gain_db", mod.clamp_gain, 13.0, -6.0)

    def test_ceiling_above_zero_is_rejected(self):
        self.assertField("ceiling", mod.clamp_gain, 1.0, -6.0, 1.0)


class PlanTests(DomainTestCase):
    def test_headroom_allows_the_full_gain(self):
        plan = mod.normalisation_plan(-20.0, -8.0)
        self.assertEqual(4.0, plan["applied_gain_db"])
        self.assertEqual(-16.0, plan["resulting_lufs"])
        self.assertFalse(plan["limited"])
        self.assertTrue(plan["on_target"])

    def test_peak_limits_the_gain(self):
        plan = mod.normalisation_plan(-20.0, -3.0)
        self.assertEqual(2.0, plan["applied_gain_db"])
        self.assertTrue(plan["limited"])
        self.assertFalse(plan["on_target"])

    def test_attenuation_is_never_limited(self):
        plan = mod.normalisation_plan(-10.0, -0.5)
        self.assertEqual(-6.0, plan["applied_gain_db"])
        self.assertFalse(plan["limited"])

    def test_wanted_gain_is_reported_unclamped(self):
        plan = mod.normalisation_plan(-40.0, -0.5)
        self.assertEqual(24.0, plan["wanted_gain_db"])

    def test_gain_is_capped_at_the_maximum(self):
        plan = mod.normalisation_plan(-40.0, -30.0)
        self.assertEqual(12.0, plan["applied_gain_db"])

    def test_profile_is_reported(self):
        plan = mod.normalisation_plan(-20.0, -8.0, "broadcast")
        self.assertEqual("broadcast", plan["profile"])
        self.assertEqual(-23.0, plan["target_lufs"])

    def test_measured_value_is_echoed(self):
        self.assertEqual(-20.0, mod.normalisation_plan(-20.0, -8.0)["measured_lufs"])

    def test_unknown_profile(self):
        self.assertField("profile", mod.normalisation_plan, -20.0, -8.0, "cinema")


class ToleranceTests(DomainTestCase):
    def test_inside(self):
        self.assertTrue(mod.is_within_tolerance(-16.5))

    def test_on_the_boundary(self):
        self.assertTrue(mod.is_within_tolerance(-17.0))

    def test_outside(self):
        self.assertFalse(mod.is_within_tolerance(-18.0))

    def test_custom_tolerance(self):
        self.assertTrue(mod.is_within_tolerance(-18.0, tolerance=2.0))

    def test_other_profile(self):
        self.assertTrue(mod.is_within_tolerance(-23.0, "broadcast"))

    def test_tolerance_ceiling(self):
        self.assertField("tolerance", mod.is_within_tolerance, -16.0, "podcast", 7.0)


class LoudestTests(DomainTestCase):
    def test_picks_the_least_negative(self):
        self.assertEqual(("b", -12.0), mod.loudest([("a", -20.0), ("b", -12.0)]))

    def test_empty(self):
        self.assertIsNone(mod.loudest([]))

    def test_default(self):
        self.assertEqual("x", mod.loudest([], "x"))
