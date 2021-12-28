import datetime

from src.domain.timeline import calendar as mod
from tests.support import DomainTestCase


class ParseTests(DomainTestCase):
    def test_iso_string(self):
        self.assertEqual(datetime.date(2021, 5, 12), mod.parse_date("2021-05-12"))

    def test_date_passes_through(self):
        day = datetime.date(2021, 5, 12)
        self.assertIs(day, mod.parse_date(day))

    def test_datetime_is_rejected(self):
        self.assertField("date", mod.parse_date, datetime.datetime(2021, 5, 12))

    def test_bad_format(self):
        self.assertField("date", mod.parse_date, "12/05/2021")

    def test_impossible_day(self):
        self.assertField("date", mod.parse_date, "2021-02-30")

    def test_field_name(self):
        self.assertField("anchor", mod.parse_date, "x", "anchor")

    def test_format_date(self):
        self.assertEqual("2021-05-12", mod.format_date(datetime.date(2021, 5, 12)))


class DaysInMonthTests(DomainTestCase):
    def test_january(self):
        self.assertEqual(31, mod.days_in_month(2021, 1))

    def test_february_common(self):
        self.assertEqual(28, mod.days_in_month(2021, 2))

    def test_february_leap(self):
        self.assertEqual(29, mod.days_in_month(2020, 2))

    def test_december(self):
        self.assertEqual(31, mod.days_in_month(2021, 12))

    def test_april(self):
        self.assertEqual(30, mod.days_in_month(2021, 4))

    def test_month_out_of_range(self):
        self.assertField("month", mod.days_in_month, 2021, 13)


class AddTests(DomainTestCase):
    def test_add_days(self):
        self.assertEqual("2021-05-13", mod.add_days("2021-05-12", 1).isoformat())

    def test_add_days_backwards(self):
        self.assertEqual("2021-05-11", mod.add_days("2021-05-12", -1).isoformat())

    def test_add_months(self):
        self.assertEqual("2021-06-12", mod.add_months("2021-05-12", 1).isoformat())

    def test_add_months_clamps(self):
        self.assertEqual("2021-02-28", mod.add_months("2021-01-31", 1).isoformat())

    def test_add_months_clamps_into_leap_year(self):
        self.assertEqual("2020-02-29", mod.add_months("2020-01-31", 1).isoformat())

    def test_add_months_across_a_year(self):
        self.assertEqual("2022-01-12", mod.add_months("2021-05-12", 8).isoformat())

    def test_add_months_backwards(self):
        self.assertEqual("2020-12-12", mod.add_months("2021-05-12", -5).isoformat())

    def test_add_years(self):
        self.assertEqual("2022-05-12", mod.add_years("2021-05-12", 1).isoformat())

    def test_add_years_clamps_leap_day(self):
        self.assertEqual("2021-02-28", mod.add_years("2020-02-29", 1).isoformat())


class BetweenTests(DomainTestCase):
    def test_positive(self):
        self.assertEqual(1, mod.days_between("2021-05-12", "2021-05-13"))

    def test_negative(self):
        self.assertEqual(-1, mod.days_between("2021-05-13", "2021-05-12"))

    def test_same_day(self):
        self.assertEqual(0, mod.days_between("2021-05-12", "2021-05-12"))


class LeapYearTests(DomainTestCase):
    def test_divisible_by_four(self):
        self.assertTrue(mod.is_leap_year(2020))

    def test_century_is_not_leap(self):
        self.assertFalse(mod.is_leap_year(1900))

    def test_four_hundred_is_leap(self):
        self.assertTrue(mod.is_leap_year(2000))

    def test_ordinary_year(self):
        self.assertFalse(mod.is_leap_year(2021))


class BoundaryTests(DomainTestCase):
    def test_week_start_monday(self):
        self.assertEqual("2021-05-10", mod.week_start("2021-05-12").isoformat())

    def test_week_start_sunday(self):
        self.assertEqual("2021-05-09", mod.week_start("2021-05-12", 6).isoformat())

    def test_week_start_on_the_boundary(self):
        self.assertEqual("2021-05-10", mod.week_start("2021-05-10").isoformat())

    def test_invalid_first_weekday(self):
        self.assertField("first_weekday", mod.week_start, "2021-05-12", 7)

    def test_month_start(self):
        self.assertEqual("2021-05-01", mod.month_start("2021-05-12").isoformat())

    def test_month_end(self):
        self.assertEqual("2021-05-31", mod.month_end("2021-05-12").isoformat())

    def test_month_end_february(self):
        self.assertEqual("2021-02-28", mod.month_end("2021-02-01").isoformat())


class AnniversaryTests(DomainTestCase):
    def test_anniversary_day(self):
        self.assertEqual(31, mod.anniversary_day("2021-01-31"))

    def test_next_anniversary_monthly(self):
        self.assertEqual(
            "2021-03-31", mod.next_anniversary("2021-01-31", "2021-03-05").isoformat()
        )

    def test_next_anniversary_skips_equal_day(self):
        self.assertEqual(
            "2021-04-30", mod.next_anniversary("2021-01-31", "2021-03-31").isoformat()
        )

    def test_next_anniversary_before_anchor(self):
        self.assertEqual(
            "2021-01-31", mod.next_anniversary("2021-01-31", "2020-12-01").isoformat()
        )

    def test_next_anniversary_yearly(self):
        self.assertEqual(
            "2022-01-31",
            mod.next_anniversary("2021-01-31", "2021-06-01", months=12).isoformat(),
        )

    def test_next_anniversary_quarterly(self):
        self.assertEqual(
            "2021-07-31",
            mod.next_anniversary("2021-01-31", "2021-05-01", months=3).isoformat(),
        )

    def test_zero_months_is_rejected(self):
        self.assertField(
            "months", mod.next_anniversary, "2021-01-31", "2021-05-01", 0
        )


class DateRangeTests(DomainTestCase):
    def test_half_open(self):
        days = mod.date_range("2021-05-10", "2021-05-13")
        self.assertEqual(3, len(days))
        self.assertEqual("2021-05-12", days[-1].isoformat())

    def test_empty_range(self):
        self.assertEqual((), mod.date_range("2021-05-10", "2021-05-10"))

    def test_reversed_is_rejected(self):
        self.assertField("end", mod.date_range, "2021-05-13", "2021-05-10")


class MonthNameTests(DomainTestCase):
    def test_first(self):
        self.assertEqual("january", mod.month_name(1))

    def test_last(self):
        self.assertEqual("december", mod.month_name(12))

    def test_out_of_range(self):
        self.assertField("month", mod.month_name, 0)
