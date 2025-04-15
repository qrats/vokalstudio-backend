from src.domain.episodes import shownotes as mod
from tests.support import DomainTestCase

BODY = "Hello **world**\n\nSee [the docs](https://x.test) for more."


class ConstructionTests(DomainTestCase):
    def test_body_is_trimmed(self):
        self.assertEqual("abc", mod.ShowNotes("  abc  ").body)

    def test_empty_is_allowed(self):
        self.assertTrue(mod.ShowNotes("").is_empty)

    def test_whitespace_only_is_empty(self):
        self.assertTrue(mod.ShowNotes("   ").is_empty)

    def test_non_empty(self):
        self.assertFalse(mod.ShowNotes(BODY).is_empty)

    def test_over_long_body(self):
        self.assertField("body", mod.ShowNotes, "x" * (mod.MAX_SUMMARY + 1))

    def test_non_string(self):
        self.assertField("body", mod.ShowNotes, None)


class RenderTests(DomainTestCase):
    def setUp(self):
        self.notes = mod.ShowNotes(BODY)

    def test_plain_text_drops_the_link_url(self):
        self.assertNotIn("https://x.test", self.notes.plain_text())

    def test_plain_text_keeps_the_label(self):
        self.assertIn("the docs", self.notes.plain_text())

    def test_summary_is_truncated(self):
        self.assertLessEqual(len(self.notes.summary(20)), 20)

    def test_summary_of_empty_notes(self):
        self.assertEqual("", mod.ShowNotes("").summary())

    def test_summary_length_must_be_positive(self):
        self.assertField("length", self.notes.summary, 0)

    def test_links(self):
        self.assertEqual(("https://x.test",), self.notes.links())

    def test_no_links(self):
        self.assertEqual((), mod.ShowNotes("plain").links())

    def test_word_count(self):
        self.assertEqual(7, self.notes.word_count())

    def test_word_count_of_empty(self):
        self.assertEqual(0, mod.ShowNotes("").word_count())

    def test_reading_time(self):
        self.assertGreater(self.notes.reading_time_seconds(), 0)

    def test_reading_time_of_empty(self):
        self.assertEqual(0, mod.ShowNotes("").reading_time_seconds())

    def test_paragraphs(self):
        self.assertEqual(2, len(self.notes.paragraphs()))

    def test_paragraphs_of_empty(self):
        self.assertEqual((), mod.ShowNotes("").paragraphs())

    def test_blank_paragraphs_are_dropped(self):
        self.assertEqual(1, len(mod.ShowNotes("a\n\n\n\n").paragraphs()))


class AppendTests(DomainTestCase):
    def test_appends(self):
        appended = mod.ShowNotes("first").with_appended("second")
        self.assertEqual(2, len(appended.paragraphs()))

    def test_appending_to_empty(self):
        self.assertEqual("second", mod.ShowNotes("").with_appended("second").body)

    def test_returns_a_copy(self):
        notes = mod.ShowNotes("first")
        notes.with_appended("second")
        self.assertEqual("first", notes.body)

    def test_rejects_empty_extra(self):
        self.assertField("extra", mod.ShowNotes("a").with_appended, "")


class SerialisationTests(DomainTestCase):
    def test_to_dict(self):
        payload = mod.ShowNotes(BODY).to_dict()
        self.assertEqual(["https://x.test"], payload["links"])
        self.assertEqual(7, payload["word_count"])

    def test_equality(self):
        self.assertEqual(mod.ShowNotes("a"), mod.ShowNotes("a"))

    def test_inequality(self):
        self.assertNotEqual(mod.ShowNotes("a"), mod.ShowNotes("b"))

    def test_hashable(self):
        self.assertEqual(1, len({mod.ShowNotes("a"), mod.ShowNotes("a")}))

    def test_repr(self):
        self.assertIn("1 words", repr(mod.ShowNotes("a")))


class RequireNotesTests(DomainTestCase):
    def test_none_becomes_empty(self):
        self.assertTrue(mod.require_notes(None).is_empty)

    def test_string_is_wrapped(self):
        self.assertEqual("a", mod.require_notes("a").body)

    def test_notes_pass_through(self):
        notes = mod.ShowNotes("a")
        self.assertIs(notes, mod.require_notes(notes))

    def test_other_types_are_rejected(self):
        self.assertField("show_notes", mod.require_notes, 1)

    def test_field_name(self):
        self.assertField("body", mod.require_notes, 1, "body")
