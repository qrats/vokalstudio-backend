from src.domain.distribution import destination as mod
from src.domain.media.asset import Asset
from tests.support import DomainTestCase


def audio(name="ep.mp3", size=5_000_000, duration="30:00"):
    return Asset("u-1", name, size, duration=duration)


class NormalizeTests(DomainTestCase):
    def test_lowercases(self):
        self.assertEqual("podbean", mod.normalize_destination("Podbean"))

    def test_unknown(self):
        error = self.assertRaisesCode(
            "validation_failed", mod.normalize_destination, "soundcloud"
        )
        self.assertIn("podbean", error.details["supported"])

    def test_empty(self):
        self.assertField("destination", mod.normalize_destination, "")

    def test_label(self):
        self.assertEqual("Podbean", mod.label_of("podbean"))

    def test_supported_are_sorted(self):
        found = mod.supported_destinations()
        self.assertEqual(tuple(sorted(found)), found)

    def test_every_entry_is_complete(self):
        for name, record in mod.DESTINATIONS.items():
            self.assertTrue(record["containers"], name)
            self.assertGreater(record["max_bytes"], 0, name)
            self.assertGreater(record["max_duration_millis"], 0, name)


class CapabilityTests(DomainTestCase):
    def test_accepts_container(self):
        self.assertTrue(mod.accepts_container("podbean", "mp3"))

    def test_rejects_container(self):
        self.assertFalse(mod.accepts_container("spotify", "mp4"))

    def test_container_alias(self):
        self.assertTrue(mod.accepts_container("youtube", "m4v"))

    def test_needs_oauth(self):
        self.assertTrue(mod.needs_oauth("podbean"))

    def test_does_not_need_oauth(self):
        self.assertFalse(mod.needs_oauth("apple"))

    def test_needs_artwork(self):
        self.assertTrue(mod.needs_artwork("apple"))

    def test_does_not_need_artwork(self):
        self.assertFalse(mod.needs_artwork("youtube"))


class RejectionTests(DomainTestCase):
    def test_a_good_file_is_accepted(self):
        self.assertEqual((), mod.rejections("podbean", audio()))

    def test_accepts_helper(self):
        self.assertTrue(mod.accepts("podbean", audio()))

    def test_wrong_container(self):
        self.assertEqual(("container",), mod.rejections("spotify", audio("ep.mp4")))

    def test_too_large(self):
        found = mod.rejections("spotify", audio(size=300 * 1024 ** 2))
        self.assertEqual(("size",), found)

    def test_too_long(self):
        found = mod.rejections("podbean", audio(duration="06:00:00"))
        self.assertEqual(("duration",), found)

    def test_missing_artwork(self):
        self.assertEqual(("artwork",), mod.rejections("podbean", audio(), False))

    def test_artwork_is_ignored_where_it_is_not_needed(self):
        self.assertEqual((), mod.rejections("youtube", audio("ep.mp4"), False))

    def test_several_reasons_are_sorted(self):
        found = mod.rejections("spotify", audio("ep.wav", 300 * 1024 ** 2), False)
        self.assertEqual(("artwork", "container", "size"), found)

    def test_exactly_at_the_size_limit(self):
        limit = mod.DESTINATIONS["spotify"]["max_bytes"]
        self.assertEqual((), mod.rejections("spotify", audio(size=limit)))
