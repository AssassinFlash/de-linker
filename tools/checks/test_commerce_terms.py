"""The commerce vocabulary gate: wordlist, prose extraction, and the ratchet.

Each test pins one decision the checker makes, because a gate that quietly
over- or under-matches is worse than no gate: over-matching buries the real
findings, under-matching lets shop copy ship.
"""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

CHECKS = Path(__file__).resolve().parent
sys.path.insert(0, str(CHECKS))

_spec = importlib.util.spec_from_file_location(
    "commerce_terms", CHECKS / "commerce-terms.py"
)
assert _spec is not None and _spec.loader is not None
commerce = importlib.util.module_from_spec(_spec)
sys.modules["commerce_terms"] = commerce
_spec.loader.exec_module(commerce)


def patterns(terms=None):
    return [(term, commerce.term_pattern(term)) for term in terms or commerce.load_terms()]


class WordlistTests(unittest.TestCase):
    def test_the_shipped_list_carries_both_documents_words(self):
        """docs/specs/11-commerce.md and AGENTS.md §3 are the sources."""
        terms = set(commerce.load_terms())
        for term in (
            "order*",
            "checkout*",
            "payment*",
            "shipping*",
            "Versand*",
            "Kasse*",
            "Bezahl*",
            "Warenkorb*",
            "catalogue*",
            "article",
            "articles",
            "basket*",
            "cart",
            "Bestell*",
            "Zahlung*",
        ):
            self.assertIn(term, terms)

    def test_an_empty_or_missing_list_fails_loudly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "words.txt"
            path.write_text("# only a comment\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                commerce.load_terms(path)
            with self.assertRaises(RuntimeError):
                commerce.load_terms(Path(directory) / "absent.txt")

    def test_the_logistics_words_past_the_spec_list_are_named(self):
        """AGENTS.md §1 bans 发货 and 采购, not only 运费.

        The first version of the list carried the spec's own words and missed
        "dispatch", so the German home said "Lagerversand" while its English
        twin said "warehouse dispatch" and only the German was caught. These
        two are the words that gap proved necessary; dropping either from the
        list must fail here, not on a live page.
        """
        terms = set(commerce.load_terms())
        self.assertIn("dispatch*", terms)
        self.assertIn("purchase*", terms)
        # The German side of the same class: Versand* already covers
        # "Lagerversand" and "versandt".
        self.assertIn("Versand*", terms)
        self.assertEqual(
            commerce.matched_terms("Stock dispatch from Germany", patterns()), ["dispatch*"]
        )
        self.assertEqual(commerce.matched_terms("Lagerversand", patterns()), ["Versand*"])


class MatchingTests(unittest.TestCase):
    def test_whole_word_boundaries_hold(self):
        self.assertEqual(commerce.matched_terms("Sort the rows", patterns()), [])
        # "order" inside a longer word is not the commerce noun.
        self.assertEqual(commerce.matched_terms("Reordering is not a word here", patterns()), [])
        self.assertEqual(commerce.matched_terms("backorder", patterns()), [])

    def test_prefix_terms_carry_inflections(self):
        self.assertEqual(commerce.matched_terms("Your orders ship", patterns()), ["order*"])
        self.assertEqual(commerce.matched_terms("Bestellungen", patterns()), ["Bestell*"])
        self.assertEqual(commerce.matched_terms("Versandkosten", patterns()), ["Versand*"])
        self.assertEqual(commerce.matched_terms("Zahlungsbedingungen", patterns()), ["Zahlung*"])

    def test_german_compounds_match_with_the_word_last(self):
        """German closes its compounds, so the head is the last element.

        The list carried "Versand*" from its first version and still missed
        "Lagerversand", which the German home page says three times: the
        leading word boundary only allowed the word at the start of a word.
        """
        cases = {
            "Lagerversand": ["Versand*"],
            "Paketversand": ["Versand*"],
            "Expressversand": ["Versand*"],
            "Nachbestellung": ["Bestell*"],
            "Kundenbestellung": ["Bestell*"],
            "Teilzahlung": ["Zahlung*"],
            "Vorauszahlung": ["Zahlung*"],
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(commerce.matched_terms(text, patterns()), expected)

    def test_the_compound_rule_does_not_reach_unrelated_words(self):
        """Only the four heads are loosened; "Kasse*" keeps its start anchor."""
        for text in ("Sort the rows", "Zurück", "Bestand", "Kassierer"):
            with self.subTest(text=text):
                self.assertEqual(commerce.matched_terms(text, patterns()), [])

    def test_kasse_prefix_is_recorded_as_a_latent_false_positive(self):
        """`Kasse*` also matches "Kassette" and "Kasserolle".

        Recorded rather than fixed: loosening the term would start missing
        "Kassenbuch" and "Kassensystem", and neither spelling occurs in the
        tree or on the live pages. A future string that uses one of them
        reaches the baseline path, where a human reads the reason.
        """
        self.assertEqual(commerce.matched_terms("Kassette", patterns()), ["Kasse*"])

    def test_case_is_ignored(self):
        self.assertEqual(commerce.matched_terms("CHECKOUT", patterns()), ["checkout*"])
        self.assertEqual(commerce.matched_terms("Warenkorb", patterns()), ["Warenkorb*"])

    def test_namespaced_technical_keys_do_not_match(self):
        """A merge field renders as data, so the customer reads no word."""
        self.assertEqual(
            commerce.matched_terms("Your inquiry #{order_number} has arrived", patterns()), []
        )
        self.assertEqual(commerce.matched_terms("Inquiry {order_id}", patterns()), [])

    def test_statute_citation_is_not_the_blog_word(self):
        self.assertEqual(
            commerce.matched_terms("not a device rating or Article 3 installed power", patterns()),
            [],
        )
        self.assertEqual(commerce.matched_terms("Read article", patterns()), ["article"])


class FragmentProseTests(unittest.TestCase):
    def test_configuration_attributes_are_not_copy(self):
        html = (
            '<div class="woocommerce-cart-form">'
            '[lc_get_cats title_li="Topics" taxonomy="category" orderby="name" order="ASC"]'
            '</div>'
        )
        parser = commerce.CopyStrings()
        parser.feed(html)
        values = " ".join(value for value, _line in parser.strings)
        self.assertNotIn("order", values.replace("Topics", ""))

    def test_shortcode_labels_are_copy(self):
        html = '[linker_products_sort label="Order the range by name"]'
        parser = commerce.CopyStrings()
        parser.feed(html)
        values = " ".join(value for value, _line in parser.strings)
        self.assertIn("Order the range by name", values)

    def test_script_bodies_are_not_copy(self):
        html = '<script>var base = "tv-article-section-" + index;</script><p>Real copy</p>'
        parser = commerce.CopyStrings()
        parser.feed(html)
        values = " ".join(value for value, _line in parser.strings)
        self.assertNotIn("article", values)
        self.assertIn("Real copy", values)

    def test_accessible_labels_are_copy(self):
        html = '<button aria-label="Open the cart">x</button>'
        parser = commerce.CopyStrings()
        parser.feed(html)
        self.assertIn("Open the cart", [value for value, _line in parser.strings])


class CatalogTests(unittest.TestCase):
    def test_msgids_and_every_plural_msgstr_reach_the_gate(self):
        catalog = (
            'msgid ""\nmsgstr "header"\n\n'
            '#: x.php:1\nmsgid "Open the basket"\nmsgstr "Warenkorb öffnen"\n\n'
            '#: y.php:2\nmsgid "%d item"\nmsgid_plural "%d items"\n'
            'msgstr[0] "%d Artikel im Warenkorb"\nmsgstr[1] "%d Artikel im Warenkorb"\n\n'
            '#~ msgid "Obsolete checkout"\n#~ msgstr "Alte Kasse"\n'
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.po"
            path.write_text(catalog, encoding="utf-8")
            messages = commerce.po_messages(path)
        msgids = " ".join(msgid for msgid, _msgstr, _line in messages)
        msgstrs = " ".join(msgstr for _msgid, msgstr, _line in messages)
        self.assertIn("Open the basket", msgids)
        self.assertIn("Warenkorb", msgstrs)
        # An obsolete entry is dead copy and must not be read as live.
        self.assertNotIn("Obsolete checkout", msgids)
        self.assertNotIn("Alte Kasse", msgstrs)


class RatchetTests(unittest.TestCase):
    def baseline(self, rows):
        return {
            (source, term, commerce.normalise(text)): {"count": count, "why": "why"}
            for source, term, text, count in rows
        }

    def hit(self, source, term, text, line=1):
        return commerce.Hit("gettext", source, line, text, term)

    def test_an_unbaselined_hit_fails(self):
        findings, covered = commerce.apply_baseline(
            [self.hit("a.php", "order*", "Order now")], {}, live=False
        )
        self.assertEqual(covered, 0)
        self.assertEqual(len(findings), 1)
        self.assertIn("new 'order*'", findings[0])

    def test_a_baselined_hit_passes(self):
        baseline = self.baseline([("a.php", "order*", "Order now", 1)])
        findings, covered = commerce.apply_baseline(
            [self.hit("a.php", "order*", "Order now")], baseline, live=False
        )
        self.assertEqual(findings, [])
        self.assertEqual(covered, 1)

    def test_more_occurrences_than_recorded_fails(self):
        baseline = self.baseline([("a.php", "order*", "Order now", 1)])
        findings, _covered = commerce.apply_baseline(
            [self.hit("a.php", "order*", "Order now", 1), self.hit("a.php", "order*", "Order now", 9)],
            baseline,
            live=False,
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("grew from 1 to 2", findings[0])

    def test_a_rewritten_string_leaves_the_entry_stale(self):
        baseline = self.baseline([("a.php", "order*", "Order now", 1)])
        findings, covered = commerce.apply_baseline(
            [self.hit("a.php", "order*", "Start your inquiry")], baseline, live=False
        )
        self.assertEqual(covered, 0)
        self.assertTrue(any("stale baseline entry" in finding for finding in findings))
        self.assertTrue(any("new 'order*'" in finding for finding in findings))

    def test_reflow_does_not_read_as_a_new_string(self):
        baseline = self.baseline([("a.php", "order*", "Order now, pay later", 1)])
        findings, _covered = commerce.apply_baseline(
            [self.hit("a.php", "order*", "Order now,\n   pay later")], baseline, live=False
        )
        self.assertEqual(findings, [])

    def test_a_repository_entry_is_not_stale_during_the_live_smoke(self):
        """The two scans cover disjoint sources; neither may stale the other's."""
        baseline = self.baseline([("a.php", "order*", "Order now", 1)])
        # A clean live site: no hits at all, and no db: entries to compare.
        findings, covered = commerce.apply_baseline([], baseline, live=True)
        self.assertEqual(findings, [])
        self.assertEqual(covered, 0)

    def test_a_live_entry_is_not_stale_during_the_repository_scan(self):
        baseline = self.baseline([("db:page:home", "order*", "Order now", 1)])
        findings, _covered = commerce.apply_baseline([], baseline, live=False)
        self.assertEqual(findings, [])

    def test_a_stale_live_entry_still_fails_the_smoke(self):
        baseline = self.baseline([("db:page:home", "order*", "Order now", 1)])
        findings, _covered = commerce.apply_baseline(
            [commerce.Hit("db", "db:page:other", 1, "Clean copy", "order*")],
            baseline,
            live=True,
        )
        self.assertTrue(any("stale baseline entry" in finding for finding in findings))

    def test_an_exemption_without_a_reason_fails_the_whole_run(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "baseline.json"
            path.write_text(
                json.dumps(
                    {
                        "files": {
                            "a.php": [
                                {"term": "order*", "string": "Order now", "justification": "  "}
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(RuntimeError) as raised:
                commerce.load_baseline(path)
        self.assertIn("no justification", str(raised.exception))

    def test_a_matrix_entry_without_a_term_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "baseline.json"
            path.write_text(
                json.dumps({"files": {"a.php": [{"string": "Order now", "justification": "x"}]}}),
                encoding="utf-8",
            )
            with self.assertRaises(RuntimeError):
                commerce.load_baseline(path)


class LegalPageTests(unittest.TestCase):
    def test_the_four_protected_slugs_are_exempt(self):
        for slug in ("privacy-policy", "datenschutz", "terms-of-sale", "verkaufsbedingungen"):
            hit = commerce.Hit("db", f"db:page:{slug}", 1, "An order", "order*")
            self.assertTrue(commerce.is_legal(hit), slug)

    def test_a_marketing_page_is_not_exempt(self):
        hit = commerce.Hit("db", "db:page:capability", 1, "An order", "order*")
        self.assertFalse(commerce.is_legal(hit))

    def test_a_repository_file_is_never_exempt(self):
        hit = commerce.Hit("gettext", "privacy-policy.php", 1, "An order", "order*")
        self.assertFalse(commerce.is_legal(hit))


class LiveDatabaseTests(unittest.TestCase):
    """The --wp-cli mode reads post_content; production runs are main-line's."""

    def test_the_smoke_orders_the_three_outcomes(self):
        """Fixture run of the deploy smoke: baselined passes, new fails, legal reports."""
        import subprocess

        rows = [
            {
                "ID": "6913",
                "post_name": "home",
                "post_type": "page",
                "post_content": "<p>Check combinations before you order.</p>",
            },
            {
                "ID": "1674",
                "post_name": "terms-of-sale",
                "post_type": "page",
                "post_content": "<p>Payment is by bank transfer.</p>",
            },
            {
                "ID": "6921",
                "post_name": "commercial-storage",
                "post_type": "page",
                "post_content": "<p>Versand aus Deutschland.</p>",
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            wp = Path(directory) / "wp"
            # A stand-in for WP-CLI: the argument the smoke passes is asserted
            # in test_the_wp_cli_invocation_is_read_only.
            wp.write_text(
                "#!/bin/sh\ncat <<'JSON'\n" + json.dumps(rows) + "\nJSON\n", encoding="utf-8"
            )
            wp.chmod(0o755)
            baseline = Path(directory) / "baseline.json"
            baseline.write_text(
                json.dumps(
                    {
                        "files": {
                            "db:page:home": [
                                {
                                    "term": "order*",
                                    "string": "Check combinations before you order.",
                                    "count": 1,
                                    "justification": "fixture",
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(CHECKS / "commerce-terms.py"),
                    "--wp-cli",
                    "--wp",
                    str(wp),
                    "--baseline",
                    str(baseline),
                ],
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 1, result.stderr)
        # The baselined page does not appear as a finding…
        self.assertNotIn("db:page:home", result.stdout.split("legal")[0])
        # …the new German hit does…
        self.assertIn("new 'Versand*'", result.stdout)
        # …and the protected page is reported without failing on its own.
        self.assertIn("hit(s) on protected legal pages", result.stdout)
        self.assertIn("db:page:terms-of-sale", result.stdout)

    def test_published_content_is_read_as_prose(self):
        documents = [
            (
                "page",
                "capability",
                '<p>Check compatibility before you order.</p>'
                '<div class="wc-proceed-to-checkout"><a href="/x">x</a></div>',
            )
        ]
        hits = commerce.live_hits(documents, commerce.load_terms())
        self.assertEqual([hit.term for hit in hits], ["order*"])
        self.assertEqual(hits[0].source, "db:page:capability")

    def test_a_legal_page_hit_is_kept_but_exempt_from_failing(self):
        documents = [("page", "terms-of-sale", "<p>Payment falls due on delivery.</p>")]
        hits = commerce.live_hits(documents, commerce.load_terms())
        self.assertTrue(hits)
        self.assertTrue(all(commerce.is_legal(hit) for hit in hits))

    def test_the_wp_cli_invocation_is_read_only(self):
        """No write verb may appear in the commands the smoke runs."""
        source = (CHECKS / "commerce-terms.py").read_text(encoding="utf-8")
        start = source.index("def wp_run")
        end = source.index("def live_hits")
        body = source[start:end]
        self.assertIn('"post",\n            "list",', body)
        for verb in ("update", "delete", "create", "edit", "meta", "option"):
            self.assertNotIn(f'"{verb}"', body)

    def test_a_row_without_the_content_field_is_fetched_individually(self):
        """A build that drops the column must not be read as a clean site."""
        with tempfile.TemporaryDirectory() as directory:
            wp = Path(directory) / "wp"
            wp.write_text(
                "#!/bin/sh\n"
                "case \"$2\" in\n"
                "  list) echo '[{\"ID\":\"7\",\"post_name\":\"capability\",\"post_type\":\"page\"}]' ;;\n"
                "  get) echo '<p>Before you order</p>' ;;\n"
                "esac\n",
                encoding="utf-8",
            )
            wp.chmod(0o755)
            documents = commerce.live_documents(str(wp))
        self.assertEqual(documents, [("page", "capability", "<p>Before you order</p>")])
        self.assertEqual(
            [hit.term for hit in commerce.live_hits(documents, commerce.load_terms())],
            ["order*"],
        )

    def test_an_unreadable_row_fails_instead_of_counting_as_clean(self):
        with tempfile.TemporaryDirectory() as directory:
            wp = Path(directory) / "wp"
            wp.write_text(
                "#!/bin/sh\n"
                "case \"$2\" in\n"
                "  list) echo '[{\"post_name\":\"x\",\"post_type\":\"page\"}]' ;;\n"
                "  get) exit 1 ;;\n"
                "esac\n",
                encoding="utf-8",
            )
            wp.chmod(0o755)
            with self.assertRaises(RuntimeError):
                commerce.live_documents(str(wp))


if __name__ == "__main__":
    unittest.main()
