from src.domain.media import storage as mod
from tests.support import DomainTestCase


class SanitiseTests(DomainTestCase):
    def test_keeps_a_clean_name(self):
        self.assertEqual("episode-12.mp3", mod.sanitise_filename("episode-12.mp3"))

    def test_replaces_spaces(self):
        self.assertEqual("My-Episode.mp3", mod.sanitise_filename("My Episode.mp3"))

    def test_replaces_punctuation(self):
        self.assertEqual("a-b.mp3", mod.sanitise_filename("a/#?b.mp3"))

    def test_lowercases_the_extension(self):
        self.assertTrue(mod.sanitise_filename("clip.MP3").endswith(".mp3"))

    def test_no_extension(self):
        self.assertEqual("episode", mod.sanitise_filename("episode"))

    def test_trims_separators(self):
        self.assertEqual("abc.mp3", mod.sanitise_filename("--abc--.mp3"))

    def test_truncates_a_long_stem(self):
        name = mod.sanitise_filename("a" * 200 + ".mp3")
        self.assertEqual(124, len(name))

    def test_nothing_usable(self):
        self.assertField("filename", mod.sanitise_filename, "###.mp3")

    def test_empty(self):
        self.assertField("filename", mod.sanitise_filename, "")


class BuildKeyTests(DomainTestCase):
    def test_shape(self):
        key = mod.build_key("uploads", "u-1", "episode-12.mp3")
        self.assertTrue(key.startswith("uploads/u-1/"))
        self.assertTrue(key.endswith("-episode-12.mp3"))

    def test_stable(self):
        self.assertEqual(
            mod.build_key("uploads", "u-1", "a.mp3"),
            mod.build_key("uploads", "u-1", "a.mp3"),
        )

    def test_depends_on_the_owner(self):
        self.assertNotEqual(
            mod.build_key("uploads", "u-1", "a.mp3"),
            mod.build_key("uploads", "u-2", "a.mp3"),
        )

    def test_container_overrides_the_extension(self):
        key = mod.build_key("renders", "u-1", "episode.wav", "mp3")
        self.assertTrue(key.endswith(".mp3"))

    def test_unknown_prefix(self):
        error = self.assertRaisesCode(
            "validation_failed", mod.build_key, "tmp", "u-1", "a.mp3"
        )
        self.assertIn("uploads", error.details["allowed"])

    def test_empty_owner(self):
        self.assertField("user_id", mod.build_key, "uploads", "", "a.mp3")

    def test_key_is_valid(self):
        self.assertTrue(mod.is_valid_key(mod.build_key("uploads", "u-1", "a.mp3")))


class ValidateKeyTests(DomainTestCase):
    def test_simple_key(self):
        self.assertTrue(mod.is_valid_key("uploads/u-1/abc.mp3"))

    def test_leading_slash_is_rejected(self):
        self.assertFalse(mod.is_valid_key("/uploads/a.mp3"))

    def test_traversal_is_rejected(self):
        self.assertFalse(mod.is_valid_key("uploads/../etc/passwd"))

    def test_spaces_are_rejected(self):
        self.assertFalse(mod.is_valid_key("uploads/a b.mp3"))

    def test_empty_is_rejected(self):
        self.assertFalse(mod.is_valid_key(""))

    def test_non_string_is_rejected(self):
        self.assertFalse(mod.is_valid_key(None))

    def test_require_key_returns_it(self):
        self.assertEqual("uploads/a.mp3", mod.require_key("uploads/a.mp3"))

    def test_require_key_raises(self):
        self.assertField("key", mod.require_key, "../a")

    def test_require_key_field_name(self):
        self.assertField("intro_key", mod.require_key, "../a", "intro_key")


class OwnerTests(DomainTestCase):
    def test_extracts_the_owner(self):
        key = mod.build_key("uploads", "u-1", "a.mp3")
        self.assertEqual("u-1", mod.owner_of(key))

    def test_rejects_a_foreign_key(self):
        self.assertField("key", mod.owner_of, "some/other/thing")

    def test_rejects_a_short_key(self):
        self.assertField("key", mod.owner_of, "uploads/a.mp3")

    def test_rejects_an_invalid_key(self):
        self.assertField("key", mod.owner_of, "../a")


class DescriptorTests(DomainTestCase):
    def test_shape(self):
        descriptor = mod.upload_descriptor("uploads", "u-1", "episode.mp3", 5_000_000)
        self.assertEqual(5_000_000, descriptor["size_bytes"])
        self.assertEqual(mod.SIGNED_URL_TTL_SECONDS, descriptor["expires_in"])

    def test_content_type(self):
        descriptor = mod.upload_descriptor("uploads", "u-1", "episode.mp3", 100)
        self.assertEqual("audio/mpeg", descriptor["content_type"])

    def test_video_content_type(self):
        descriptor = mod.upload_descriptor("uploads", "u-1", "episode.mp4", 100)
        self.assertEqual("video/mp4", descriptor["content_type"])

    def test_unknown_extension_falls_back(self):
        descriptor = mod.upload_descriptor("transcripts", "u-1", "notes", 100)
        self.assertEqual("application/octet-stream", descriptor["content_type"])

    def test_zero_size(self):
        self.assertField(
            "size_bytes", mod.upload_descriptor, "uploads", "u-1", "a.mp3", 0
        )

    def test_over_the_limit(self):
        self.assertField(
            "size_bytes",
            mod.upload_descriptor,
            "uploads",
            "u-1",
            "a.mp3",
            mod.MAX_UPLOAD_BYTES + 1,
        )

    def test_exactly_the_limit(self):
        descriptor = mod.upload_descriptor(
            "uploads", "u-1", "a.mp3", mod.MAX_UPLOAD_BYTES
        )
        self.assertEqual(mod.MAX_UPLOAD_BYTES, descriptor["size_bytes"])


class ContentTypeTests(DomainTestCase):
    def test_audio(self):
        self.assertEqual("audio/mpeg", mod.content_type_for("mp3"))

    def test_image_alias(self):
        self.assertEqual("image/jpeg", mod.content_type_for("jpg"))

    def test_video(self):
        self.assertEqual("video/quicktime", mod.content_type_for("mov"))

    def test_every_container_has_a_type(self):
        from src.domain.media.format import CONTAINERS

        for container in CONTAINERS:
            self.assertNotEqual(
                "application/octet-stream", mod.content_type_for(container), container
            )
