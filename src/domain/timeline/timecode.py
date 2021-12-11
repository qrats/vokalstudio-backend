"""Frame accurate timecode.

Video renditions are cut on frame boundaries, so an offset expressed in
milliseconds has to be snapped before it is handed to the encoder.  Drop-frame
timecode is supported for the 29.97 and 59.94 rates the studio ingests.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int, require_number, require_text

SUPPORTED_RATES = (23.976, 24.0, 25.0, 29.97, 30.0, 50.0, 59.94, 60.0)
DROP_FRAME_RATES = (29.97, 59.94)


def nominal_rate(rate):
    """Return the integer frame count a rate is nominally quoted at."""
    return int(round(float(rate)))


def is_drop_frame(rate):
    return round(float(rate), 3) in DROP_FRAME_RATES


def validate_rate(rate, field="rate"):
    value = round(require_number(rate, field, minimum=1), 3)
    if value not in SUPPORTED_RATES:
        raise ValidationError(
            "{} must be one of {}".format(
                field, ", ".join(str(item) for item in SUPPORTED_RATES)
            ),
            field=field,
        )
    return value


class Timecode:
    """A frame index paired with the rate it was counted at."""

    __slots__ = ("frames", "rate")

    def __init__(self, frames, rate=25.0):
        self.frames = require_int(frames, "frames", minimum=0)
        self.rate = validate_rate(rate)

    @classmethod
    def from_millis(cls, millis, rate=25.0):
        checked = validate_rate(rate)
        count = require_int(millis, "millis", minimum=0)
        return cls(int(count * checked // 1000), checked)

    @classmethod
    def parse(cls, text, rate=25.0, field="timecode"):
        raw = require_text(text, field)
        separator = ";" if ";" in raw else ":"
        parts = raw.replace(";", ":").split(":")
        if len(parts) != 4:
            raise ValidationError(
                "{} must look like HH:MM:SS:FF".format(field), field=field
            )
        try:
            hours, minutes, seconds, frames = (int(part, 10) for part in parts)
        except ValueError:
            raise ValidationError(
                "{} must look like HH:MM:SS:FF".format(field), field=field
            ) from None
        checked = validate_rate(rate)
        per_second = nominal_rate(checked)
        if frames >= per_second or minutes > 59 or seconds > 59:
            raise ValidationError(
                "{} has an out of range component".format(field), field=field
            )
        drop = separator == ";" or is_drop_frame(checked)
        total = ((hours * 60 + minutes) * 60 + seconds) * per_second + frames
        if drop:
            dropped = 2 * (per_second // 30)
            total -= dropped * (60 * hours + minutes - (hours * 6 + minutes // 10))
        return cls(total, checked)

    @property
    def millis(self):
        return int(round(self.frames * 1000 / self.rate))

    def format(self):
        per_second = nominal_rate(self.rate)
        count = self.frames
        separator = ":"
        if is_drop_frame(self.rate):
            separator = ";"
            dropped = 2 * (per_second // 30)
            frames_per_ten_minutes = per_second * 600 - dropped * 9
            frames_per_minute = per_second * 60 - dropped
            blocks = count // frames_per_ten_minutes
            remainder = count % frames_per_ten_minutes
            count += dropped * 9 * blocks
            if remainder >= dropped:
                count += dropped * ((remainder - dropped) // frames_per_minute)
        frames = count % per_second
        total_seconds = count // per_second
        return "{:02d}:{:02d}:{:02d}{}{:02d}".format(
            total_seconds // 3600,
            (total_seconds % 3600) // 60,
            total_seconds % 60,
            separator,
            frames,
        )

    def plus_frames(self, frames):
        return Timecode(self.frames + require_int(frames, "frames"), self.rate)

    def at_rate(self, rate):
        """Re-express the same wall-clock offset at another frame rate."""
        return Timecode.from_millis(self.millis, rate)

    def to_dict(self):
        return {"frames": self.frames, "rate": self.rate, "timecode": self.format()}

    def __eq__(self, other):
        return (
            isinstance(other, Timecode)
            and other.frames == self.frames
            and other.rate == self.rate
        )

    def __hash__(self):
        return hash(("timecode", self.frames, self.rate))

    def __repr__(self):
        return "Timecode({} @ {})".format(self.format(), self.rate)


def snap_millis(millis, rate):
    """Round ``millis`` down onto the nearest earlier frame boundary."""
    return Timecode.from_millis(millis, rate).millis
