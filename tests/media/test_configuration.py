from src.domain.media.asset import Asset
from src.domain.media import configuration as mod
from tests.support import DomainTestCase


def audio(name="body.mp3", role="main", duration="30:00"):
    return Asset("u-1", name, 5_000_000, duration=duration, role=role)


def video(name="body.mp4", role="main"):
    return Asset("u-1", name, 50_000_000, duration="30:00", role=role)


def cover():
    return Asset("u-1", "cover.png", 400_000, role="artwork")


class WatermarkTests(DomainTestCase):
    def test_defaults(self):
        mark = mod.Watermark("u-1/logo.png")
        self.assertEqual("bottom_right", mark.corner)
        self.assertEqual(80, mark.opacity_percent)
        self.assertEqual(24, mark.margin_pixels)

    def test_corner(self):
        self.assertEqual("top_left", mod.Watermark("k", "top_left").corner)

    def test_unknown_corner(self):
        self.assertField("corner", mod.Watermark, "k", "middle")

    def test_opacity_floor(self):
        self.assertField("opacity_percent", mod.Watermark, "k", "top_left", 0)

    def test_opacity_ceiling(self):
        self.assertField("opacity_percent", mod.Watermark, "k", "top_left", 101)

    def test_margin_ceiling(self):
        self.assertField("margin_pixels", mod.Watermark, "k", "top_left", 80, 401)

    def test_zero_margin_is_allowed(self):
        self.assertEqual(0, mod.Watermark("k", "top_left", 80, 0).margin_pixels)

    def test_empty_key(self):
        self.assertField("asset_key", mod.Watermark, "")

    def test_round_trip(self):
        self.assertRoundTrips(mod.Watermark.from_dict, mod.Watermark("k", "top_left", 50, 8))

    def test_equality(self):
        self.assertEqual(mod.Watermark("k"), mod.Watermark("k"))

    def test_hashable(self):
        self.assertEqual(1, len({mod.Watermark("k"), mod.Watermark("k")}))

    def test_repr(self):
        self.assertIn("bottom_right", repr(mod.Watermark("k")))


class ConstructionTests(DomainTestCase):
    def test_defaults(self):
        config = mod.MediaConfiguration("u-1")
        self.assertFalse(config.has_intro())
        self.assertFalse(config.has_outro())
        self.assertTrue(config.normalise)
        self.assertEqual("podcast", config.loudness_profile)
        self.assertEqual(0, config.fade_millis)

    def test_intro(self):
        config = mod.MediaConfiguration("u-1", intro=audio("intro.mp3", "intro", "00:05"))
        self.assertTrue(config.has_intro())

    def test_image_cannot_be_an_intro(self):
        self.assertField("intro", mod.MediaConfiguration, "u-1", cover())

    def test_image_cannot_be_an_outro(self):
        self.assertField("outro", mod.MediaConfiguration, "u-1", None, cover())

    def test_unknown_loudness_profile(self):
        self.assertField(
            "loudness_profile", mod.MediaConfiguration, "u-1", None, None, None, "cinema"
        )

    def test_watermark_must_be_a_watermark(self):
        self.assertField(
            "watermark", mod.MediaConfiguration, "u-1", None, None, "u-1/logo.png"
        )

    def test_fade_ceiling(self):
        self.assertField(
            "fade_millis",
            mod.MediaConfiguration,
            "u-1",
            None,
            None,
            None,
            "podcast",
            True,
            mod.FADE_MAX_MILLIS + 1,
        )

    def test_normalise_accepts_text(self):
        config = mod.MediaConfiguration("u-1", normalise="false")
        self.assertFalse(config.normalise)


class BedTests(DomainTestCase):
    def test_bed_duration_of_nothing(self):
        self.assertEqual(0, mod.MediaConfiguration("u-1").bed_duration_millis())

    def test_bed_duration_of_an_intro(self):
        config = mod.MediaConfiguration("u-1", intro=audio("i.mp3", "intro", "00:05"))
        self.assertEqual(5000, config.bed_duration_millis())

    def test_bed_duration_of_both(self):
        config = mod.MediaConfiguration(
            "u-1",
            intro=audio("i.mp3", "intro", "00:05"),
            outro=audio("o.mp3", "outro", "00:10"),
        )
        self.assertEqual(15000, config.bed_duration_millis())


class AppliesTests(DomainTestCase):
    def test_plain_configuration_applies_to_audio(self):
        self.assertTrue(mod.MediaConfiguration("u-1").applies_to(audio()))

    def test_never_applies_to_an_image(self):
        self.assertFalse(mod.MediaConfiguration("u-1").applies_to(cover()))

    def test_watermark_does_not_apply_to_audio(self):
        config = mod.MediaConfiguration("u-1", watermark=mod.Watermark("u-1/logo.png"))
        self.assertFalse(config.applies_to(audio()))

    def test_watermark_applies_to_video(self):
        config = mod.MediaConfiguration("u-1", watermark=mod.Watermark("u-1/logo.png"))
        self.assertTrue(config.applies_to(video()))

    def test_video_intro_does_not_apply_to_audio(self):
        config = mod.MediaConfiguration("u-1", intro=video("i.mp4", "intro"))
        self.assertFalse(config.applies_to(audio()))

    def test_audio_intro_applies_to_video(self):
        config = mod.MediaConfiguration("u-1", intro=audio("i.mp3", "intro", "00:05"))
        self.assertTrue(config.applies_to(video()))

    def test_without_watermark_makes_it_apply(self):
        config = mod.MediaConfiguration("u-1", watermark=mod.Watermark("u-1/logo.png"))
        self.assertTrue(config.without_watermark().applies_to(audio()))

    def test_without_watermark_returns_a_copy(self):
        config = mod.MediaConfiguration("u-1", watermark=mod.Watermark("u-1/logo.png"))
        config.without_watermark()
        self.assertIsNotNone(config.watermark)

    def test_without_watermark_keeps_the_beds(self):
        intro = audio("i.mp3", "intro", "00:05")
        config = mod.MediaConfiguration("u-1", intro=intro, watermark=mod.Watermark("k"))
        self.assertTrue(config.without_watermark().has_intro())


class SerialisationTests(DomainTestCase):
    def test_to_dict_empty(self):
        payload = mod.MediaConfiguration("u-1").to_dict()
        self.assertIsNone(payload["intro_key"])
        self.assertIsNone(payload["watermark"])

    def test_to_dict_with_beds(self):
        intro = audio("i.mp3", "intro", "00:05")
        payload = mod.MediaConfiguration("u-1", intro=intro).to_dict()
        self.assertEqual(intro.key, payload["intro_key"])

    def test_to_dict_with_watermark(self):
        config = mod.MediaConfiguration("u-1", watermark=mod.Watermark("k"))
        self.assertEqual("k", payload_key(config))

    def test_equality(self):
        self.assertEqual(mod.MediaConfiguration("u-1"), mod.MediaConfiguration("u-1"))

    def test_inequality(self):
        self.assertNotEqual(
            mod.MediaConfiguration("u-1"),
            mod.MediaConfiguration("u-1", loudness_profile="music"),
        )

    def test_hashable(self):
        self.assertEqual(
            1, len({mod.MediaConfiguration("u-1"), mod.MediaConfiguration("u-1")})
        )

    def test_repr(self):
        self.assertIn("u-1", repr(mod.MediaConfiguration("u-1")))


def payload_key(config):
    return config.to_dict()["watermark"]["asset_key"]
