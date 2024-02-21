from src.domain.media import assembly as mod
from src.domain.media.asset import Asset
from src.domain.media.configuration import MediaConfiguration, Watermark
from tests.support import DomainTestCase


def audio(name="body.mp3", role="main", duration="30:00"):
    return Asset("u-1", name, 5_000_000, duration=duration, role=role)


def video(name="body.mp4", role="main"):
    return Asset("u-1", name, 50_000_000, duration="30:00", role=role)


INTRO = audio("intro.mp3", "intro", "00:05")
OUTRO = audio("outro.mp3", "outro", "00:10")
BODY = audio()


class SegmentTests(DomainTestCase):
    def test_end_millis(self):
        self.assertEqual(1500, mod.Segment("body", "k", 500, 1000).end_millis)

    def test_negative_start(self):
        self.assertField("start_millis", mod.Segment, "body", "k", -1, 10)

    def test_zero_duration(self):
        self.assertField("duration_millis", mod.Segment, "body", "k", 0, 0)

    def test_negative_fade(self):
        self.assertField("fade_in_millis", mod.Segment, "body", "k", 0, 10, -1)

    def test_to_dict(self):
        payload = mod.Segment("body", "k", 0, 10, 5).to_dict()
        self.assertEqual(10, payload["end_millis"])
        self.assertEqual(5, payload["fade_in_millis"])

    def test_equality(self):
        self.assertEqual(mod.Segment("a", "k", 0, 1), mod.Segment("a", "k", 0, 1))

    def test_hashable(self):
        self.assertEqual(
            1, len({mod.Segment("a", "k", 0, 1), mod.Segment("a", "k", 0, 1)})
        )

    def test_repr(self):
        self.assertIn("body", repr(mod.Segment("body", "k", 0, 1)))


class TimelineTests(DomainTestCase):
    def test_body_only(self):
        segments = mod.build_timeline(MediaConfiguration("u-1"), BODY)
        self.assertEqual(1, len(segments))
        self.assertEqual(0, segments[0].start_millis)

    def test_intro_then_body(self):
        config = MediaConfiguration("u-1", intro=INTRO)
        segments = mod.build_timeline(config, BODY)
        self.assertEqual(("intro", "body"), tuple(s.role for s in segments))
        self.assertEqual(5000, segments[1].start_millis)

    def test_body_then_outro(self):
        config = MediaConfiguration("u-1", outro=OUTRO)
        segments = mod.build_timeline(config, BODY)
        self.assertEqual(1_800_000, segments[1].start_millis)

    def test_all_three(self):
        config = MediaConfiguration("u-1", intro=INTRO, outro=OUTRO)
        segments = mod.build_timeline(config, BODY)
        self.assertEqual(("intro", "body", "outro"), tuple(s.role for s in segments))

    def test_fade_pulls_the_body_back(self):
        config = MediaConfiguration("u-1", intro=INTRO, fade_millis=1000)
        segments = mod.build_timeline(config, BODY)
        self.assertEqual(4000, segments[1].start_millis)

    def test_fade_pulls_the_outro_back(self):
        config = MediaConfiguration("u-1", outro=OUTRO, fade_millis=1000)
        segments = mod.build_timeline(config, BODY)
        self.assertEqual(1_799_000, segments[1].start_millis)

    def test_fade_cannot_swallow_the_intro(self):
        short = audio("short.mp3", "intro", "00:01")
        config = MediaConfiguration("u-1", intro=short, fade_millis=5000)
        segments = mod.build_timeline(config, BODY)
        self.assertEqual(1, segments[1].start_millis)

    def test_fade_override(self):
        config = MediaConfiguration("u-1", intro=INTRO, fade_millis=1000)
        segments = mod.build_timeline(config, BODY, fade_millis=0)
        self.assertEqual(5000, segments[1].start_millis)

    def test_body_carries_the_fade(self):
        config = MediaConfiguration("u-1", intro=INTRO, fade_millis=1000)
        self.assertEqual(1000, mod.build_timeline(config, BODY)[1].fade_in_millis)

    def test_first_segment_has_no_fade(self):
        segments = mod.build_timeline(MediaConfiguration("u-1"), BODY)
        self.assertEqual(0, segments[0].fade_in_millis)

    def test_image_body_is_rejected(self):
        cover = Asset("u-1", "cover.png", 400_000, role="artwork")
        self.assertField("body", mod.build_timeline, MediaConfiguration("u-1"), cover)

    def test_incompatible_configuration_is_rejected(self):
        config = MediaConfiguration("u-1", watermark=Watermark("u-1/logo.png"))
        self.assertField("body", mod.build_timeline, config, BODY)


