from src.domain.timeline import timecode as mod
from tests.support import DomainTestCase


class RateTests(DomainTestCase):
    def test_nominal_rate_rounds(self):
        self.assertEqual(30, mod.nominal_rate(29.97))

    def test_nominal_rate_of_integer(self):
        self.assertEqual(25, mod.nominal_rate(25.0))

    def test_drop_frame_detection(self):
        self.assertTrue(mod.is_drop_frame(29.97))
        self.assertTrue(mod.is_drop_frame(59.94))

    def test_non_drop_frame(self):
        self.assertFalse(mod.is_drop_frame(25.0))

    def test_validate_accepts_supported(self):
        self.assertEqual(23.976, mod.validate_rate(23.976))

    def test_validate_rejects_unsupported(self):
        self.assertField("rate", mod.validate_rate, 48.0)

    def test_validate_rejects_zero(self):
        self.assertField("rate", mod.validate_rate, 0)

    def test_validate_field_name(self):
        self.assertField("fps", mod.validate_rate, 48.0, "fps")


class ConstructionTests(DomainTestCase):
    def test_frames_and_rate(self):
        code = mod.Timecode(50, 25.0)
        self.assertEqual(50, code.frames)
        self.assertEqual(25.0, code.rate)

    def test_default_rate(self):
        self.assertEqual(25.0, mod.Timecode(0).rate)

    def test_negative_frames_are_rejected(self):
        self.assertField("frames", mod.Timecode, -1)

    def test_from_millis(self):
        self.assertEqual(25, mod.Timecode.from_millis(1000, 25.0).frames)

    def test_from_millis_truncates(self):
        self.assertEqual(0, mod.Timecode.from_millis(39, 25.0).frames)

    def test_from_millis_rejects_negative(self):
        self.assertField("millis", mod.Timecode.from_millis, -1, 25.0)


class ParseTests(DomainTestCase):
    def test_non_drop(self):
        self.assertEqual(25, mod.Timecode.parse("00:00:01:00", 25.0).frames)

    def test_frames_component(self):
        self.assertEqual(27, mod.Timecode.parse("00:00:01:02", 25.0).frames)

    def test_drop_frame_semicolon(self):
        self.assertEqual(17982, mod.Timecode.parse("00:10:00;00", 29.97).frames)

    def test_drop_frame_first_minute(self):
        self.assertEqual(1800, mod.Timecode.parse("00:01:00;02", 29.97).frames)

    def test_wrong_shape(self):
        self.assertField("timecode", mod.Timecode.parse, "00:00:01")

    def test_non_numeric(self):
        self.assertField("timecode", mod.Timecode.parse, "aa:bb:cc:dd")

    def test_frames_out_of_range(self):
        self.assertField("timecode", mod.Timecode.parse, "00:00:00:25", 25.0)

    def test_minutes_out_of_range(self):
        self.assertField("timecode", mod.Timecode.parse, "00:60:00:00", 25.0)

    def test_field_name(self):
        self.assertField("cue", mod.Timecode.parse, "x", 25.0, "cue")


class FormatTests(DomainTestCase):
    def test_hour(self):
        self.assertEqual("01:00:00:00", mod.Timecode(90000, 25.0).format())

    def test_frames(self):
        self.assertEqual("00:00:01:02", mod.Timecode(27, 25.0).format())

    def test_drop_frame_uses_semicolon(self):
        self.assertIn(";", mod.Timecode(0, 29.97).format())

    def test_drop_frame_round_trip(self):
        for label in ("00:10:00;00", "00:01:00;02", "01:00:00;00"):
            code = mod.Timecode.parse(label, 29.97)
            self.assertEqual(label, code.format(), label)

    def test_non_drop_round_trip(self):
        for label in ("00:00:00:00", "00:10:00:00", "02:34:56:12"):
            self.assertEqual(label, mod.Timecode.parse(label, 25.0).format(), label)


class ConversionTests(DomainTestCase):
    def test_millis(self):
        self.assertEqual(1000, mod.Timecode(25, 25.0).millis)

    def test_plus_frames(self):
        self.assertEqual(30, mod.Timecode(25, 25.0).plus_frames(5).frames)

    def test_at_rate_keeps_wall_clock(self):
        code = mod.Timecode(25, 25.0)
        self.assertEqual(50, code.at_rate(50.0).frames)

    def test_to_dict(self):
        payload = mod.Timecode(25, 25.0).to_dict()
        self.assertEqual(25, payload["frames"])
        self.assertEqual("00:00:01:00", payload["timecode"])

    def test_snap_millis_rounds_down(self):
        self.assertEqual(1000, mod.snap_millis(1039, 25.0))

    def test_snap_millis_on_boundary(self):
        self.assertEqual(1000, mod.snap_millis(1000, 25.0))


class ValueSemanticsTests(DomainTestCase):
    def test_equality(self):
        self.assertEqual(mod.Timecode(1, 25.0), mod.Timecode(1, 25.0))

    def test_rate_matters(self):
        self.assertNotEqual(mod.Timecode(1, 25.0), mod.Timecode(1, 30.0))

    def test_hashable(self):
        self.assertEqual(1, len({mod.Timecode(1), mod.Timecode(1)}))

    def test_repr(self):
        self.assertIn("Timecode(", repr(mod.Timecode(1)))
