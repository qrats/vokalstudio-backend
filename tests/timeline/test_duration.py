from src.domain.timeline import duration as mod
from tests.support import DomainTestCase


class ConstructionTests(DomainTestCase):
    def test_millis(self):
        self.assertEqual(1500, mod.Duration(1500).millis)

    def test_zero(self):
        self.assertTrue(mod.Duration.zero().is_zero())

    def test_negative_is_rejected(self):
        self.assertField("millis", mod.Duration, -1)

    def test_of_seconds(self):
        self.assertEqual(2000, mod.Duration.of_seconds(2).millis)

    def test_of_minutes(self):
        self.assertEqual(120000, mod.Duration.of_minutes(2).millis)

    def test_of_hours(self):
        self.assertEqual(7200000, mod.Duration.of_hours(2).millis)

    def test_negative_seconds_are_rejected(self):
        self.assertField("seconds", mod.Duration.of_seconds, -1)


class ParseTests(DomainTestCase):
    def test_hours_minutes_seconds(self):
        self.assertEqual(3723000, mod.Duration.parse("01:02:03").millis)

    def test_minutes_seconds(self):
        self.assertEqual(123000, mod.Duration.parse("02:03").millis)

    def test_fraction(self):
        self.assertEqual(1500, mod.Duration.parse("00:01.5").millis)

    def test_three_digit_fraction(self):
        self.assertEqual(1250, mod.Duration.parse("00:01.250").millis)

    def test_too_many_parts(self):
        self.assertField("duration", mod.Duration.parse, "1:2:3:4")

    def test_one_part(self):
        self.assertField("duration", mod.Duration.parse, "90")

    def test_non_numeric(self):
        self.assertField("duration", mod.Duration.parse, "aa:bb")

    def test_out_of_range_minutes(self):
        self.assertField("duration", mod.Duration.parse, "01:60:00")

    def test_out_of_range_seconds(self):
        self.assertField("duration", mod.Duration.parse, "01:00:60")

    def test_negative_component(self):
        self.assertField("duration", mod.Duration.parse, "-1:00")

    def test_over_long_fraction(self):
        self.assertField("duration", mod.Duration.parse, "00:01.1234")

    def test_non_digit_fraction(self):
        self.assertField("duration", mod.Duration.parse, "00:01.abc")

    def test_field_name(self):
        self.assertField("length", mod.Duration.parse, "x", "length")


class AccessorTests(DomainTestCase):
    def test_seconds_truncate(self):
        self.assertEqual(1, mod.Duration(1999).seconds)

    def test_whole_minutes(self):
        self.assertEqual(2, mod.Duration.of_seconds(150).whole_minutes)

    def test_whole_minutes_rounds_down(self):
        self.assertEqual(1, mod.Duration.of_seconds(119).whole_minutes)


class ArithmeticTests(DomainTestCase):
    def test_plus(self):
        self.assertEqual(3000, mod.Duration(1000).plus(mod.Duration(2000)).millis)

    def test_plus_accepts_millis(self):
        self.assertEqual(1500, mod.Duration(1000).plus(500).millis)

    def test_plus_accepts_text(self):
        self.assertEqual(61000, mod.Duration(1000).plus("01:00").millis)

    def test_minus(self):
        self.assertEqual(500, mod.Duration(1500).minus(1000).millis)

    def test_minus_below_zero_is_rejected(self):
        self.assertField("duration", mod.Duration(1).minus, 2)

    def test_times(self):
        self.assertEqual(3000, mod.Duration(1000).times(3).millis)

    def test_times_zero(self):
        self.assertTrue(mod.Duration(1000).times(0).is_zero())

    def test_times_negative_is_rejected(self):
        self.assertField("factor", mod.Duration(1000).times, -1)

    def test_bad_operand_type(self):
        self.assertField("value", mod.Duration(1).plus, None)


class FormatTests(DomainTestCase):
    def test_minutes_and_seconds(self):
        self.assertEqual("02:03", mod.Duration.parse("02:03").format())

    def test_hours_appear_when_needed(self):
        self.assertEqual("01:02:03", mod.Duration.parse("01:02:03").format())

    def test_always_hours(self):
        self.assertEqual("00:02:03", mod.Duration.parse("02:03").format(always_hours=True))

    def test_millis(self):
        self.assertEqual("00:01.250", mod.Duration(1250).format(millis=True))

    def test_to_dict(self):
        self.assertEqual(
            {"millis": 1000, "formatted": "00:01"}, mod.Duration(1000).to_dict()
        )

    def test_repr(self):
        self.assertIn("00:01.000", repr(mod.Duration(1000)))


class ComparisonTests(DomainTestCase):
    def test_equality(self):
        self.assertEqual(mod.Duration(5), mod.Duration(5))

    def test_not_equal_to_int(self):
        self.assertNotEqual(mod.Duration(5), 5)

    def test_ordering(self):
        self.assertLess(mod.Duration(1), mod.Duration(2))
        self.assertLessEqual(mod.Duration(2), 2)
        self.assertGreater(mod.Duration(3), 2)
        self.assertGreaterEqual(mod.Duration(2), 2)

    def test_hashable(self):
        self.assertEqual(1, len({mod.Duration(5), mod.Duration(5)}))


class CoerceAndTotalTests(DomainTestCase):
    def test_duration_passes_through(self):
        value = mod.Duration(1)
        self.assertIs(value, mod.coerce_duration(value))

    def test_int(self):
        self.assertEqual(mod.Duration(5), mod.coerce_duration(5))

    def test_text(self):
        self.assertEqual(mod.Duration(60000), mod.coerce_duration("01:00"))

    def test_bool_is_rejected(self):
        self.assertField("duration", mod.coerce_duration, True)

    def test_negative_int_is_rejected(self):
        self.assertField("duration", mod.coerce_duration, -5)

    def test_total(self):
        self.assertEqual(mod.Duration(3000), mod.total([1000, "00:02"]))

    def test_total_of_empty(self):
        self.assertTrue(mod.total([]).is_zero())
