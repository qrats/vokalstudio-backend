from src.domain.content import markup as mod
from tests.support import DomainTestCase

BODY = "\n".join(
    [
        "# Title",
        "",
        "Intro paragraph.",
        "It continues here.",
        "",
        "## Section",
        "",
        "- one",
        "- two",
        "",
        "> a quote",
        "",
        "```python",
        "print(1)",
        "```",
    ]
)


class HeadingLevelTests(DomainTestCase):
    def test_one_hash(self):
        self.assertEqual(1, mod.heading_level("# Title"))

    def test_three_hashes(self):
        self.assertEqual(3, mod.heading_level("### Deep"))

    def test_capped_at_six(self):
        self.assertEqual(6, mod.heading_level("######## Very deep"))

    def test_leading_space_is_tolerated(self):
        self.assertEqual(1, mod.heading_level("  # Title"))

    def test_not_a_heading(self):
        self.assertField("line", mod.heading_level, "Title")


class ParseTests(DomainTestCase):
    def setUp(self):
        self.blocks = mod.parse_blocks(BODY)

    def test_block_order(self):
        self.assertEqual(
            ["heading", "paragraph", "heading", "list", "quote", "code"],
            [block["kind"] for block in self.blocks],
        )

    def test_heading_text(self):
        self.assertEqual("Title", self.blocks[0]["text"])

    def test_heading_level(self):
        self.assertEqual(2, self.blocks[2]["level"])

    def test_paragraph_lines_are_joined(self):
        self.assertEqual("Intro paragraph. It continues here.", self.blocks[1]["text"])

    def test_list_items(self):
        self.assertEqual(["one", "two"], self.blocks[3]["items"])

    def test_quote_marker_is_removed(self):
        self.assertEqual("a quote", self.blocks[4]["text"])

    def test_code_body_is_preserved(self):
        self.assertEqual("print(1)", self.blocks[5]["text"])

    def test_code_language(self):
        self.assertEqual("python", self.blocks[5]["language"])

    def test_code_without_a_language(self):
        blocks = mod.parse_blocks("```\nplain\n```")
        self.assertIsNone(blocks[0]["language"])

    def test_star_bullets(self):
        blocks = mod.parse_blocks("* one\n* two")
        self.assertEqual(["one", "two"], blocks[0]["items"])

    def test_empty_body(self):
        self.assertEqual((), mod.parse_blocks(""))

    def test_blank_lines_are_ignored(self):
        self.assertEqual(1, len(mod.parse_blocks("\n\n\nhello\n\n\n")))

    def test_unterminated_fence(self):
        blocks = mod.parse_blocks("```\nstill open")
        self.assertEqual("still open", blocks[0]["text"])

    def test_every_kind_is_known(self):
        for block in self.blocks:
            self.assertIn(block["kind"], mod.BLOCK_KINDS)


class HeadingTests(DomainTestCase):
    def test_headings(self):
        self.assertEqual(((1, "Title"), (2, "Section")), mod.headings(BODY))

    def test_no_headings(self):
        self.assertEqual((), mod.headings("just a paragraph"))

    def test_table_of_contents_skips_the_title(self):
        entries = mod.table_of_contents(BODY)
        self.assertEqual(1, len(entries))
        self.assertEqual("section", entries[0]["anchor"])

    def test_table_of_contents_of_a_flat_document(self):
        self.assertEqual((), mod.table_of_contents("# Only a title"))

    def test_unanchorable_heading_is_skipped(self):
        self.assertEqual((), mod.table_of_contents("## ###"))


class ExcerptTests(DomainTestCase):
    def test_first_paragraph(self):
        self.assertTrue(mod.excerpt(BODY).startswith("Intro paragraph."))

    def test_truncated(self):
        self.assertLessEqual(len(mod.excerpt(BODY, 20)), 20)

    def test_no_paragraph(self):
        self.assertEqual("", mod.excerpt("# Title"))

    def test_html_is_stripped(self):
        self.assertEqual("bold text", mod.excerpt("<b>bold</b> text"))

    def test_link_text_is_kept(self):
        self.assertEqual("docs", mod.excerpt("[docs](https://x.test)"))


class CodeLanguageTests(DomainTestCase):
    def test_languages(self):
        self.assertEqual(("python",), mod.code_languages(BODY))

    def test_sorted_and_unique(self):
        body = "```js\na\n```\n\n```bash\nb\n```\n\n```js\nc\n```"
        self.assertEqual(("bash", "js"), mod.code_languages(body))

    def test_no_code(self):
        self.assertEqual((), mod.code_languages("plain"))

    def test_unlabelled_fences_are_ignored(self):
        self.assertEqual((), mod.code_languages("```\nplain\n```"))
