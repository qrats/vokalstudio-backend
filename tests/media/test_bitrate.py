from src.domain.media import bitrate as mod
from tests.support import DomainTestCase


class RenditionTests(DomainTestCase):
    def test_named(self):
        rung = mod.Rendition.named("720p")
        self.assertEqual(720, rung.height)
        self.assertEqual(2800, rung.video_kbps)

    def test_named_is_case_insensitive(self):
        self.assertEqual(720, mod.Rendition.named("720P").height)

    def test_unknown_name(self):
        error = self.assertRaisesCode("validation_failed", mod.Rendition.named, "4k")
        self.assertIn("720p", error.details["allowed"])

    def test_total_kbps(self):
        self.assertEqual(2928, mod.Rendition.named("720p").total_kbps)

    def test_overhead_rounds_up(self):
        self.assertEqual(3280, mod.Rendition.named("720p").with_overhead(12))

    def test_zero_overhead(self):
        self.assertEqual(2928, mod.Rendition.named("720p").with_overhead(0))

    def test_overhead_ceiling(self):
        self.assertField("percent", mod.Rendition.named("720p").with_overhead, 101)

    def test_height_floor(self):
        self.assertField("height", mod.Rendition, "tiny", 100, 400, 64)

    def test_video_bitrate_floor(self):
        self.assertField("video_kbps", mod.Rendition, "x", 240, 10, 64)

    def test_audio_bitrate_floor(self):
        self.assertField("audio_kbps", mod.Rendition, "x", 240, 400, 8)

    def test_to_dict(self):
        payload = mod.Rendition.named("360p").to_dict()
        self.assertEqual("360p", payload["name"])
        self.assertEqual(896, payload["total_kbps"])

    def test_ordering_is_by_height(self):
        self.assertLess(mod.Rendition.named("360p"), mod.Rendition.named("720p"))

    def test_equality(self):
        self.assertEqual(mod.Rendition.named("720p"), mod.Rendition.named("720p"))

    def test_hashable(self):
        self.assertEqual(
            1, len({mod.Rendition.named("720p"), mod.Rendition.named("720p")})
        )

    def test_repr(self):
        self.assertIn("720p", repr(mod.Rendition.named("720p")))

    def test_ladder_entries_are_ordered(self):
        heights = [rung["height"] for rung in mod.LADDER]
        self.assertEqual(sorted(heights), heights)


class RungsTests(DomainTestCase):
    def test_largest_first(self):
        rungs = mod.rungs_up_to(1080)
        self.assertEqual("1080p", rungs[0].name)

    def test_excludes_taller_rungs(self):
        names = [rung.name for rung in mod.rungs_up_to(720)]
        self.assertNotIn("1080p", names)

    def test_includes_the_exact_height(self):
        self.assertIn("720p", [rung.name for rung in mod.rungs_up_to(720)])

    def test_between_rungs(self):
        self.assertEqual("480p", mod.rungs_up_to(700)[0].name)

    def test_below_every_rung(self):
        self.assertEqual((), mod.rungs_up_to(100))

    def test_zero_height_is_rejected(self):
        self.assertField("source_height", mod.rungs_up_to, 0)


class LadderTests(DomainTestCase):
    def test_generous_upstream_takes_the_top_rungs(self):
        names = [rung.name for rung in mod.build_ladder(1080, 20000)]
        self.assertEqual(["1080p", "720p", "480p", "360p"], names)

    def test_max_rungs_is_respected(self):
        self.assertEqual(2, len(mod.build_ladder(1080, 20000, max_rungs=2)))

    def test_tight_upstream_skips_what_will_not_fit(self):
        names = [rung.name for rung in mod.build_ladder(1080, 6000)]
        self.assertEqual(["1080p"], names)

    def test_it_keeps_filling_with_smaller_rungs(self):
        names = [rung.name for rung in mod.build_ladder(720, 4500)]
        self.assertEqual(["720p", "360p"], names)

    def test_nothing_fits(self):
        self.assertEqual((), mod.build_ladder(1080, 100))

    def test_ladder_stays_inside_the_budget(self):
        rungs = mod.build_ladder(2160, 12000)
        self.assertLessEqual(mod.ladder_cost(rungs), 12000)

    def test_zero_upstream_is_rejected(self):
        self.assertField("upstream_kbps", mod.build_ladder, 1080, 0)

    def test_max_rungs_floor(self):
        self.assertField("max_rungs", mod.build_ladder, 1080, 9000, 0)


class CostTests(DomainTestCase):
    def test_cost_of_nothing(self):
        self.assertEqual(0, mod.ladder_cost([]))

    def test_cost_sums_the_rungs(self):
        rungs = [mod.Rendition.named("360p"), mod.Rendition.named("240p")]
        self.assertEqual(1004 + 520, mod.ladder_cost(rungs))

    def test_fits(self):
        self.assertTrue(mod.fits([mod.Rendition.named("240p")], 1000))

    def test_does_not_fit(self):
        self.assertFalse(mod.fits([mod.Rendition.named("1080p")], 1000))

    def test_fits_exactly(self):
        rung = mod.Rendition.named("240p")
        self.assertTrue(mod.fits([rung], rung.with_overhead()))


class BestSingleTests(DomainTestCase):
    def test_picks_the_highest_that_fits(self):
        self.assertEqual("480p", mod.best_single(1080, 2000).name)

    def test_full_budget(self):
        self.assertEqual("1080p", mod.best_single(1080, 20000).name)

    def test_nothing_fits(self):
        self.assertIsNone(mod.best_single(1080, 100))

    def test_capped_by_the_source(self):
        self.assertEqual("360p", mod.best_single(360, 20000).name)
