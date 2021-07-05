from src.domain.core import text
from tests.support import DomainTestCase


class SlugifyTests(DomainTestCase):
    def test_lowercases_and_hyphenates(self):
        self.assertEqual("hello-world", text.slugify("Hello World"))

    def test_collapses_punctuation(self):
        self.assertEqual("a-b", text.slugify("a -- ///  b"))

    def test_strips_leading_and_trailing_separators(self):
        self.assertEqual("abc", text.slugify("!!abc!!"))

    def test_folds_accents(self):
        self.assertEqual("uber-cafe", text.slugify("Über Café"))

    def test_transliterates_eszett(self):
        self.assertEqual("strasse", text.slugify("Straße"))

    def test_transliterates_slashed_o(self):
        self.assertEqual("bodo", text.slugify("Bødø"))

    def test_max_length_trims_cleanly(self):
        self.assertEqual("one-two", text.slugify("one two three", max_length=8))

    def test_max_length_none_keeps_everything(self):
        self.assertEqual(60, len(text.slugify("a" * 60, max_length=None)))

    def test_empty_result_is_rejected(self):
        self.assertField("slug", text.slugify, "###")

    def test_non_string_is_rejected(self):
        self.assertField("slug", text.slugify, None)

    def test_field_name_is_used(self):
        self.assertField("title", text.slugify, "###", 80, "title")


class SlugPredicateTests(DomainTestCase):
    def test_canonical_slug(self):
        self.assertTrue(text.is_slug("live-from-berlin"))

    def test_uppercase_is_not_a_slug(self):
        self.assertFalse(text.is_slug("Live"))

    def test_empty_is_not_a_slug(self):
        self.assertFalse(text.is_slug(""))

    def test_safe_returns_default(self):
        self.assertEqual("fallback", text.slugify_safe("###", "fallback"))

    def test_safe_returns_slug(self):
        self.assertEqual("ok", text.slugify_safe("OK"))


class WhitespaceTests(DomainTestCase):
    def test_collapses_runs(self):
        self.assertEqual("a b", text.normalize_whitespace("a \n\t  b"))

    def test_trims(self):
        self.assertEqual("a", text.normalize_whitespace("  a  "))

    def test_rejects_non_string(self):
        self.assertRaisesCode("validation_failed", text.normalize_whitespace, 1)


class StripMarkupTests(DomainTestCase):
    def test_removes_tags(self):
        self.assertEqual("bold text", text.strip_markup("<b>bold</b> text"))

    def test_keeps_link_label(self):
        self.assertEqual("docs", text.strip_markup("[docs](https://x.test)"))

    def test_mixed_markup(self):
        self.assertEqual(
            "read the docs now",
            text.strip_markup("<p>read the [docs](http://x) now</p>"),
        )

    def test_rejects_non_string(self):
        self.assertRaisesCode("validation_failed", text.strip_markup, None)


class TruncateTests(DomainTestCase):
    def test_short_text_is_untouched(self):
        self.assertEqual("abc", text.truncate("abc", 10))

    def test_breaks_on_word_boundary(self):
        self.assertEqual("one two…", text.truncate("one two three", 9))

    def test_exact_length_is_untouched(self):
        self.assertEqual("abcde", text.truncate("abcde", 5))

    def test_suffix_is_counted(self):
        self.assertLessEqual(len(text.truncate("one two three", 8)), 8)

    def test_custom_suffix(self):
        self.assertTrue(text.truncate("one two three", 10, "...").endswith("..."))

    def test_limit_smaller_than_suffix(self):
        self.assertEqual("..", text.truncate("one two", 2, "..."))

    def test_zero_limit_is_rejected(self):
        self.assertField("limit", text.truncate, "abc", 0)

    def test_no_space_falls_back_to_hard_cut(self):
        self.assertEqual("aaaa…", text.truncate("aaaaaaaa", 5))


class WordCountTests(DomainTestCase):
    def test_counts_words(self):
        self.assertEqual(3, text.word_count("one two three"))

    def test_ignores_markup(self):
        self.assertEqual(2, text.word_count("<b>one</b> two"))

    def test_empty_is_zero(self):
        self.assertEqual(0, text.word_count("   "))


class ReadingTimeTests(DomainTestCase):
    def test_empty_is_zero(self):
        self.assertEqual(0, text.reading_time_seconds(""))

    def test_rounds_up(self):
        self.assertEqual(1, text.reading_time_seconds("one"))

    def test_uses_words_per_minute(self):
        body = " ".join(["word"] * 60)
        self.assertEqual(60, text.reading_time_seconds(body, words_per_minute=60))

    def test_zero_rate_is_rejected(self):
        self.assertField(
            "words_per_minute", text.reading_time_seconds, "a", 0
        )


class ExtractLinksTests(DomainTestCase):
    def test_returns_urls_in_order(self):
        body = "[a](https://a.test) then [b](https://b.test)"
        self.assertEqual(("https://a.test", "https://b.test"), text.extract_links(body))

    def test_deduplicates(self):
        body = "[a](https://a.test) [again](https://a.test)"
        self.assertEqual(("https://a.test",), text.extract_links(body))

    def test_no_links(self):
        self.assertEqual((), text.extract_links("plain"))

    def test_none_is_tolerated(self):
        self.assertEqual((), text.extract_links(None))


class InitialsTests(DomainTestCase):
    def test_two_initials(self):
        self.assertEqual("AB", text.initials("anna bell"))

    def test_size_is_respected(self):
        self.assertEqual("ABC", text.initials("anna bell carr", size=3))

    def test_empty_name(self):
        self.assertEqual("", text.initials(""))

    def test_none(self):
        self.assertEqual("", text.initials(None))


class MaskTests(DomainTestCase):
    def test_keeps_tail(self):
        self.assertEqual("*****cdef", text.mask("abcdefghij"[:5] + "cdef"))

    def test_short_value_is_fully_masked(self):
        self.assertEqual("***", text.mask("abc", keep=4))

    def test_keep_zero(self):
        self.assertEqual("****", text.mask("abcd", keep=0))

    def test_custom_char(self):
        self.assertEqual("##cd", text.mask("abcd", keep=2, char="#"))

    def test_negative_keep_is_rejected(self):
        self.assertField("keep", text.mask, "abcd", -1)

    def test_non_string_is_rejected(self):
        self.assertField("value", text.mask, None)
