from src.domain.episodes import chapters as mod
from src.domain.timeline.duration import Duration
from tests.support import DomainTestCase


class ChapterTests(DomainTestCase):
    def test_fields(self):
        chapter = mod.Chapter(60000, "Interview")
        self.assertEqual(60000, chapter.start_millis)
        self.assertEqual("Interview", chapter.title)

    def test_start_is_a_duration(self):
        self.assertEqual(Duration(60000), mod.Chapter(60000, "x").start)

    def test_negative_start(self):
        self.assertField("start_millis", mod.Chapter, -1, "x")

    def test_empty_title(self):
        self.assertField("title", mod.Chapter, 0, "")

    def test_long_title(self):
        self.assertField("title", mod.Chapter, 0, "x" * 129)

    def test_optional_url(self):
        self.assertIsNone(mod.Chapter(0, "x").url)

    def test_url_is_kept(self):
        self.assertEqual("https://x.test", mod.Chapter(0, "x", "https://x.test").url)

    def test_image_key(self):
        self.assertEqual("k", mod.Chapter(0, "x", None, "k").image_key)

    def test_shifted(self):
        self.assertEqual(65000, mod.Chapter(60000, "x").shifted(5000).start_millis)

    def test_shifted_keeps_the_title(self):
        self.assertEqual("x", mod.Chapter(60000, "x").shifted(5000).title)

    def test_shifted_returns_a_copy(self):
        chapter = mod.Chapter(60000, "x")
        chapter.shifted(5000)
        self.assertEqual(60000, chapter.start_millis)

    def test_to_dict_uses_whole_seconds(self):
        self.assertEqual(60, mod.Chapter(60500, "x").to_dict()["startTime"])

    def test_ordering(self):
        self.assertLess(mod.Chapter(0, "a"), mod.Chapter(1, "b"))

    def test_equality(self):
        self.assertEqual(mod.Chapter(0, "a"), mod.Chapter(0, "a"))

    def test_hashable(self):
        self.assertEqual(1, len({mod.Chapter(0, "a"), mod.Chapter(0, "a")}))

    def test_repr(self):
        self.assertIn("Interview", repr(mod.Chapter(0, "Interview")))


class ValidateTests(DomainTestCase):
    def test_empty_is_allowed(self):
        self.assertEqual((), mod.validate_chapters([]))

    def test_sorted_output(self):
        markers = [mod.Chapter(60000, "b"), mod.Chapter(0, "a")]
        self.assertEqual("a", mod.validate_chapters(markers)[0].title)

    def test_first_must_start_at_zero(self):
        self.assertField("chapters", mod.validate_chapters, [mod.Chapter(1000, "a")])

    def test_duplicate_start_times(self):
        markers = [mod.Chapter(0, "a"), mod.Chapter(0, "b")]
        self.assertField("chapters", mod.validate_chapters, markers)

    def test_past_the_end(self):
        markers = [mod.Chapter(0, "a"), mod.Chapter(2000, "b")]
        self.assertField("chapters", mod.validate_chapters, markers, 2000)

    def test_just_inside_the_end(self):
        markers = [mod.Chapter(0, "a"), mod.Chapter(1999, "b")]
        self.assertEqual(2, len(mod.validate_chapters(markers, 2000)))

    def test_no_duration_skips_the_end_check(self):
        markers = [mod.Chapter(0, "a"), mod.Chapter(10 ** 9, "b")]
        self.assertEqual(2, len(mod.validate_chapters(markers)))


class LengthTests(DomainTestCase):
    def test_two_chapters(self):
        markers = [mod.Chapter(0, "a"), mod.Chapter(60000, "b")]
        lengths = mod.chapter_lengths(markers, 1_800_000)
        self.assertEqual(Duration(60000), lengths[0])
        self.assertEqual(Duration(1_740_000), lengths[1])

    def test_one_chapter_runs_the_whole_episode(self):
        lengths = mod.chapter_lengths([mod.Chapter(0, "a")], 1_800_000)
        self.assertEqual(Duration(1_800_000), lengths[0])

    def test_no_chapters(self):
        self.assertEqual((), mod.chapter_lengths([], 1000))

    def test_lengths_add_up(self):
        markers = [mod.Chapter(0, "a"), mod.Chapter(1000, "b"), mod.Chapter(5000, "c")]
        lengths = mod.chapter_lengths(markers, 9000)
        self.assertEqual(9000, sum(length.millis for length in lengths))

    def test_invalid_markers_are_rejected(self):
        self.assertField("chapters", mod.chapter_lengths, [mod.Chapter(1, "a")], 9000)


class LookupTests(DomainTestCase):
    def setUp(self):
        self.markers = [mod.Chapter(0, "a"), mod.Chapter(60000, "b")]

    def test_inside_the_first(self):
        self.assertEqual("a", mod.chapter_at(self.markers, 100).title)

    def test_on_a_boundary(self):
        self.assertEqual("b", mod.chapter_at(self.markers, 60000).title)

    def test_after_the_last(self):
        self.assertEqual("b", mod.chapter_at(self.markers, 10 ** 6).title)

    def test_no_chapters(self):
        self.assertIsNone(mod.chapter_at([], 0))

    def test_before_the_first(self):
        self.assertIsNone(mod.chapter_at([mod.Chapter(500, "a")], 100))


class ShiftTests(DomainTestCase):
    def test_shifts_everything(self):
        markers = [mod.Chapter(0, "a"), mod.Chapter(60000, "b")]
        shifted = mod.shift_all(markers, 5000)
        self.assertEqual((5000, 65000), tuple(c.start_millis for c in shifted))

    def test_returns_sorted(self):
        markers = [mod.Chapter(60000, "b"), mod.Chapter(0, "a")]
        self.assertEqual("a", mod.shift_all(markers, 1000)[0].title)

    def test_empty(self):
        self.assertEqual((), mod.shift_all([], 1000))
