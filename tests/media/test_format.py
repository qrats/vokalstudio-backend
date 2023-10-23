from src.domain.media import format as mod
from tests.support import DomainTestCase


class NormalizeTests(DomainTestCase):
    def test_lowercases(self):
        self.assertEqual("mp3", mod.normalize_container("MP3"))

    def test_strips_a_leading_dot(self):
        self.assertEqual("mp4", mod.normalize_container(".mp4"))

    def test_alias(self):
        self.assertEqual("jpeg", mod.normalize_container("jpg"))

    def test_second_alias(self):
        self.assertEqual("mp4", mod.normalize_container("m4v"))

    def test_unknown(self):
        error = self.assertRaisesCode("validation_failed", mod.normalize_container, "avi")
        self.assertIn("mp4", error.details["supported"])

    def test_empty(self):
        self.assertField("container", mod.normalize_container, "")

    def test_field_name(self):
        self.assertField("output", mod.normalize_container, "avi", "output")


class TableTests(DomainTestCase):
    def test_audio_kind(self):
        self.assertEqual(mod.AUDIO, mod.kind_of("mp3"))

    def test_video_kind(self):
        self.assertEqual(mod.VIDEO, mod.kind_of("mov"))

    def test_image_kind(self):
        self.assertEqual(mod.IMAGE, mod.kind_of("png"))

    def test_extension(self):
        self.assertEqual("jpg", mod.extension_of("jpeg"))

    def test_extension_matches_the_name_usually(self):
        self.assertEqual("mp4", mod.extension_of("mp4"))

    def test_codecs(self):
        self.assertIn("h264", mod.codecs_for("mp4"))

    def test_default_codec_is_the_first(self):
        self.assertEqual("h264", mod.default_codec("mp4"))

    def test_every_entry_is_complete(self):
        for name, entry in mod.CONTAINERS.items():
            self.assertIn(entry["kind"], mod.KINDS, name)
            self.assertTrue(entry["codecs"], name)
            self.assertTrue(entry["extension"], name)

    def test_aliases_point_at_real_containers(self):
        for target in mod._ALIASES.values():
            self.assertIn(target, mod.CONTAINERS)


class SupportTests(DomainTestCase):
    def test_supported_pair(self):
        self.assertTrue(mod.supports("mp4", "h264"))

    def test_case_insensitive_codec(self):
        self.assertTrue(mod.supports("mp4", "H264"))

    def test_unsupported_pair(self):
        self.assertFalse(mod.supports("mp4", "vp9"))

    def test_require_supported_returns_the_pair(self):
        self.assertEqual(("mp4", "h264"), mod.require_supported("mp4", "h264"))

    def test_require_supported_raises(self):
        error = self.assertRaisesCode(
            "validation_failed", mod.require_supported, "mp3", "aac"
        )
        self.assertEqual(["mp3"], error.details["allowed"])


class FilenameTests(DomainTestCase):
    def test_extracts_the_container(self):
        self.assertEqual("mp3", mod.container_from_filename("episode-12.mp3"))

    def test_uses_the_last_dot(self):
        self.assertEqual("mp4", mod.container_from_filename("a.b.c.mp4"))

    def test_alias(self):
        self.assertEqual("jpeg", mod.container_from_filename("cover.JPG"))

    def test_no_extension(self):
        self.assertField("filename", mod.container_from_filename, "episode")

    def test_unknown_extension(self):
        self.assertField("filename", mod.container_from_filename, "clip.avi")


class DeliveryTests(DomainTestCase):
    def test_mp3_is_deliverable(self):
        self.assertTrue(mod.is_deliverable("mp3"))

    def test_wav_is_not(self):
        self.assertFalse(mod.is_deliverable("wav"))

    def test_png_is_not(self):
        self.assertFalse(mod.is_deliverable("png"))

    def test_streaming_container_carries_the_streaming_codec(self):
        self.assertTrue(mod.supports(mod.STREAMING_CONTAINER, mod.STREAMING_CODEC))

    def test_delivery_containers_are_known(self):
        for container in mod.DELIVERY_CONTAINERS:
            self.assertIn(container, mod.CONTAINERS)
