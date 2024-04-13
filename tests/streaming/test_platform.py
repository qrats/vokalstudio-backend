from src.domain.streaming import platform as mod
from tests.support import DomainTestCase


class NormalizeTests(DomainTestCase):
    def test_lowercases(self):
        self.assertEqual("youtube", mod.normalize_platform("YouTube"))

    def test_unknown(self):
        error = self.assertRaisesCode("validation_failed", mod.normalize_platform, "vimeo")
        self.assertIn("youtube", error.details["supported"])

    def test_empty(self):
        self.assertField("platform", mod.normalize_platform, "")

    def test_field_name(self):
        self.assertField("service", mod.normalize_platform, "vimeo", "service")


class TableTests(DomainTestCase):
    def test_label(self):
        self.assertEqual("YouTube Live", mod.label_of("youtube"))

    def test_custom_is_present(self):
        self.assertIn(mod.CUSTOM, mod.PLATFORMS)

    def test_entry_is_a_copy(self):
        entry = mod.entry("youtube")
        entry["label"] = "changed"
        self.assertEqual("YouTube Live", mod.label_of("youtube"))

    def test_is_custom(self):
        self.assertTrue(mod.is_custom("custom"))

    def test_is_not_custom(self):
        self.assertFalse(mod.is_custom("youtube"))

    def test_requires_secure(self):
        self.assertTrue(mod.requires_secure("facebook"))

    def test_does_not_require_secure(self):
        self.assertFalse(mod.requires_secure("youtube"))

    def test_max_kbps(self):
        self.assertEqual(6000, mod.max_kbps("twitch"))

    def test_minimum_key_length(self):
        self.assertEqual(24, mod.minimum_key_length("twitch"))

    def test_supported_platforms_are_sorted(self):
        platforms = mod.supported_platforms()
        self.assertEqual(tuple(sorted(platforms)), platforms)

    def test_every_entry_is_complete(self):
        for name, record in mod.PLATFORMS.items():
            self.assertTrue(record["label"], name)
            self.assertGreater(record["max_kbps"], 0, name)
            self.assertGreater(record["key_length"], 0, name)


class IngestTests(DomainTestCase):
    def test_plain_rtmp(self):
        self.assertEqual(
            "rtmp://a.rtmp.youtube.com/live2", mod.default_ingest("youtube")
        )

    def test_secure_platform_uses_rtmps(self):
        self.assertTrue(mod.default_ingest("facebook").startswith("rtmps://"))

    def test_custom_has_no_default(self):
        self.assertIsNone(mod.default_ingest("custom"))

    def test_every_non_custom_platform_has_an_ingest(self):
        for name in mod.supported_platforms():
            if name == mod.CUSTOM:
                continue
            self.assertIsNotNone(mod.default_ingest(name), name)
