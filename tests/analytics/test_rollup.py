from src.domain.analytics.event import COMPLETE, DOWNLOAD, PROGRESS, PlayEvent, START
from src.domain.analytics import rollup as mod
from tests.support import DomainTestCase


def event(kind=START, session="s-1", at="2021-05-01T10:00:00Z", position=0, reference="e-1"):
    return PlayEvent(reference, session, kind, at, position)


class DailyTotalsTests(DomainTestCase):
    def test_completion_rate(self):
        self.assertEqual(50.0, mod.DailyTotals("2021-05-01", 4, 2).completion_rate)

    def test_completion_rate_without_starts(self):
        self.assertEqual(0.0, mod.DailyTotals("2021-05-01").completion_rate)

    def test_completes_cannot_exceed_starts(self):
        self.assertField("completes", mod.DailyTotals, "2021-05-01", 1, 2)

    def test_negative_starts(self):
        self.assertField("starts", mod.DailyTotals, "2021-05-01", -1)

    def test_plus(self):
        one = mod.DailyTotals("2021-05-01", 2, 1, 3, 2)
        merged = one.plus(mod.DailyTotals("2021-05-02", 1, 1, 1, 1))
        self.assertEqual(3, merged.starts)
        self.assertEqual("2021-05-01", merged.day.isoformat())

    def test_to_dict(self):
        payload = mod.DailyTotals("2021-05-01", 4, 2).to_dict()
        self.assertEqual(50.0, payload["completion_rate"])

    def test_equality(self):
        self.assertEqual(mod.DailyTotals("2021-05-01"), mod.DailyTotals("2021-05-01"))

    def test_hashable(self):
        self.assertEqual(
            1, len({mod.DailyTotals("2021-05-01"), mod.DailyTotals("2021-05-01")})
        )

    def test_repr(self):
        self.assertIn("2021-05-01", repr(mod.DailyTotals("2021-05-01")))


class DailyTests(DomainTestCase):
    def setUp(self):
        self.events = [
            event(START, "s-1"),
            event(COMPLETE, "s-1", position=100),
            event(START, "s-2", "2021-05-01T11:00:00Z"),
            event(DOWNLOAD, "s-3", "2021-05-02T09:00:00Z"),
        ]

    def test_one_row_per_day(self):
        self.assertEqual(2, len(mod.daily(self.events)))

    def test_starts_are_counted(self):
        self.assertEqual(2, mod.daily(self.events)[0].starts)

    def test_completes_are_counted(self):
        self.assertEqual(1, mod.daily(self.events)[0].completes)

    def test_downloads_are_counted(self):
        self.assertEqual(1, mod.daily(self.events)[1].downloads)

    def test_sessions_are_distinct(self):
        self.assertEqual(2, mod.daily(self.events)[0].sessions)

    def test_progress_is_not_a_start(self):
        events = [event(PROGRESS, position=100)]
        self.assertEqual(0, mod.daily(events)[0].starts)

    def test_duplicates_are_dropped(self):
        self.assertEqual(2, mod.daily(self.events + [event(START, "s-1")])[0].starts)

    def test_rows_are_ordered(self):
        rows = mod.daily(self.events)
        self.assertLess(rows[0].day, rows[1].day)

    def test_scoped_to_an_episode(self):
        events = self.events + [event(START, "s-9", reference="e-2")]
        self.assertEqual(2, mod.daily(events, "e-1")[0].starts)

    def test_no_events(self):
        self.assertEqual((), mod.daily([]))


class FillGapsTests(DomainTestCase):
    def test_inserts_zero_rows(self):
        rows = mod.daily([event()])
        filled = mod.fill_gaps(rows, "2021-05-01", "2021-05-04")
        self.assertEqual(3, len(filled))
        self.assertEqual(0, filled[1].starts)

    def test_keeps_the_real_rows(self):
        rows = mod.daily([event()])
        filled = mod.fill_gaps(rows, "2021-05-01", "2021-05-03")
        self.assertEqual(1, filled[0].starts)

    def test_empty_range(self):
        self.assertEqual((), mod.fill_gaps([], "2021-05-01", "2021-05-01"))


class CombineTests(DomainTestCase):
    def test_sums(self):
        rows = [mod.DailyTotals("2021-05-01", 2, 1), mod.DailyTotals("2021-05-02", 3, 2)]
        merged = mod.combine(rows)
        self.assertEqual(5, merged.starts)
        self.assertEqual(3, merged.completes)

    def test_dated_on_the_first_day(self):
        rows = [mod.DailyTotals("2021-05-01"), mod.DailyTotals("2021-05-02")]
        self.assertEqual("2021-05-01", mod.combine(rows).day.isoformat())

    def test_empty(self):
        self.assertIsNone(mod.combine([]))

    def test_single_row(self):
        row = mod.DailyTotals("2021-05-01", 2)
        self.assertEqual(row, mod.combine([row]))


class BusiestTests(DomainTestCase):
    def test_most_starts(self):
        rows = [mod.DailyTotals("2021-05-01", 2), mod.DailyTotals("2021-05-02", 5)]
        self.assertEqual("2021-05-02", mod.busiest(rows).day.isoformat())

    def test_ties_break_by_date(self):
        rows = [mod.DailyTotals("2021-05-02", 2), mod.DailyTotals("2021-05-01", 2)]
        self.assertEqual("2021-05-02", mod.busiest(rows).day.isoformat())

    def test_empty(self):
        self.assertIsNone(mod.busiest([]))

    def test_default(self):
        self.assertEqual("x", mod.busiest([], "x"))


class MovingAverageTests(DomainTestCase):
    def test_trailing_window(self):
        rows = [mod.DailyTotals("2021-05-0{}".format(i), i) for i in range(1, 5)]
        self.assertEqual((1.0, 1.5, 2.0, 3.0), mod.moving_average(rows, 3))

    def test_window_of_one(self):
        rows = [mod.DailyTotals("2021-05-01", 2), mod.DailyTotals("2021-05-02", 4)]
        self.assertEqual((2.0, 4.0), mod.moving_average(rows, 1))

    def test_empty(self):
        self.assertEqual((), mod.moving_average([]))

    def test_zero_window_is_rejected(self):
        self.assertField("window", mod.moving_average, [], 0)
