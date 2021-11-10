from src.domain.timeline.duration import Duration
from src.domain.timeline.instant import Instant
from src.domain.timeline import interval as mod
from tests.support import DomainTestCase


def span(start, end):
    return mod.Interval(Instant(start), Instant(end))


class ConstructionTests(DomainTestCase):
    def test_start_and_end(self):
        one = span(0, 10)
        self.assertEqual(0, one.start.millis)
        self.assertEqual(10, one.end.millis)

    def test_end_before_start_is_rejected(self):
        self.assertField("end", mod.Interval, Instant(10), Instant(1))

    def test_empty_interval_is_allowed(self):
        self.assertTrue(span(5, 5).is_empty())

    def test_starting_with_duration(self):
        one = mod.Interval.starting(Instant(100), Duration(50))
        self.assertEqual(150, one.end.millis)

    def test_starting_with_millis(self):
        self.assertEqual(150, mod.Interval.starting(Instant(100), 50).end.millis)

    def test_accepts_iso_text(self):
        one = mod.Interval("1970-01-01T00:00:00Z", "1970-01-01T00:00:01Z")
        self.assertEqual(1000, one.duration.millis)


class QueryTests(DomainTestCase):
    def test_duration(self):
        self.assertEqual(Duration(10), span(5, 15).duration)

    def test_contains_start(self):
        self.assertTrue(span(0, 10).contains(Instant(0)))

    def test_does_not_contain_end(self):
        self.assertFalse(span(0, 10).contains(Instant(10)))

    def test_contains_accepts_millis(self):
        self.assertTrue(span(0, 10).contains(5))

    def test_overlap(self):
        self.assertTrue(span(0, 10).overlaps(span(5, 15)))

    def test_no_overlap_when_touching(self):
        self.assertFalse(span(0, 10).overlaps(span(10, 20)))

    def test_touches(self):
        self.assertTrue(span(0, 10).touches(span(10, 20)))

    def test_touches_is_symmetric(self):
        self.assertTrue(span(10, 20).touches(span(0, 10)))

    def test_empty_never_overlaps(self):
        self.assertFalse(span(5, 5).overlaps(span(0, 10)))


class CombineTests(DomainTestCase):
    def test_intersection(self):
        self.assertEqual(span(5, 10), span(0, 10).intersection(span(5, 15)))

    def test_intersection_is_none_when_disjoint(self):
        self.assertIsNone(span(0, 5).intersection(span(6, 10)))

    def test_intersection_of_touching_is_empty(self):
        self.assertTrue(span(0, 5).intersection(span(5, 10)).is_empty())

    def test_union(self):
        self.assertEqual(span(0, 15), span(0, 10).union(span(5, 15)))

    def test_union_of_touching(self):
        self.assertEqual(span(0, 20), span(0, 10).union(span(10, 20)))

    def test_union_of_disjoint_is_rejected(self):
        self.assertField("other", span(0, 5).union, span(6, 10))

    def test_shift(self):
        self.assertEqual(span(10, 20), span(0, 10).shift(10))

    def test_shift_backwards(self):
        self.assertEqual(span(-5, 5), span(0, 10).shift(-5))


class SerialisationTests(DomainTestCase):
    def test_to_dict(self):
        self.assertEqual(
            {"start": "1970-01-01T00:00:00Z", "end": "1970-01-01T00:00:01Z"},
            span(0, 1000).to_dict(),
        )

    def test_equality(self):
        self.assertEqual(span(0, 1), span(0, 1))

    def test_inequality(self):
        self.assertNotEqual(span(0, 1), span(0, 2))

    def test_hashable(self):
        self.assertEqual(1, len({span(0, 1), span(0, 1)}))

    def test_repr(self):
        self.assertIn("Interval(", repr(span(0, 1)))


class MergeTests(DomainTestCase):
    def test_merges_overlapping(self):
        merged = mod.merge_overlapping([span(0, 10), span(5, 15)])
        self.assertEqual((span(0, 15),), merged)

    def test_merges_touching(self):
        merged = mod.merge_overlapping([span(0, 10), span(10, 20)])
        self.assertEqual((span(0, 20),), merged)

    def test_keeps_disjoint(self):
        merged = mod.merge_overlapping([span(0, 5), span(10, 20)])
        self.assertEqual(2, len(merged))

    def test_sorts_input(self):
        merged = mod.merge_overlapping([span(10, 20), span(0, 5)])
        self.assertEqual(span(0, 5), merged[0])

    def test_empty(self):
        self.assertEqual((), mod.merge_overlapping([]))


class ConflictTests(DomainTestCase):
    def test_finds_pairs(self):
        found = mod.find_conflicts([span(0, 10), span(5, 15), span(30, 40)])
        self.assertEqual(((0, 1),), found)

    def test_no_conflicts(self):
        self.assertEqual((), mod.find_conflicts([span(0, 5), span(5, 10)]))

    def test_three_way_conflict(self):
        found = mod.find_conflicts([span(0, 10), span(1, 9), span(2, 8)])
        self.assertEqual(((0, 1), (0, 2), (1, 2)), found)


class CoverageTests(DomainTestCase):
    def test_counts_overlap_once(self):
        self.assertEqual(Duration(15), mod.total_covered([span(0, 10), span(5, 15)]))

    def test_sums_disjoint(self):
        self.assertEqual(Duration(10), mod.total_covered([span(0, 5), span(10, 15)]))

    def test_empty(self):
        self.assertTrue(mod.total_covered([]).is_zero())


class GapTests(DomainTestCase):
    def test_gap_in_the_middle(self):
        holes = mod.gaps([span(0, 4), span(6, 10)], span(0, 10))
        self.assertEqual((span(4, 6),), holes)

    def test_leading_gap(self):
        holes = mod.gaps([span(5, 10)], span(0, 10))
        self.assertEqual((span(0, 5),), holes)

    def test_trailing_gap(self):
        holes = mod.gaps([span(0, 5)], span(0, 10))
        self.assertEqual((span(5, 10),), holes)

    def test_full_cover_has_no_gaps(self):
        self.assertEqual((), mod.gaps([span(0, 10)], span(0, 10)))

    def test_nothing_covered(self):
        self.assertEqual((span(0, 10),), mod.gaps([], span(0, 10)))

    def test_ignores_intervals_outside_the_window(self):
        self.assertEqual((span(0, 10),), mod.gaps([span(20, 30)], span(0, 10)))
