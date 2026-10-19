# #265 red/green evidence

Recorded 2026-10-19 on branch `feat/265-german-checks` (base `origin/main`
`f59cd9b5`). Everything below is re-runnable from the repository root.

## Green: the gates pass on current main's content

Both gates run over this tree (same content as main for every scanned
surface — this branch only adds checks):

    $ just german-copy
    german-copy: clean

    $ just internal-home-urls
    internal-home-urls: clean

## Red: each planted fixture fails the gate

The planted fixtures are the pytest suites; each failing case plants one
defect in an isolated tree and asserts the gate exits 1 naming it:

    $ cd tools/migrate && uv run --locked pytest tests/test_german_copy.py tests/test_internal_home_urls.py -v
    40 passed

One line per check (`tools/migrate/tests/test_german_copy.py` unless noted):

| Check (rule) | Planted fixture (red) | Passing counterpart (green) |
|---|---|---|
| Banned word from the shared list, .po | `test_a_banned_word_in_a_po_msgstr_fails_the_gate` ("In den Warenkorb legen") | `test_a_clean_po_msgstr_passes_the_gate` |
| du-form pronouns, .po | `test_the_du_form_in_a_po_msgstr_fails_the_gate` ("Dein Dach") | `test_a_clean_po_msgstr_passes_the_gate` |
| Obsolete entries are dead | — (skip rule) | `test_an_obsolete_po_entry_is_dead_copy` |
| Shared list present (database kind) | `test_a_missing_shared_banned_list_disarms_both_fences` | the same fixture without the unlink |
| English month dates, .po | `test_an_english_date_in_a_po_msgstr_fails_the_gate` ("October 19" / "19 October 2026" / "May 29, 2026") | `test_german_dates_pass_the_gate` ("19. Oktober 2026") |
| ISO date, .po | `…[Gültig ab 2026-10-19]` | `…[29.05.2026]` |
| Artikel blog word | `test_the_blog_article_word_fails_the_gate` ("Artikel lesen", "Artikelkontext", …) | `test_legal_citations_and_sku_numbers_pass_the_gate` ("Artikel 6 DSGVO", "Artikelnummer") |
| Generated JSON values | `test_a_hand_edited_german_json_value_fails_the_gate` | `test_generated_json_metadata_is_not_copy` |
| du-form, German template text | `test_the_du_form_in_a_german_template_fails_the_gate` | `test_a_german_templates_attributes_are_not_prose` (`dir="ltr"`) |
| Label attributes are copy | `test_a_german_templates_label_attributes_are_copy` (placeholder "Artikel suchen") | — |
| `date_format` day-first, German templates | `test_an_english_date_format_in_a_german_template_fails_the_gate` ("M j, Y", "F j, Y", "Y-m-d") | `test_a_german_date_format_in_a_german_template_passes` ("d.m.Y", "j. F Y") |
| English face stays free | — (scope rule) | `test_english_templates_are_out_of_scope` |
| Journal labels | `test_a_banned_word_in_a_journal_title_fails_the_gate` | `test_the_english_half_of_a_journal_title_is_not_german_copy` |
| Catalogue word (absorbed grep) | `test_the_english_catalogue_word_fails_the_gate` (templates/, languages/) | `test_the_catalogue_exclusions_stay` |
| German hrefs (`tools/migrate/tests/test_internal_home_urls.py`) | `test_an_english_site_path_in_a_german_export_fails` (`href="/product/"`) | `test_german_dynamic_and_offsite_hrefs_pass` |
| PHP home_url literals (#263 rule unchanged) | `test_the_php_literal_rule_still_fires` | — |

## Red against origin/main (the gates did not exist there)

Copied the two test files into a worktree of `origin/main` and ran the same
command:

    $ cd <worktree of origin/main>/tools/migrate && uv run --locked pytest tests/test_german_copy.py
    E   FileNotFoundError: … tools/checks/german-copy.py does not exist  (collection error)

    $ … pytest tests/test_internal_home_urls.py
    FAILED test_an_english_site_path_in_a_german_export_fails   # no German href rule yet

    $ python3 tools/checks/internal-home-urls.py --root .        # main's own gate still green
    internal-home-urls: clean
