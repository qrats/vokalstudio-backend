from src.domain.analytics.event import PlayEvent
from src.domain.analytics import report as mod
from src.domain.analytics.rollup import DailyTotals, daily
from src.domain.episodes.episode import Episode
from src.domain.media.asset import Asset
from tests.support import DomainTestCase

ASSET = Asset("u-1", "episode-12.mp3", 5_000_000, duration="30:00")
DAY_ONE = "2021-05-01T10:00:00Z"
DAY_TWO = "2021-05-02T10:00:00Z"


def episode(title="Episode 12"):
    return Episode("u-1", "vokal-weekly", title, ASSET, "Notes here.", number=12)


def listen(reference, session_id, at=DAY_ONE, position=0, kind="start", source="web"):
    return PlayEvent(reference, session_id, kind, at, position, source)


class EpisodeReportTests(DomainTestCase):
    def setUp(self):
        self.episode = episode()
        self.reference = self.episode.reference
        self.events = [
            listen(self.reference, "s-1"),
            listen(self.reference, "s-1", DAY_ONE, 1_700_000, "progress"),
            listen(self.reference, "s-2", DAY_TWO),
            listen("other", "s-9", DAY_ONE),
        ]

    def test_names_the_episode(self):
        built = mod.episode_report(self.events, self.episode, "2021-05-01", "2021-05-03")
        self.assertEqual(self.reference, built["episode"])
        self.assertEqual("Episode 12", built["title"])

    def test_one_row_per_day(self):
        built = mod.episode_report(self.events, self.episode, "2021-05-01", "2021-05-04")
        self.assertEqual(3, len(built["days"]))

    def test_gaps_are_filled_with_zeroes(self):
        built = mod.episode_report(self.events, self.episode, "2021-05-01", "2021-05-04")
        self.assertEqual(0, built["days"][2]["starts"])

    def test_other_episodes_are_excluded(self):
        built = mod.episode_report(self.events, self.episode, "2021-05-01", "2021-05-03")
        self.assertEqual(2, built["listeners"])

    def test_totals(self):
        built = mod.episode_report(self.events, self.episode, "2021-05-01", "2021-05-03")
        self.assertEqual(2, built["totals"]["starts"])

    def test_totals_are_none_without_days(self):
        built = mod.episode_report([], self.episode, "2021-05-01", "2021-05-01")
        self.assertIsNone(built["totals"])

    def test_retention_curve_length(self):
        built = mod.episode_report(self.events, self.episode, "2021-05-01", "2021-05-03")
        self.assertEqual(11, len(built["retention"]))

    def test_custom_bucket_count(self):
        built = mod.episode_report(
            self.events, self.episode, "2021-05-01", "2021-05-03", buckets=4
        )
        self.assertEqual(5, len(built["retention"]))

    def test_completion_rate_is_reported(self):
        built = mod.episode_report(self.events, self.episode, "2021-05-01", "2021-05-03")
        self.assertEqual(50.0, built["completion_rate"])

    def test_an_episode_without_media(self):
        bare = Episode("u-1", "vokal-weekly", "Bare", None, "Notes.", number=1)
        built = mod.episode_report([], bare, "2021-05-01", "2021-05-02")
        self.assertEqual(0, built["listeners"])


