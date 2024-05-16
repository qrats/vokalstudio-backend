from src.domain.streaming import rtmp as mod
from tests.support import DomainTestCase


class ConstructionTests(DomainTestCase):
    def test_fields(self):
        url = mod.IngestUrl("rtmp", "a.rtmp.youtube.com", "live2")
        self.assertEqual("rtmp", url.scheme)
        self.assertEqual(1935, url.port)

    def test_default_secure_port(self):
        self.assertEqual(443, mod.IngestUrl("rtmps", "a.b.test", "live").port)

    def test_explicit_port(self):
        self.assertEqual(1936, mod.IngestUrl("rtmp", "a.b.test", "live", 1936).port)

    def test_host_is_lowercased(self):
        self.assertEqual("a.b.test", mod.IngestUrl("rtmp", "A.B.TEST", "live").host)

    def test_path_is_stripped(self):
        self.assertEqual("live", mod.IngestUrl("rtmp", "a.b.test", "/live/").path)

    def test_unknown_scheme(self):
        self.assertField("scheme", mod.IngestUrl, "http", "a.b.test", "live")

    def test_host_without_a_dot(self):
        self.assertField("host", mod.IngestUrl, "rtmp", "localhost", "live")

    def test_host_with_bad_characters(self):
        self.assertField("host", mod.IngestUrl, "rtmp", "a_b.test", "live")

    def test_empty_path(self):
        self.assertField("path", mod.IngestUrl, "rtmp", "a.b.test", "/")

    def test_port_out_of_range(self):
        self.assertField("port", mod.IngestUrl, "rtmp", "a.b.test", "live", 70000)

    def test_port_must_be_an_integer(self):
        self.assertField("port", mod.IngestUrl, "rtmp", "a.b.test", "live", "1935")


class ParseTests(DomainTestCase):
    def test_simple(self):
        url = mod.IngestUrl.parse("rtmp://a.rtmp.youtube.com/live2")
        self.assertEqual("a.rtmp.youtube.com", url.host)
        self.assertEqual("live2", url.path)

    def test_with_a_port(self):
        self.assertEqual(1936, mod.IngestUrl.parse("rtmp://a.b.test:1936/live").port)

    def test_nested_path(self):
        self.assertEqual("a/b", mod.IngestUrl.parse("rtmp://a.b.test/a/b").path)

    def test_missing_scheme(self):
        self.assertField("url", mod.IngestUrl.parse, "a.b.test/live")

    def test_missing_path(self):
        self.assertField("url", mod.IngestUrl.parse, "rtmp://a.b.test")

    def test_bad_port(self):
        self.assertField("url", mod.IngestUrl.parse, "rtmp://a.b.test:live/live")

    def test_field_name(self):
        self.assertField("ingest", mod.IngestUrl.parse, "nonsense", "ingest")


class FormatTests(DomainTestCase):
    def test_default_port_is_omitted(self):
        url = mod.IngestUrl.parse("rtmp://a.b.test:1935/live")
        self.assertEqual("rtmp://a.b.test/live", url.to_string())

    def test_non_default_port_is_kept(self):
        url = mod.IngestUrl.parse("rtmp://a.b.test:1936/live")
        self.assertEqual("rtmp://a.b.test:1936/live", url.to_string())

    def test_round_trip(self):
        url = mod.IngestUrl.parse("rtmps://a.b.test/live/inner")
        self.assertEqual(url, mod.IngestUrl.parse(url.to_string()))

    def test_is_secure(self):
        self.assertTrue(mod.IngestUrl.parse("rtmps://a.b.test/live").is_secure)

    def test_uses_default_port(self):
        self.assertTrue(mod.IngestUrl.parse("rtmp://a.b.test/live").uses_default_port)

    def test_with_key(self):
        url = mod.IngestUrl.parse("rtmp://a.b.test/live")
        self.assertEqual("rtmp://a.b.test/live/abcd", url.with_key("abcd"))

    def test_with_key_validates(self):
        url = mod.IngestUrl.parse("rtmp://a.b.test/live")
        self.assertField("stream_key", url.with_key, "a b")

    def test_to_dict(self):
        payload = mod.IngestUrl.parse("rtmp://a.b.test/live").to_dict()
        self.assertEqual("a.b.test", payload["host"])
        self.assertEqual("rtmp://a.b.test/live", payload["url"])

    def test_equality(self):
        self.assertEqual(
            mod.IngestUrl.parse("rtmp://a.b.test/live"),
            mod.IngestUrl.parse("rtmp://a.b.test/live"),
        )

    def test_hashable(self):
        one = mod.IngestUrl.parse("rtmp://a.b.test/live")
        self.assertEqual(1, len({one, mod.IngestUrl.parse("rtmp://a.b.test/live")}))

    def test_repr(self):
        self.assertIn("rtmp://a.b.test/live", repr(mod.IngestUrl.parse("rtmp://a.b.test/live")))


class StreamKeyTests(DomainTestCase):
    def test_accepts_a_normal_key(self):
        self.assertEqual("abcd-efgh", mod.validate_stream_key("abcd-efgh"))

    def test_accepts_underscores(self):
        self.assertEqual("live_1", mod.validate_stream_key("live_1"))

    def test_rejects_spaces(self):
        self.assertField("stream_key", mod.validate_stream_key, "abcd efgh")

    def test_rejects_slashes(self):
        self.assertField("stream_key", mod.validate_stream_key, "abcd/efgh")

    def test_rejects_a_short_key(self):
        self.assertField("stream_key", mod.validate_stream_key, "abc")

    def test_minimum_is_configurable(self):
        self.assertField("stream_key", mod.validate_stream_key, "abcd", "stream_key", 8)

    def test_field_name(self):
        self.assertField("key", mod.validate_stream_key, "a b", "key")

    def test_masked_key_hides_the_body(self):
        self.assertEqual("****cdef", mod.masked_key("abababcdef"[:4] + "cdef"))

    def test_masked_key_keeps_four(self):
        self.assertTrue(mod.masked_key("abcdefghij").endswith("ghij"))


class SplitTests(DomainTestCase):
    def test_splits(self):
        url, key = mod.split_url_and_key("rtmp://a.b.test/live/abcd-efgh")
        self.assertEqual("rtmp://a.b.test/live", url.to_string())
        self.assertEqual("abcd-efgh", key)

    def test_nested_path(self):
        url, key = mod.split_url_and_key("rtmp://a.b.test/live/inner/abcd")
        self.assertEqual("live/inner", url.path)

    def test_no_key(self):
        self.assertField("url", mod.split_url_and_key, "rtmp://a.b.test/live/")

    def test_bad_key(self):
        self.assertField("url", mod.split_url_and_key, "rtmp://a.b.test/live/ab")

    def test_field_name(self):
        self.assertField("ingest", mod.split_url_and_key, "nope", "ingest")
