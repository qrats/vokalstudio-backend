"""Loudness normalisation.

Podcast destinations want -16 LUFS, broadcast wants -23, and a live restream
target wants whatever the platform asks for.  The gain to apply is a
subtraction, but the true-peak ceiling means it sometimes cannot be applied in
full, and that is the case this module exists to get right.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_number

TARGETS = {
    "podcast": -16.0,
    "broadcast": -23.0,
    "music": -14.0,
    "voice": -19.0,
}

DEFAULT_TARGET = "podcast"
TRUE_PEAK_CEILING = -1.0
MAX_GAIN_DB = 12.0


def target_for(profile, field="profile"):
    """The LUFS target for a named delivery profile."""
    if profile not in TARGETS:
        raise ValidationError(
            "unknown profile {}".format(profile),
            field=field,
            details={"allowed": sorted(TARGETS)},
        )
    return TARGETS[profile]


def gain_to_target(measured_lufs, profile=DEFAULT_TARGET):
    """The gain in dB that would move ``measured_lufs`` onto the target."""
    measured = require_number(measured_lufs, "measured_lufs", minimum=-70, maximum=0)
    return round(target_for(profile) - measured, 2)


def clamp_gain(gain_db, true_peak_db, ceiling=TRUE_PEAK_CEILING):
    """Reduce ``gain_db`` so the true peak stays under ``ceiling``."""
    gain = require_number(gain_db, "gain_db", minimum=-MAX_GAIN_DB, maximum=MAX_GAIN_DB)
    peak = require_number(true_peak_db, "true_peak_db", minimum=-70, maximum=12)
    headroom = require_number(ceiling, "ceiling", minimum=-12, maximum=0) - peak
    if gain <= headroom:
        return round(gain, 2)
    return round(headroom, 2)


def normalisation_plan(measured_lufs, true_peak_db, profile=DEFAULT_TARGET):
    """What to do to one asset to hit a delivery target."""
    wanted = gain_to_target(measured_lufs, profile)
    bounded = max(-MAX_GAIN_DB, min(MAX_GAIN_DB, wanted))
    applied = clamp_gain(bounded, true_peak_db)
    resulting = round(require_number(measured_lufs, "measured_lufs") + applied, 2)
    return {
        "profile": profile,
        "target_lufs": target_for(profile),
        "measured_lufs": round(float(measured_lufs), 2),
        "wanted_gain_db": wanted,
        "applied_gain_db": applied,
        "resulting_lufs": resulting,
        "limited": applied < wanted,
        "on_target": abs(resulting - target_for(profile)) <= 0.5,
    }


def is_within_tolerance(measured_lufs, profile=DEFAULT_TARGET, tolerance=1.0):
    """Whether an asset is already close enough to the target to leave alone."""
    allowed = require_number(tolerance, "tolerance", minimum=0, maximum=6)
    return abs(target_for(profile) - float(measured_lufs)) <= allowed


def loudest(measurements, default=None):
    """The entry with the highest (least negative) integrated loudness."""
    ordered = sorted(measurements, key=lambda pair: pair[1])
    return ordered[-1] if ordered else default
