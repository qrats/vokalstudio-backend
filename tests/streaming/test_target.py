from src.domain.streaming.rtmp import IngestUrl
from src.domain.streaming import target as mod
from tests.support import DomainTestCase

KEY = "abcdefghijklmnopqrstuvwx"


def build(**overrides):
    payload = {"user_id": "u-1", "platform": "youtube", "stream_key": KEY}
    payload.update(overrides)
    return mod.StreamTarget(**payload)


def custom(**overrides):
    payload = {
        "user_id": "u-1",
        "platform": "custom",
        "stream_key": "abcdefgh",
        "ingest": "rtmp://my.host.test/live",
    }
    payload.update(overrides)
    return mod.StreamTarget(**payload)


class ConstructionTests(DomainTestCase):
    def test_default_ingest_is_used(self):
        self.assertEqual("a.rtmp.youtube.com", build().ingest.host)

    def test_enabled_by_default(self):
        self.assertTrue(build().enabled)

    def test_custom_needs_an_ingest(self):
        self.assertField(
            "ingest", mod.StreamTarget, "u-1", "custom", "abcdefgh"
        )

    def test_custom_accepts_an_ingest_object(self):
        url = IngestUrl.parse("rtmp://my.host.test/live")
        self.assertEqual(url, custom(ingest=url).ingest)

    def test_secure_platform_rejects_plain_rtmp(self):
        self.assertField(
            "ingest",
            mod.StreamTarget,
            "u-1",
            "facebook",
            KEY,
            "rtmp://live-api-s.facebook.com/rtmp",
        )

    def test_secure_platform_accepts_rtmps(self):
        target = mod.StreamTarget("u-1", "facebook", KEY)
        self.assertTrue(target.ingest.is_secure)

    def test_short_key_for_a_strict_platform(self):
        self.assertField("stream_key", build, stream_key="abcd")

    def test_short_key_is_fine_for_custom(self):
        self.assertEqual("abcdefgh", custom().stream_key)

    def test_unknown_platform(self):
        self.assertField("platform", build, platform="vimeo")

    def test_label(self):
        self.assertEqual("Main channel", build(label="Main channel").label)

    def test_label_is_optional(self):
        self.assertIsNone(build().label)


class BehaviourTests(DomainTestCase):
    def test_reference_is_stable(self):
        self.assertEqual(build().reference, build().reference)

    def test_reference_depends_on_the_ingest(self):
        self.assertNotEqual(build().reference, custom().reference)

    def test_reference_ignores_the_key(self):
        self.assertEqual(build().reference, build(stream_key="z" * 24).reference)

    def test_max_kbps_comes_from_the_platform(self):
        self.assertEqual(51000, build().max_kbps)

    def test_is_custom(self):
        self.assertTrue(custom().is_custom())
        self.assertFalse(build().is_custom())

    def test_publish_url_carries_the_key(self):
        self.assertTrue(build().publish_url().endswith("/" + KEY))

    def test_accepts_within_the_cap(self):
        self.assertTrue(build().accepts(9000))

    def test_rejects_above_the_cap(self):
        self.assertFalse(mod.StreamTarget("u-1", "facebook", KEY).accepts(9000))

    def test_accepts_exactly_the_cap(self):
        self.assertTrue(mod.StreamTarget("u-1", "twitch", KEY).accepts(6000))

    def test_enabled_copy(self):
        self.assertFalse(build().enabled_copy(False).enabled)

    def test_enabled_copy_does_not_mutate(self):
        target = build()
        target.enabled_copy(False)
        self.assertTrue(target.enabled)

    def test_enabled_copy_keeps_the_label(self):
        self.assertEqual("Main", build(label="Main").enabled_copy(False).label)


class SerialisationTests(DomainTestCase):
    def test_key_is_masked_by_default(self):
        self.assertNotEqual(KEY, build().to_dict()["stream_key"])

    def test_masked_key_keeps_the_tail(self):
        self.assertTrue(build().to_dict()["stream_key"].endswith(KEY[-4:]))

    def test_key_can_be_revealed(self):
        self.assertEqual(KEY, build().to_dict(True)["stream_key"])

    def test_ingest_is_a_string(self):
        self.assertEqual("rtmp://a.rtmp.youtube.com/live2", build().to_dict()["ingest"])

    def test_max_kbps_is_included(self):
        self.assertEqual(51000, build().to_dict()["max_kbps"])

    def test_equality(self):
        self.assertEqual(build(), build())

    def test_key_matters_for_equality(self):
        self.assertNotEqual(build(), build(stream_key="z" * 24))

    def test_hashable(self):
        self.assertEqual(1, len({build(), build()}))

    def test_repr(self):
        self.assertIn("youtube", repr(build()))

    def test_repr_shows_the_switch(self):
        self.assertIn("off", repr(build().enabled_copy(False)))


class CollectionTests(DomainTestCase):
    def setUp(self):
        self.on = build()
        self.off = mod.StreamTarget("u-1", "twitch", KEY, enabled=False)
        self.custom = custom()

    def test_enabled_targets(self):
        found = mod.enabled_targets([self.on, self.off, self.custom])
        self.assertEqual((self.on, self.custom), found)

    def test_by_platform(self):
        self.assertEqual((self.on,), mod.by_platform([self.on, self.off], "youtube"))

    def test_by_platform_normalises(self):
        self.assertEqual((self.on,), mod.by_platform([self.on], "YouTube"))

    def test_custom_targets(self):
        self.assertEqual((self.custom,), mod.custom_targets([self.on, self.custom]))

    def test_no_duplicates(self):
        self.assertEqual((), mod.duplicate_references([self.on, self.custom]))

    def test_duplicate_references(self):
        found = mod.duplicate_references([self.on, build(stream_key="z" * 24)])
        self.assertEqual((self.on.reference,), found)
