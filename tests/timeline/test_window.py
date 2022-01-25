from src.domain.timeline.duration import Duration
from src.domain.timeline import window as mod
from tests.support import DomainTestCase


def weekly(day="tue", start="19:00", minutes=90, label=None):
    return mod.Window([day], start, Duration.of_minutes(minutes), label)


class WeekdayTests(DomainTestCase):
    def test_names(self):
        self.assertEqual(0, mod.parse_weekday("mon"))
        self.assertEqual(6, mod.parse_weekday("sun"))

    def test_long_names(self):
        self.assertEqual(2, mod.parse_weekday("Wednesday"))

    def test_index(self):
        self.assertEqual(3, mod.parse_weekday(3))

    def test_out_of_range_index(self):
        self.assertField("weekday", mod.parse_weekday, 7)

    def test_unknown_name(self):
        self.assertField("weekday", mod.parse_weekday, "funday")

    def test_bool_is_treated_as_a_name(self):
        self.assertField("weekday", mod.parse_weekday, True)


class TimeOfDayTests(DomainTestCase):
    def test_parses(self):
        self.assertEqual(19 * 60, mod.parse_time_of_day("19:00"))

    def test_minutes(self):
        self.assertEqual(19 * 60 + 30, mod.parse_time_of_day("19:30"))

    def test_midnight(self):
        self.assertEqual(0, mod.parse_time_of_day("00:00"))

    def test_wrong_shape(self):
        self.assertField("time", mod.parse_time_of_day, "1900")

    def test_non_numeric(self):
        self.assertField("time", mod.parse_time_of_day, "aa:bb")

    def test_out_of_range_hour(self):
        self.assertField("time", mod.parse_time_of_day, "24:00")

    def test_out_of_range_minute(self):
        self.assertField("time", mod.parse_time_of_day, "12:60")

    def test_format(self):
        self.assertEqual("19:05", mod.format_time_of_day(19 * 60 + 5))

    def test_format_rejects_a_full_day(self):
        self.assertField("minutes", mod.format_time_of_day, 24 * 60)


class ConstructionTests(DomainTestCase):
    def test_weekdays_are_sorted_and_unique(self):
        window = mod.Window(["fri", "mon", "mon"], "10:00", Duration.of_minutes(30))
        self.assertEqual((0, 4), window.weekdays)

    def test_empty_weekdays_are_rejected(self):
        self.assertField("weekdays", mod.Window, [], "10:00", 60000)

    def test_zero_duration_is_rejected(self):
        self.assertField("duration", mod.Window, ["mon"], "10:00", 0)

    def test_over_long_duration_is_rejected(self):
        self.assertField(
            "duration", mod.Window, ["mon"], "10:00", 24 * 3600 * 1000 + 1
        )

    def test_exactly_a_day_is_allowed(self):
        window = mod.Window(["mon"], "00:00", 24 * 3600 * 1000)
        self.assertEqual(24 * 3600 * 1000, window.duration.millis)

    def test_label(self):
        self.assertEqual("Drive time", weekly(label="Drive time").label)

    def test_label_is_optional(self):
        self.assertIsNone(weekly().label)


class OccurrenceTests(DomainTestCase):
    def test_occurs_on_matching_weekday(self):
        self.assertTrue(weekly().occurs_on("2021-05-11"))

    def test_does_not_occur_otherwise(self):
        self.assertFalse(weekly().occurs_on("2021-05-12"))

    def test_interval_on(self):
        span = weekly().interval_on("2021-05-11")
        self.assertEqual("2021-05-11T19:00:00Z", span.start.to_iso())
        self.assertEqual("2021-05-11T20:30:00Z", span.end.to_iso())

    def test_interval_on_other_day_is_none(self):
        self.assertIsNone(weekly().interval_on("2021-05-12"))

    def test_expand(self):
        spans = weekly().expand("2021-05-10", "2021-05-25")
        self.assertEqual(2, len(spans))

    def test_expand_is_half_open(self):
        spans = weekly().expand("2021-05-11", "2021-05-11")
        self.assertEqual(0, len(spans))

    def test_weekly_load(self):
        window = mod.Window(["mon", "tue"], "10:00", Duration.of_minutes(30))
        self.assertEqual(Duration.of_minutes(60), window.weekly_load())


class SerialisationTests(DomainTestCase):
    def test_to_dict(self):
        payload = weekly(label="Drive time").to_dict()
        self.assertEqual(["tue"], payload["weekdays"])
        self.assertEqual("19:00", payload["start_time"])
        self.assertEqual("Drive time", payload["label"])

    def test_to_dict_omits_missing_label(self):
        self.assertNotIn("label", weekly().to_dict())

    def test_equality_ignores_label(self):
        self.assertEqual(weekly(), weekly(label="anything"))

    def test_hashable(self):
        self.assertEqual(1, len({weekly(), weekly()}))

    def test_repr(self):
        self.assertIn("tue", repr(weekly()))


class ScheduleTests(DomainTestCase):
    def test_conflicts(self):
        clash = mod.schedule_conflicts(
            [weekly(start="19:00"), weekly(start="20:00")], "2021-05-10", "2021-05-17"
        )
        self.assertEqual(((0, 1),), clash)

    def test_no_conflict_on_different_days(self):
        clash = mod.schedule_conflicts(
            [weekly("tue"), weekly("wed")], "2021-05-10", "2021-05-17"
        )
        self.assertEqual((), clash)

    def test_no_conflict_when_back_to_back(self):
        clash = mod.schedule_conflicts(
            [weekly(start="19:00", minutes=60), weekly(start="20:00")],
            "2021-05-10",
            "2021-05-17",
        )
        self.assertEqual((), clash)

    def test_busiest_day(self):
        busiest = mod.busiest_day(
            [weekly("tue", minutes=90), weekly("wed", minutes=30)],
            "2021-05-10",
            "2021-05-17",
        )
        self.assertEqual("2021-05-11", busiest)

    def test_busiest_day_of_nothing(self):
        self.assertIsNone(mod.busiest_day([], "2021-05-10", "2021-05-17"))

    def test_busiest_day_breaks_ties_by_date(self):
        busiest = mod.busiest_day(
            [weekly("tue", minutes=60), weekly("wed", minutes=60)],
            "2021-05-10",
            "2021-05-17",
        )
        self.assertEqual("2021-05-11", busiest)
