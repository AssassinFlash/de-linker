"""Runtime source extraction must include formatted modern application calls."""

import unittest

from i18n_sources import gettext_strings


class GettextSourceTests(unittest.TestCase):
    def test_trailing_comma_keeps_the_literal_domain(self):
        code = '__("A saved project",\n "linker-tools",\n);'
        self.assertEqual(
            gettext_strings(code, domain="linker-tools"), [("A saved project", 1)]
        )

    def test_nested_count_and_other_domain_do_not_confuse_the_final_argument(self):
        code = '_n("Project", "Projects", count(items, 2), "linker-tools",); __("Other", "other");'
        self.assertEqual(gettext_strings(code, domain="linker-tools"), [("Project", 1)])

    def test_nonliteral_domain_is_not_made_into_a_literal(self):
        self.assertEqual(
            gettext_strings('__("Project", variable,);', domain="linker-tools"), []
        )


if __name__ == "__main__":
    unittest.main()
