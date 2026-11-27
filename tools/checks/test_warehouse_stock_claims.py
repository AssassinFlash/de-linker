"""Public warehouse promises and the customer language that remains valid."""

import importlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

claims = importlib.import_module("warehouse-stock-claims")


class WarehouseClaimsTest(unittest.TestCase):
    def test_all_prohibited_phrases(self):
        for text in (
            "German warehouse stock",
            "WAREHOUSE STOCK",
            "warehouse in Germany",
            "warehouse location",
            "warehouse delivery",
            "our warehouse",
            "our German warehouse",
            "in its warehouse",
            "stock in Germany",
            "stocked in Barleben",
            "from stock",
            "against our stock",
            "local stock",
            "confirmed stock availability",
            "Lagerbestand in Deutschland",
            "Lagerware",
            "ab Lager",
            "im deutschen Lager",
            "auf Lager in Barleben",
            "aus dem Lager",
            "aus unserem deutschen Lager",
            "Lager in Deutschland",
            "Lagerverfügbarkeit",
            "Lagerlieferung",
            "Lagerstandort",
        ):
            with self.subTest(text=text):
                self.assertRegex(text, claims.PHRASE)

    def test_valid_stock_address_and_storage_terms(self):
        for text in (
            "In stock",
            "Out of stock",
            "Auf Lager",
            "Nicht vorrätig",
            "your company warehouse",
            "Ihr Firmenlager",
            "Rotterdam warehouse project",
            "Lagerhalle Rotterdam",
            "Lagertemperatur",
            "Lagerdauer",
            "Bestands-PV",
        ):
            with self.subTest(text=text):
                self.assertNotRegex(text, claims.PHRASE)

    def test_visible_inline_text_labels_and_block_boundaries(self):
        html = (
            "<p>Stocked&nbsp;<b>in</b> Germany.</p><p>Warehouse</p><p>location</p>"
            '<i title="warehouse delivery" data-example="warehouse stock"></i>'
            "<script>local stock</script><style>/* from stock */</style>"
            '<p>[linker_example label="Warehouse location" class="from stock"]</p>'
            '<p>Products in <a href="#" title="our warehouse">our</a> warehouse.</p>'
        )
        self.assertCountEqual(
            [
                m.group()
                for _, txt in claims.visible_text(html)
                for m in claims.PHRASE.finditer(txt)
            ],
            [
                "Stocked\xa0in Germany",
                "warehouse delivery",
                "Warehouse location",
                "our warehouse",
                "our warehouse",
            ],
        )

    def test_repository_surfaces(self):
        fixtures = {
            "plugins/demo/front.php": """<?php __( 'Stock in Germany', 'linker' );""",
            "themes/demo/index.php": """<?php _e( 'Warehouse stock', 'linker' );""",
            "apps/planner/src/card.tsx": """__( 'From stock', 'linker' )""",
            "plugins/demo/content/group/card.html": '<img alt="local stock">',
            "plugins/demo/languages/messages.po": 'msgid "From stock"\nmsgstr "Ab Lager"\n',
            "plugins/linker-commerce/data/operating-policies.json": json.dumps(
                {"policies": {"shipping": {"value": "our warehouse"}}}
            ),
            "plugins/linker-commerce/data/faq-trade.json": json.dumps(
                {"categories": [{"qas": [{"answer": {"de": "Lagerware"}}]}]}
            ),
        }
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, data in fixtures.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(data, encoding="utf-8")
            self.assertCountEqual(
                [hit[0] for hit in claims.findings(claims.repo_strings(root))],
                [*fixtures, "plugins/demo/languages/messages.po"],
            )

    def test_plural_forms_are_independent_customer_messages(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            php = root / "plugins/demo/count.php"
            php.parent.mkdir(parents=True)
            php.write_text(
                "<?php _n( 'One device', 'Devices from stock', $n, 'linker' );"
            )
            po = php.parent / "languages/forms.po"
            po.parent.mkdir()
            po.write_text(
                'msgid "One device"\nmsgid_plural "Products from stock"\n'
                'msgstr[0] "Lieferung ab Lager"\nmsgstr[1] "Lagerlieferung"\n'
                '\n#~ msgid "Our warehouse"\n#~ msgstr "Lagerware"\n'
            )
            self.assertCountEqual(
                [match for _, _, match in claims.findings(claims.repo_strings(root))],
                ["from stock", "from stock", "ab Lager", "Lagerlieferung"],
            )

    def test_live_pages_check_body_and_all_three_descriptions(self):
        row = {
            "ID": "7",
            "post_type": "page",
            "post_name": "logistik",
            "post_content": '<p>aus <em>dem</em> Lager</p><img alt="Am Arbeitsplatz im Lager"><script>our warehouse</script>',
            "_seopress_titles_desc": "Lagerstandort",
            "_seopress_social_fb_desc": "Warehouse stock",
            "_seopress_social_twitter_desc": "Lagerware",
        }
        with patch.object(claims.subprocess, "run") as run:
            run.return_value.stdout = json.dumps([row])
            rows = claims.live_rows("ssh host /usr/local/bin/wp --path=/site")
        self.assertEqual(
            run.call_args.args[0],
            ["ssh", "host", "/usr/local/bin/wp", "--path=/site", "eval-file", "-"],
        )
        query = run.call_args.kwargs["input"]
        self.assertIn("post_status = 'publish'", query)
        self.assertIn("'page', 'post'", query)
        hits = list(claims.findings(claims.live_strings(rows)))
        self.assertCountEqual(
            [hit[0].rsplit(":", 1)[-1] for hit in hits],
            [
                "post_content",
                "_seopress_titles_desc",
                "_seopress_social_fb_desc",
                "_seopress_social_twitter_desc",
            ],
        )
