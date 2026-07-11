from src.domain.analytics.event import COMPLETE, DOWNLOAD, PlayEvent, START
from src.domain.analytics import report as mod
from src.domain.analytics.rollup import DailyTotals
from src.domain.episodes.episode import Episode
from src.domain.media.asset import Asset
from tests.support import DomainTestCase

ASSET = Asset("u-1", "ep.mp3", 5_000_000, duration="30:00")


def episode(title="Episode 12"):
    return Episode(
        "u-1", "vokal-weekly", title, asset=ASSET, notes="Notes.", number=12
    )


def event(reference, session, kind=START, at="2021-05-01T10:00:00Z", position=0, source="web"):
    return PlayEvent(reference, session, kind, at, position, source)


class EpisodeReportTests(DomainTestCase):
    def setUp(self):
        self.one = episode()
        self.events = [
            event(self.one.reference, "s-1"),
            event(self.one.reference, "s-1", COMPLETE, position=1_800_000),
            event(self.one.reference, "s-2"),
        ]
        self.report = mod.episode_report(
            self.events, self.one, "2021-05-01", "2021-05-04"
        )

    def test_title(self):
        self.assertEqual("Episode 12", self.report["title"])

    def test_days_are_filled(self):
        self.assertEqual(3, len(self.report["days"]))

    def test_totals(self):
        self.assertEqual(2, self.report["totals"]["starts"])

    def test_listeners(self):
        self.assertEqual(2, self.report["listeners"])

    def test_retention_curve(self):
        self.assertEqual(11, len(self.report["retention"]))

    def test_completion_rate(self):
        self.assertEqual(50.0, self.report["completion_rate"])

    def test_other_episodes_are_excluded(self):
        events = self.events + [event("other", "s-9")]
        built = mod.episode_report(events, self.one, "2021-05-01", "2021-05-04")
        self.assertEqual(2, built["listeners"])

    def test_no_events(self):
        built = mod.episode_report([], self.one, "2021-05-01", "2021-05-04")
        self.assertEqual(0, built["listeners"])
        self.assertEqual(0, built["totals"]["starts"])


class ShowReportTests(DomainTestCase):
    def setUp(self):
        self.one = episode("Alpha")
        self.two = episode("Beta")
        self.events = [
            event(self.one.reference, "s-1"),
            event(self.one.reference, "s-2"),
            event(self.two.reference, "s-3"),
        ]
        self.report = mod.show_report(
            self.events, [self.two, self.one], "2021-05-01", "2021-05-08"
        )

    def test_days(self):
        self.assertEqual(7, self.report["days"])

    def test_rows_ordered_by_listeners(self):
        self.assertEqual("Alpha", self.report["episodes"][0]["title"])

    def test_totals(self):
        self.assertEqual(3, self.report["listeners"])
        self.assertEqual(3, self.report["starts"])

    def test_downloads_are_counted(self):
        events = self.events + [event(self.two.reference, "s-4", DOWNLOAD)]
        built = mod.show_report(events, [self.one, self.two], "2021-05-01", "2021-05-08")
        beta = [row for row in built["episodes"] if row["title"] == "Beta"][0]
        self.assertEqual(1, beta["downloads"])

    def test_no_episodes(self):
        built = mod.show_report([], [], "2021-05-01", "2021-05-08")
        self.assertEqual(0, built["listeners"])

    def test_top_episodes(self):
        self.assertEqual((self.one.reference,), mod.top_episodes(self.report, 1))

    def test_top_episodes_limit_floor(self):
        self.assertField("limit", mod.top_episodes, self.report, 0)


class SourceTests(DomainTestCase):
    def test_counts_distinct_sessions(self):
        events = [
            event("e-1", "s-1", source="web"),
            event("e-1", "s-1", source="web"),
            event("e-1", "s-2", source="ios"),
        ]
        self.assertEqual({"ios": 1, "web": 1}, mod.source_breakdown(events))

    def test_downloads_are_included(self):
        events = [event("e-1", "s-1", DOWNLOAD, source="rss")]
        self.assertEqual({"rss": 1}, mod.source_breakdown(events))

    def test_progress_is_ignored(self):
        events = [event("e-1", "s-1", COMPLETE, position=10, source="web")]
        self.assertEqual({}, mod.source_breakdown(events))

    def test_no_events(self):
        self.assertEqual({}, mod.source_breakdown([]))


class RetentionTrimTests(DomainTestCase):
    def setUp(self):
        self.rows = [
            DailyTotals("2021-05-01", 1),
            DailyTotals("2021-05-05", 1),
            DailyTotals("2021-05-10", 1),
        ]

    def test_keeps_recent_rows(self):
        kept = mod.trim_to_retention(self.rows, 7)
        self.assertEqual(2, len(kept))

    def test_keeps_everything_with_a_long_window(self):
        self.assertEqual(3, len(mod.trim_to_retention(self.rows, 30)))

    def test_zero_retention_keeps_nothing(self):
        self.assertEqual((), mod.trim_to_retention(self.rows, 0))

    def test_empty(self):
        self.assertEqual((), mod.trim_to_retention([], 30))

    def test_negative_retention_is_rejected(self):
        self.assertField("retention_days", mod.trim_to_retention, self.rows, -1)
