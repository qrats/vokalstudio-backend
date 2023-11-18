from src.domain.media import asset as mod
from src.domain.timeline.duration import Duration
from tests.support import DomainTestCase


def audio(**overrides):
    payload = {
        "user_id": "u-1",
        "name": "episode-12.mp3",
        "size_bytes": 5_000_000,
        "duration": "30:00",
    }
    payload.update(overrides)
    return mod.Asset(**payload)


def image(**overrides):
    payload = {"user_id": "u-1", "name": "cover.png", "size_bytes": 400_000, "role": "artwork"}
    payload.update(overrides)
    return mod.Asset(**payload)


class ConstructionTests(DomainTestCase):
    def test_container_from_the_name(self):
        self.assertEqual("mp3", audio().container)

    def test_explicit_container_wins(self):
        self.assertEqual("wav", audio(name="clip.mp3", container="wav").container)

    def test_kind(self):
        self.assertEqual("audio", audio().kind)

    def test_default_role(self):
        self.assertEqual("main", audio().role)

    def test_unknown_role(self):
        error = self.assertRaisesCode("validation_failed", audio, role="sting")
        self.assertIn("intro", error.details["allowed"])

    def test_zero_size(self):
        self.assertField("size_bytes", audio, size_bytes=0)

    def test_empty_user(self):
        self.assertField("user_id", audio, user_id="")

    def test_checksum_length(self):
        self.assertField("checksum", audio, checksum="abc")

    def test_checksum_is_optional(self):
        self.assertIsNone(audio().checksum)

    def test_checksum_is_kept(self):
        self.assertEqual("a" * 64, audio(checksum="a" * 64).checksum)


class DurationTests(DomainTestCase):
    def test_audio_needs_a_duration(self):
        self.assertField("duration", mod.Asset, "u-1", "a.mp3", 100)

    def test_video_needs_a_duration(self):
        self.assertField("duration", mod.Asset, "u-1", "a.mp4", 100)

    def test_zero_duration_is_rejected(self):
        self.assertField("duration", audio, duration=0)

    def test_image_has_no_duration(self):
        self.assertIsNone(image().duration)

    def test_image_rejects_a_duration(self):
        self.assertField("duration", image, duration="01:00")

    def test_duration_is_parsed(self):
        self.assertEqual(Duration.of_minutes(30), audio().duration)

    def test_duration_accepts_millis(self):
        self.assertEqual(Duration(1500), audio(duration=1500).duration)


class KeyTests(DomainTestCase):
    def test_key_starts_with_the_owner(self):
        self.assertTrue(audio().key.startswith("u-1/"))

    def test_key_ends_with_the_extension(self):
        self.assertTrue(audio().key.endswith(".mp3"))

    def test_key_is_stable(self):
        self.assertEqual(audio().key, audio().key)

    def test_key_depends_on_the_name(self):
        self.assertNotEqual(audio().key, audio(name="other.mp3").key)

    def test_key_depends_on_the_size(self):
        self.assertNotEqual(audio().key, audio(size_bytes=6_000_000).key)

    def test_image_key_uses_the_mapped_extension(self):
        self.assertTrue(mod.Asset("u-1", "c.jpg", 100, role="artwork").key.endswith(".jpg"))


class PredicateTests(DomainTestCase):
    def test_is_audio(self):
        self.assertTrue(audio().is_audio())

    def test_is_not_video(self):
        self.assertFalse(audio().is_video())

    def test_is_image(self):
        self.assertTrue(image().is_image())

    def test_size_gigabytes_rounds_up(self):
        self.assertEqual(1, audio().size_gigabytes())

    def test_size_gigabytes_exact(self):
        self.assertEqual(2, audio(size_bytes=2 * mod.BYTES_PER_GIGABYTE).size_gigabytes())

    def test_bitrate(self):
        self.assertEqual(22222, audio().bitrate_bps())

    def test_image_has_no_bitrate(self):
        self.assertIsNone(image().bitrate_bps())


class MutationTests(DomainTestCase):
    def test_with_role(self):
        self.assertEqual("intro", audio().with_role("intro").role)

    def test_with_role_returns_a_copy(self):
        one = audio()
        one.with_role("intro")
        self.assertEqual("main", one.role)

    def test_with_role_keeps_the_key(self):
        one = audio()
        self.assertEqual(one.key, one.with_role("intro").key)


class SerialisationTests(DomainTestCase):
    def test_to_dict(self):
        payload = audio().to_dict()
        self.assertEqual("audio", payload["kind"])
        self.assertEqual(1_800_000, payload["duration_millis"])

    def test_to_dict_for_an_image(self):
        self.assertIsNone(image().to_dict()["duration_millis"])

    def test_round_trip(self):
        self.assertRoundTrips(mod.Asset.from_dict, audio(checksum="b" * 64))

    def test_round_trip_image(self):
        self.assertRoundTrips(mod.Asset.from_dict, image())

    def test_equality(self):
        self.assertEqual(audio(), audio())

    def test_hashable(self):
        self.assertEqual(1, len({audio(), audio()}))

    def test_repr(self):
        self.assertIn("episode-12.mp3", repr(audio()))


class CollectionTests(DomainTestCase):
    def setUp(self):
        self.main = audio()
        self.intro = audio(name="intro.mp3", size_bytes=100_000, duration="00:05", role="intro")
        self.cover = image()

    def test_total_bytes(self):
        self.assertEqual(5_500_000, mod.total_bytes([self.main, self.intro, self.cover]))

    def test_total_duration(self):
        total = mod.total_duration([self.main, self.intro, self.cover])
        self.assertEqual(1_805_000, total.millis)

    def test_total_duration_of_nothing(self):
        self.assertTrue(mod.total_duration([]).is_zero())

    def test_by_role(self):
        self.assertEqual((self.intro,), mod.by_role([self.main, self.intro], "intro"))

    def test_by_role_with_no_match(self):
        self.assertEqual((), mod.by_role([self.main], "outro"))

    def test_storage_used_rounds_up(self):
        self.assertEqual(1, mod.storage_used_gb([self.main, self.intro]))

    def test_storage_used_of_nothing(self):
        self.assertEqual(0, mod.storage_used_gb([]))
