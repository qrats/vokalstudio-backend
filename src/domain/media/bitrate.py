"""Rendition ladders.

A live session is encoded once per rung of a ladder.  Rungs above the source
resolution are pointless, and the total bitrate has to fit the customer's
upstream, so building the ladder is a small selection problem rather than a
constant.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int, require_text

LADDER = (
    {"name": "240p", "height": 240, "video_kbps": 400, "audio_kbps": 64},
    {"name": "360p", "height": 360, "video_kbps": 800, "audio_kbps": 96},
    {"name": "480p", "height": 480, "video_kbps": 1400, "audio_kbps": 128},
    {"name": "720p", "height": 720, "video_kbps": 2800, "audio_kbps": 128},
    {"name": "1080p", "height": 1080, "video_kbps": 5000, "audio_kbps": 192},
    {"name": "1440p", "height": 1440, "video_kbps": 9000, "audio_kbps": 192},
    {"name": "2160p", "height": 2160, "video_kbps": 16000, "audio_kbps": 256},
)

BY_NAME = {rung["name"]: rung for rung in LADDER}
OVERHEAD_PERCENT = 12


class Rendition:
    """One rung of the ladder."""

    __slots__ = ("name", "height", "video_kbps", "audio_kbps")

    def __init__(self, name, height, video_kbps, audio_kbps):
        self.name = require_text(name, "name", max_length=20)
        self.height = require_int(height, "height", minimum=144, maximum=4320)
        self.video_kbps = require_int(video_kbps, "video_kbps", minimum=50)
        self.audio_kbps = require_int(audio_kbps, "audio_kbps", minimum=32)

    @classmethod
    def named(cls, name):
        key = require_text(name, "name", max_length=20).lower()
        if key not in BY_NAME:
            raise ValidationError(
                "unknown rendition {}".format(key),
                field="name",
                details={"allowed": sorted(BY_NAME)},
            )
        return cls(**BY_NAME[key])

    @property
    def total_kbps(self):
        return self.video_kbps + self.audio_kbps

    def with_overhead(self, percent=OVERHEAD_PERCENT):
        """Bitrate including muxing and network overhead, rounded up."""
        extra = require_int(percent, "percent", minimum=0, maximum=100)
        return -(-self.total_kbps * (100 + extra) // 100)

    def to_dict(self):
        return {
            "name": self.name,
            "height": self.height,
            "video_kbps": self.video_kbps,
            "audio_kbps": self.audio_kbps,
            "total_kbps": self.total_kbps,
        }

    def __eq__(self, other):
        return isinstance(other, Rendition) and other.to_dict() == self.to_dict()

    def __lt__(self, other):
        return self.height < other.height

    def __hash__(self):
        return hash(("rendition", self.name, self.height))

    def __repr__(self):
        return "Rendition({}, {} kbps)".format(self.name, self.total_kbps)


def rungs_up_to(source_height):
    """Every rung at or below the source height, largest first."""
    height = require_int(source_height, "source_height", minimum=1)
    usable = [Rendition(**rung) for rung in LADDER if rung["height"] <= height]
    return tuple(sorted(usable, reverse=True))


def build_ladder(source_height, upstream_kbps, max_rungs=4):
    """Pick the rungs that fit inside ``upstream_kbps``, highest quality first."""
    budget = require_int(upstream_kbps, "upstream_kbps", minimum=1)
    limit = require_int(max_rungs, "max_rungs", minimum=1, maximum=len(LADDER))
    chosen = []
    spent = 0
    for rung in rungs_up_to(source_height):
        if len(chosen) >= limit:
            break
        cost = rung.with_overhead()
        if spent + cost > budget:
            continue
        chosen.append(rung)
        spent += cost
    return tuple(chosen)


def ladder_cost(renditions, percent=OVERHEAD_PERCENT):
    return sum(rendition.with_overhead(percent) for rendition in renditions)


def fits(renditions, upstream_kbps):
    return ladder_cost(renditions) <= require_int(
        upstream_kbps, "upstream_kbps", minimum=1
    )


def best_single(source_height, upstream_kbps):
    """The highest rung that fits on its own, or ``None``."""
    for rung in rungs_up_to(source_height):
        if rung.with_overhead() <= upstream_kbps:
            return rung
    return None
