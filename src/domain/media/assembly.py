"""Building the render plan for one episode.

The output is intro, body, outro laid end to end, with the fade overlaps
subtracted so that the timeline adds up.  Nothing here touches a file; it
produces the offsets a worker then hands to ffmpeg.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int, require_sequence
from src.domain.media.format import AUDIO, IMAGE
from src.domain.media.loudness import normalisation_plan
from src.domain.timeline.duration import Duration


class Segment:
    """One piece of the finished timeline."""

    __slots__ = ("role", "asset_key", "start_millis", "duration_millis", "fade_in_millis")

    def __init__(self, role, asset_key, start_millis, duration_millis, fade_in_millis=0):
        self.role = role
        self.asset_key = asset_key
        self.start_millis = require_int(start_millis, "start_millis", minimum=0)
        self.duration_millis = require_int(duration_millis, "duration_millis", minimum=1)
        self.fade_in_millis = require_int(fade_in_millis, "fade_in_millis", minimum=0)

    @property
    def end_millis(self):
        return self.start_millis + self.duration_millis

    def to_dict(self):
        return {
            "role": self.role,
            "asset_key": self.asset_key,
            "start_millis": self.start_millis,
            "duration_millis": self.duration_millis,
            "end_millis": self.end_millis,
            "fade_in_millis": self.fade_in_millis,
        }

    def __eq__(self, other):
        return isinstance(other, Segment) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("segment", self.role, self.asset_key, self.start_millis))

    def __repr__(self):
        return "Segment({}, {}ms)".format(self.role, self.start_millis)


def build_timeline(configuration, body, fade_millis=None):
    """Lay the intro, the body and the outro onto one timeline."""
    if body.kind == IMAGE:
        raise ValidationError("the body must be audio or video", field="body")
    if not configuration.applies_to(body):
        raise ValidationError(
            "configuration cannot be applied to this asset", field="body"
        )
    fade = configuration.fade_millis if fade_millis is None else require_int(
        fade_millis, "fade_millis", minimum=0
    )
    segments = []
    cursor = 0
    if configuration.has_intro():
        intro = configuration.intro
        segments.append(Segment("intro", intro.key, cursor, intro.duration.millis))
        cursor += intro.duration.millis
        cursor -= min(fade, intro.duration.millis - 1, body.duration.millis - 1)
    segments.append(
        Segment("body", body.key, cursor, body.duration.millis, fade if cursor else 0)
    )
    cursor += body.duration.millis
    if configuration.has_outro():
        outro = configuration.outro
        cursor -= min(fade, outro.duration.millis - 1, body.duration.millis - 1)
        segments.append(Segment("outro", outro.key, cursor, outro.duration.millis, fade))
    return tuple(segments)


def timeline_duration(segments):
    """Total length of a timeline, in whole milliseconds."""
    materialised = require_sequence(segments, "segments", min_length=1)
    return Duration(max(segment.end_millis for segment in materialised))


def render_plan(configuration, body, measured_lufs=None, true_peak_db=None):
    """Everything a render worker needs for one episode."""
    segments = build_timeline(configuration, body)
    plan = {
        "user_id": configuration.user_id,
        "segments": [segment.to_dict() for segment in segments],
        "duration_millis": timeline_duration(segments).millis,
        "watermark": (
            configuration.watermark.to_dict()
            if configuration.watermark and body.kind != AUDIO
            else None
        ),
        "loudness": None,
    }
    if configuration.normalise and measured_lufs is not None:
        plan["loudness"] = normalisation_plan(
            measured_lufs,
            true_peak_db if true_peak_db is not None else -3.0,
            configuration.loudness_profile,
        )
    return plan


def overlaps(segments):
    """Pairs of segment indexes whose spans overlap, after the fades."""
    materialised = tuple(segments)
    found = []
    for left in range(len(materialised)):
        for right in range(left + 1, len(materialised)):
            one, two = materialised[left], materialised[right]
            if one.start_millis < two.end_millis and two.start_millis < one.end_millis:
                found.append((left, right))
    return tuple(found)