class ShowReportTests(DomainTestCase):
    def setUp(self):
        self.first = episode("Alpha")
        self.second = episode("Beta")
        self.events = [
            listen(self.first.reference, "s-1"),
            listen(self.first.reference, "s-2"),
            listen(self.second.reference, "s-3"),
            listen(self.second.reference, "s-4", DAY_TWO, 0, "download", "rss"),
        ]

    def test_one_row_per_episode(self):
        built = mod.show_report(self.events, [self.first, self.second], "2021-05-01", "2021-05-03")
        self.assertEqual(2, len(built["episodes"]))

    def test_ordered_by_listeners(self):
        built = mod.show_report(self.events, [self.second, self.first], "2021-05-01", "2021-05-03")
        self.assertEqual("Alpha", built["episodes"][0]["title"])

    def test_ties_break_by_title(self):
        events = [listen(self.first.reference, "s-1"), listen(self.second.reference, "s-2")]
        built = mod.show_report(events, [self.second, self.first], "2021-05-01", "2021-05-03")
        self.assertEqual("Alpha", built["episodes"][0]["title"])

    def test_totals(self):
        built = mod.show_report(self.events, [self.first, self.second], "2021-05-01", "2021-05-03")
        self.assertEqual(4, built["listeners"])
        self.assertEqual(3, built["starts"])

    def test_downloads_are_counted(self):
        built = mod.show_report(self.events, [self.second], "2021-05-01", "2021-05-03")
        self.assertEqual(1, built["episodes"][0]["downloads"])

    def test_day_span(self):
        built = mod.show_report(self.events, [self.first], "2021-05-01", "2021-05-08")
        self.assertEqual(7, built["days"])

    def test_dates_are_echoed(self):
        built = mod.show_report([], [], "2021-05-01", "2021-05-03")
        self.assertEqual("2021-05-01", built["start"])
        self.assertEqual("2021-05-03", built["end"])

    def test_an_episode_with_no_plays(self):
        built = mod.show_report([], [self.first], "2021-05-01", "2021-05-03")
        self.assertEqual(0, built["episodes"][0]["starts"])


class TopEpisodeTests(DomainTestCase):
    def setUp(self):
        self.first = episode("Alpha")
        self.second = episode("Beta")
        events = [
            listen(self.first.reference, "s-1"),
            listen(self.first.reference, "s-2"),
            listen(self.second.reference, "s-3"),
        ]
        self.report = mod.show_report(
            events, [self.first, self.second], "2021-05-01", "2021-05-03"
        )

    def test_default_limit(self):
        self.assertEqual(2, len(mod.top_episodes(self.report)))

    def test_ordering(self):
        self.assertEqual(self.first.reference, mod.top_episodes(self.report)[0])

    def test_limit(self):
        self.assertEqual(1, len(mod.top_episodes(self.report, limit=1)))

    def test_limit_floor(self):
        self.assertField("limit", mod.top_episodes, self.report, 0)


class SourceBreakdownTests(DomainTestCase):
    def test_counts_distinct_sessions(self):
        events = [
            listen("ep-1", "s-1", source="web"),
            listen("ep-1", "s-1", DAY_TWO, source="web"),
            listen("ep-1", "s-2", source="ios"),
        ]
        self.assertEqual({"ios": 1, "web": 1}, mod.source_breakdown(events))

    def test_progress_events_do_not_count(self):
        events = [listen("ep-1", "s-1", DAY_ONE, 1000, "progress", "web")]
        self.assertEqual({}, mod.source_breakdown(events))

    def test_downloads_count(self):
        events = [listen("ep-1", "s-1", DAY_ONE, 0, "download", "rss")]
        self.assertEqual({"rss": 1}, mod.source_breakdown(events))

    def test_no_events(self):
        self.assertEqual({}, mod.source_breakdown([]))


class RetentionTrimTests(DomainTestCase):
    def setUp(self):
        events = [
            listen("ep-1", "s-1", "2021-05-01T00:00:00Z"),
            listen("ep-1", "s-2", "2021-05-05T00:00:00Z"),
            listen("ep-1", "s-3", "2021-05-09T00:00:00Z"),
        ]
        self.rows = daily(events)

    def test_keeps_recent_rows(self):
        self.assertEqual(2, len(mod.trim_to_retention(self.rows, 5)))

    def test_keeps_everything_with_a_long_window(self):
        self.assertEqual(3, len(mod.trim_to_retention(self.rows, 30)))

    def test_drops_everything_with_no_window(self):
        self.assertEqual((), mod.trim_to_retention(self.rows, 0))

    def test_empty_input(self):
        self.assertEqual((), mod.trim_to_retention([], 30))

    def test_negative_window_is_rejected(self):
        self.assertField("retention_days", mod.trim_to_retention, self.rows, -1)

    def test_boundary_day_is_dropped(self):
        kept = mod.trim_to_retention(self.rows, 4)
        self.assertEqual(1, len(kept))
        self.assertEqual("2021-05-09", kept[0].day.isoformat())
