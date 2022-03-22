from src.domain.money import rounding as mod
from tests.support import DomainTestCase


class ModeTests(DomainTestCase):
    def test_known_mode(self):
        self.assertEqual(mod.HALF_UP, mod.validate_mode(mod.HALF_UP))

    def test_unknown_mode(self):
        self.assertField("mode", mod.validate_mode, "nearest")

    def test_all_modes_validate(self):
        for mode in mod.MODES:
            self.assertEqual(mode, mod.validate_mode(mode))


class RoundDivisionTests(DomainTestCase):
    def test_exact(self):
        self.assertEqual(3, mod.round_division(9, 3))

    def test_half_up_rounds_away(self):
        self.assertEqual(3, mod.round_division(5, 2, mod.HALF_UP))

    def test_half_up_negative_rounds_away_from_zero(self):
        self.assertEqual(-3, mod.round_division(-5, 2, mod.HALF_UP))

    def test_half_even_to_even(self):
        self.assertEqual(2, mod.round_division(5, 2, mod.HALF_EVEN))

    def test_half_even_other_side(self):
        self.assertEqual(4, mod.round_division(7, 2, mod.HALF_EVEN))

    def test_below_half_rounds_down(self):
        self.assertEqual(2, mod.round_division(9, 4, mod.HALF_UP))

    def test_above_half_rounds_up(self):
        self.assertEqual(3, mod.round_division(11, 4, mod.HALF_UP))

    def test_floor(self):
        self.assertEqual(2, mod.round_division(29, 10, mod.FLOOR))

    def test_floor_negative(self):
        self.assertEqual(-3, mod.round_division(-29, 10, mod.FLOOR))

    def test_ceiling(self):
        self.assertEqual(3, mod.round_division(21, 10, mod.CEILING))

    def test_down_truncates_towards_zero(self):
        self.assertEqual(2, mod.round_division(29, 10, mod.DOWN))

    def test_down_negative_truncates_towards_zero(self):
        self.assertEqual(-2, mod.round_division(-29, 10, mod.DOWN))

    def test_up_away_from_zero(self):
        self.assertEqual(3, mod.round_division(21, 10, mod.UP))

    def test_up_negative_away_from_zero(self):
        self.assertEqual(-3, mod.round_division(-21, 10, mod.UP))

    def test_negative_denominator_is_normalised(self):
        self.assertEqual(-3, mod.round_division(5, -2, mod.HALF_UP))

    def test_zero_denominator(self):
        self.assertField("denominator", mod.round_division, 1, 0)

    def test_unknown_mode(self):
        self.assertField("mode", mod.round_division, 1, 2, "nearest")


class ApplyRateTests(DomainTestCase):
    def test_simple_percentage(self):
        self.assertEqual(20, mod.apply_rate(100, 0.2))

    def test_rounds_half_up(self):
        self.assertEqual(2, mod.apply_rate(15, 0.1))

    def test_floor_mode(self):
        self.assertEqual(1, mod.apply_rate(15, 0.1, mod.FLOOR))

    def test_zero_rate(self):
        self.assertEqual(0, mod.apply_rate(100, 0))

    def test_rate_above_one(self):
        self.assertEqual(250, mod.apply_rate(100, 2.5))

    def test_non_integer_units(self):
        self.assertField("units", mod.apply_rate, 1.5, 0.2)

    def test_bool_units(self):
        self.assertField("units", mod.apply_rate, True, 0.2)
