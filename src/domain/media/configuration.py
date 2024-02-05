"""Media configuration.

Every studio has one configuration: which intro plays, which outro plays, where
the logo sits and whether the recording is normalised on the way out.  The
resources used to validate this ad hoc, which is why an intro could be set to a
still image.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_bool, require_choice, require_int, require_text
from src.domain.media.format import AUDIO, IMAGE, VIDEO
from src.domain.media.loudness import DEFAULT_TARGET, TARGETS

CORNERS = ("top_left", "top_right", "bottom_left", "bottom_right")
FADE_MAX_MILLIS = 10000


class Watermark:
    """Where the logo goes and how strongly it shows."""

    __slots__ = ("asset_key", "corner", "opacity_percent", "margin_pixels")

    def __init__(self, asset_key, corner="bottom_right", opacity_percent=80, margin_pixels=24):
        self.asset_key = require_text(asset_key, "asset_key", max_length=255)
        self.corner = require_choice(corner, "corner", CORNERS)
        self.opacity_percent = require_int(
            opacity_percent, "opacity_percent", minimum=1, maximum=100
        )
        self.margin_pixels = require_int(
            margin_pixels, "margin_pixels", minimum=0, maximum=400
        )

    def to_dict(self):
        return {
            "asset_key": self.asset_key,
            "corner": self.corner,
            "opacity_percent": self.opacity_percent,
            "margin_pixels": self.margin_pixels,
        }

    @classmethod
    def from_dict(cls, payload):
        return cls(
            payload["asset_key"],
            payload.get("corner", "bottom_right"),
            payload.get("opacity_percent", 80),
            payload.get("margin_pixels", 24),
        )

    def __eq__(self, other):
        return isinstance(other, Watermark) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("watermark", self.asset_key, self.corner))

    def __repr__(self):
        return "Watermark({}, {})".format(self.asset_key, self.corner)


class MediaConfiguration:
    """One studio's render settings."""

    __slots__ = (
        "user_id",
        "intro",
        "outro",
        "watermark",
        "loudness_profile",
        "normalise",
        "fade_millis",
    )

    def __init__(
        self,
        user_id,
        intro=None,
        outro=None,
        watermark=None,
        loudness_profile=DEFAULT_TARGET,
        normalise=True,
        fade_millis=0,
    ):
        self.user_id = require_text(user_id, "user_id", max_length=64)
        self.intro = self._check_bed(intro, "intro")
        self.outro = self._check_bed(outro, "outro")
        self.watermark = self._check_watermark(watermark)
        self.loudness_profile = require_choice(
            loudness_profile, "loudness_profile", tuple(TARGETS)
        )
        self.normalise = require_bool(normalise, "normalise")
        self.fade_millis = require_int(
            fade_millis, "fade_millis", minimum=0, maximum=FADE_MAX_MILLIS
        )

    @staticmethod
    def _check_bed(asset, field):
        if asset is None:
            return None
        if asset.kind == IMAGE:
            raise ValidationError(
                "{} must be audio or video".format(field), field=field
            )
        return asset

    @staticmethod
    def _check_watermark(watermark):
        if watermark is None:
            return None
        if not isinstance(watermark, Watermark):
            raise ValidationError("watermark must be a Watermark", field="watermark")
        return watermark

    def has_intro(self):
        return self.intro is not None

    def has_outro(self):
        return self.outro is not None

    def bed_duration_millis(self):
        total = 0
        for bed in (self.intro, self.outro):
            if bed is not None:
                total += bed.duration.millis
        return total

    def applies_to(self, asset):
        """Whether this configuration can be used with ``asset``."""
        if asset.kind == IMAGE:
            return False
        if self.watermark is not None and asset.kind == AUDIO:
            return False
        for bed in (self.intro, self.outro):
            if bed is not None and bed.kind == VIDEO and asset.kind == AUDIO:
                return False
        return True

    def without_watermark(self):
        return MediaConfiguration(
            self.user_id,
            self.intro,
            self.outro,
            None,
            self.loudness_profile,
            self.normalise,
            self.fade_millis,
        )

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "intro_key": self.intro.key if self.intro else None,
            "outro_key": self.outro.key if self.outro else None,
            "watermark": self.watermark.to_dict() if self.watermark else None,
            "loudness_profile": self.loudness_profile,
            "normalise": self.normalise,
            "fade_millis": self.fade_millis,
        }

    def __eq__(self, other):
        return isinstance(other, MediaConfiguration) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("configuration", self.user_id, self.loudness_profile))

    def __repr__(self):
        return "MediaConfiguration({})".format(self.user_id)
