"""How far into an episode people actually get.

The curve is expressed as the share of listeners still present at each tenth of
the episode, which is the shape the dashboard draws.
"""

from src.domain.analytics.event import furthest_position, sessions
from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int

DEFAULT_BUCKETS = 10


def curve(events, duration_millis, buckets=DEFAULT_BUCKETS):
    """The share of listeners still present at each bucket boundary."""
    length = require_int(duration_millis, "duration_millis", minimum=1)
    count = require_int(buckets, "buckets", minimum=1, maximum=100)
    listeners = sessions(events)
    if not listeners:
        return tuple(0.0 for _ in range(count + 1))
    furthest = [furthest_position(events, session) for session in listeners]
    points = []
    for index in range(count + 1):
        boundary = length * index // count
        still_here = sum(1 for position in furthest if position >= boundary)
        points.append(round(still_here * 100.0 / len(listeners), 2))
    return tuple(points)


def completion_rate(events, duration_millis, threshold_percent=90):
    """Share of listeners who reached ``threshold_percent`` of the episode."""
    length = require_int(duration_millis, "duration_millis", minimum=1)
    threshold = require_int(
        threshold_percent, "threshold_percent", minimum=1, maximum=100
    )
    listeners = sessions(events)
    if not listeners:
        return 0.0
    boundary = length * threshold // 100
    reached = sum(
        1 for session in listeners if furthest_position(events, session) >= boundary
    )
    return round(reached * 100.0 / len(listeners), 2)


def average_position(events):
    """Mean furthest position across listeners, in whole milliseconds."""
    listeners = sessions(events)
    if not listeners:
        return 0
    total = sum(furthest_position(events, session) for session in listeners)
    return total // len(listeners)


def drop_off_bucket(points):
    """The bucket index where the largest share of listeners left."""
    if len(points) < 2:
        raise ValidationError("a curve needs at least two points", field="points")
    worst = 0
    biggest = None
    for index in range(1, len(points)):
        fall = points[index - 1] - points[index]
        if biggest is None or fall > biggest:
            biggest = fall
            worst = index
    return worst


def is_healthy(points, floor_percent=50.0):
    """Whether at least ``floor_percent`` of listeners reach the end."""
    if not points:
        return False
    return points[-1] >= floor_percent
