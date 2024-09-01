"""Turning encoder telemetry into something a dashboard can show.

The worker reports dropped frames, round-trip time and how full the send buffer
is.  Each has its own thresholds, and the overall status is the worst of them
so that one bad signal is never averaged away.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_number

HEALTHY = "healthy"
DEGRADED = "degraded"
UNHEALTHY = "unhealthy"

LEVELS = (HEALTHY, DEGRADED, UNHEALTHY)

THRESHOLDS = {
    "dropped_frames_percent": (1.0, 5.0),
    "round_trip_millis": (150.0, 400.0),
    "buffer_fill_percent": (60.0, 90.0),
}


def rate_signal(name, value):
    """Classify one telemetry reading."""
    if name not in THRESHOLDS:
        raise ValidationError(
            "unknown signal {}".format(name),
            field="name",
            details={"known": sorted(THRESHOLDS)},
        )
    warn, fail = THRESHOLDS[name]
    reading = require_number(value, name, minimum=0)
    if reading >= fail:
        return UNHEALTHY
    if reading >= warn:
        return DEGRADED
    return HEALTHY


def worst(levels, default=HEALTHY):
    """The most severe level in ``levels``."""
    found = default
    for level in levels:
        if level not in LEVELS:
            raise ValidationError("unknown level {}".format(level), field="levels")
        if LEVELS.index(level) > LEVELS.index(found):
            found = level
    return found


def assess(readings):
    """Classify every reading and report the overall status."""
    signals = {}
    for name, value in sorted(readings.items()):
        signals[name] = rate_signal(name, value)
    return {
        "signals": signals,
        "status": worst(signals.values()),
        "degraded": tuple(
            name for name, level in sorted(signals.items()) if level != HEALTHY
        ),
    }


def should_reduce_bitrate(readings):
    """Whether the encoder should step down a rung."""
    return assess(readings)["status"] != HEALTHY


def recommended_kbps(current_kbps, readings, floor=400):
    """Back off when the link is struggling, recover when it is not."""
    rate = require_number(current_kbps, "current_kbps", minimum=1)
    status = assess(readings)["status"]
    if status == UNHEALTHY:
        return max(int(floor), int(rate * 0.5))
    if status == DEGRADED:
        return max(int(floor), int(rate * 0.75))
    return int(rate)