class DurationTests(DomainTestCase):
    def test_body_only(self):
        segments = mod.build_timeline(MediaConfiguration("u-1"), BODY)
        self.assertEqual(1_800_000, mod.timeline_duration(segments).millis)

    def test_with_beds(self):
        config = MediaConfiguration("u-1", intro=INTRO, outro=OUTRO)
        segments = mod.build_timeline(config, BODY)
        self.assertEqual(1_815_000, mod.timeline_duration(segments).millis)

    def test_with_fades(self):
        config = MediaConfiguration("u-1", intro=INTRO, outro=OUTRO, fade_millis=1000)
        segments = mod.build_timeline(config, BODY)
        self.assertEqual(1_813_000, mod.timeline_duration(segments).millis)

    def test_empty_is_rejected(self):
        self.assertField("segments", mod.timeline_duration, [])


class OverlapTests(DomainTestCase):
    def test_no_fade_means_no_overlap(self):
        config = MediaConfiguration("u-1", intro=INTRO, outro=OUTRO)
        self.assertEqual((), mod.overlaps(mod.build_timeline(config, BODY)))

    def test_fades_overlap_on_purpose(self):
        config = MediaConfiguration("u-1", intro=INTRO, outro=OUTRO, fade_millis=1000)
        found = mod.overlaps(mod.build_timeline(config, BODY))
        self.assertEqual(((0, 1), (1, 2)), found)

    def test_single_segment(self):
        self.assertEqual((), mod.overlaps([mod.Segment("body", "k", 0, 10)]))


class RenderPlanTests(DomainTestCase):
    def test_segments_are_included(self):
        plan = mod.render_plan(MediaConfiguration("u-1"), BODY)
        self.assertEqual(1, len(plan["segments"]))

    def test_duration_is_included(self):
        plan = mod.render_plan(MediaConfiguration("u-1"), BODY)
        self.assertEqual(1_800_000, plan["duration_millis"])

    def test_no_loudness_without_a_measurement(self):
        self.assertIsNone(mod.render_plan(MediaConfiguration("u-1"), BODY)["loudness"])

    def test_loudness_is_planned(self):
        plan = mod.render_plan(MediaConfiguration("u-1"), BODY, -20.0, -8.0)
        self.assertEqual(4.0, plan["loudness"]["applied_gain_db"])

    def test_default_peak_is_used(self):
        plan = mod.render_plan(MediaConfiguration("u-1"), BODY, -20.0)
        self.assertEqual(2.0, plan["loudness"]["applied_gain_db"])

    def test_normalise_off_skips_loudness(self):
        config = MediaConfiguration("u-1", normalise=False)
        self.assertIsNone(mod.render_plan(config, BODY, -20.0)["loudness"])

    def test_watermark_reaches_a_video_plan(self):
        config = MediaConfiguration("u-1", watermark=Watermark("u-1/logo.png"))
        plan = mod.render_plan(config, video())
        self.assertEqual("u-1/logo.png", plan["watermark"]["asset_key"])

    def test_user_id_is_carried(self):
        self.assertEqual("u-1", mod.render_plan(MediaConfiguration("u-1"), BODY)["user_id"])
