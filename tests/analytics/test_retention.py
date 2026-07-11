from src.domain.analytics.event import PlayEvent
from src.domain.analytics import retention as mod
from tests.support import DomainTestCase

WHEN = "2021-05-01T10:00:00Z"
LENGTH = 1_000_000


def listener(session_id, furthest):
    """One session that got as far as ``furthest`` milliseconds."""
    return [
        PlayEvent("ep-1", session_id, "start", WHEN, 0),
        PlayEvent("ep-1", session_id, "progress", WHEN, furthest),
    ]


def audience(*positions):
    events = []
    for index, position in enumerate(positions):
        events.extend(listener("s-{}".format(index), position))
    return events


class CurveTests(DomainTestCase):
    def test_starts_at_a_hundred(self):
        points = mod.curve(audience(LENGTH), LENGTH)
        self.assertEqual(100.0, points[0])

    def test_point_count(self):
        self.assertEqual(11, len(mod.curve(audience(LENGTH), LENGTH)))

    def test_custom_bucket_count(self):
        self.assertEqual(5, len(mod.curve(audience(LENGTH), LENGTH, buckets=4)))

    def test_everyone_finishes(self):
        self.assertEqual(100.0, mod.curve(audience(LENGTH, LENGTH), LENGTH)[-1])

    def test_half_drop_out_at_the_middle(self):
        points = mod.curve(audience(LENGTH, LENGTH // 2), LENGTH)
        self.assertEqual(100.0, points[5])
        self.assertEqual(50.0, points[6])

    def test_no_listeners(self):
        self.assertEqual(tuple(0.0 for _ in range(11)), mod.curve([], LENGTH))

    def test_curve_never_rises(self):
        points = mod.curve(audience(LENGTH, LENGTH // 2, LENGTH // 4), LENGTH)
        for index in range(1, len(points)):
            self.assertLessEqual(points[index], points[index - 1])

    def test_zero_duration_is_rejected(self):
        self.assertField("duration_millis", mod.curve, audience(1), 0)

    def test_zero_buckets_is_rejected(self):
        self.assertField("buckets", mod.curve, audience(1), LENGTH, 0)

    def test_too_many_buckets(self):
        self.assertField("buckets", mod.curve, audience(1), LENGTH, 101)


class CompletionTests(DomainTestCase):
    def test_everyone_completes(self):
        self.assertEqual(100.0, mod.completion_rate(audience(LENGTH, LENGTH), LENGTH))

    def test_nobody_completes(self):
        self.assertEqual(0.0, mod.completion_rate(audience(100), LENGTH))

    def test_half_complete(self):
        rate = mod.completion_rate(audience(LENGTH, 100), LENGTH)
        self.assertEqual(50.0, rate)

    def test_threshold_is_respected(self):
        events = audience(LENGTH // 2)
        self.assertEqual(100.0, mod.completion_rate(events, LENGTH, threshold_percent=50))

    def test_below_the_threshold(self):
        events = audience(LENGTH // 2 - 1)
        self.assertEqual(0.0, mod.completion_rate(events, LENGTH, threshold_percent=50))

    def test_no_listeners(self):
        self.assertEqual(0.0, mod.completion_rate([], LENGTH))

    def test_threshold_floor(self):
        self.assertField(
            "threshold_percent", mod.completion_rate, audience(1), LENGTH, 0
        )

    def test_threshold_ceiling(self):
        self.assertField(
            "threshold_percent", mod.completion_rate, audience(1), LENGTH, 101
        )


class AveragePositionTests(DomainTestCase):
    def test_single_listener(self):
        self.assertEqual(500, mod.average_position(audience(500)))

    def test_two_listeners(self):
        self.assertEqual(750, mod.average_position(audience(500, 1000)))

    def test_no_listeners(self):
        self.assertEqual(0, mod.average_position([]))

    def test_truncates(self):
        self.assertEqual(333, mod.average_position(audience(0, 500, 500)))


class DropOffTests(DomainTestCase):
    def test_finds_the_steepest_fall(self):
        self.assertEqual(2, mod.drop_off_bucket([100.0, 90.0, 40.0, 35.0]))

    def test_first_bucket(self):
        self.assertEqual(1, mod.drop_off_bucket([100.0, 10.0, 5.0]))

    def test_flat_curve(self):
        self.assertEqual(1, mod.drop_off_bucket([100.0, 100.0, 100.0]))

    def test_needs_two_points(self):
        self.assertField("points", mod.drop_off_bucket, [100.0])

    def test_empty_curve(self):
        self.assertField("points", mod.drop_off_bucket, [])


class HealthTests(DomainTestCase):
    def test_healthy(self):
        self.assertTrue(mod.is_healthy([100.0, 80.0, 60.0]))

    def test_on_the_floor(self):
        self.assertTrue(mod.is_healthy([100.0, 50.0]))

    def test_unhealthy(self):
        self.assertFalse(mod.is_healthy([100.0, 20.0]))

    def test_custom_floor(self):
        self.assertTrue(mod.is_healthy([100.0, 20.0], floor_percent=10.0))

    def test_empty_curve(self):
        self.assertFalse(mod.is_healthy([]))
