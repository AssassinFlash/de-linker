# Product search and filter recovery

## Problem and scope

On the product archive, a search with no matching products and no selected
filter displayed instructions to clear a filter. In the mobile view the
filter count was zero. The empty message must reflect the current selection,
and filter-reset controls must not discard an independent search.

## Behaviour

- With no search or selected facet, retain the existing empty-section message.
- With only a search, say that the search has no matching products and offer
  another search term. With only facets, name the selected filters and suggest
  changing or clearing one. With both, name both and offer either option.
- The product search field and individual filter chips retain their existing
  behaviour. The filter rail's Reset, its mobile Clear, and the chips' Clear
  all remove the selected facets while retaining the validated search, sort,
  and the current localized shop or category path; pagination starts over.
- The existing All products action continues to clear the entire selection
  and return to the localized product page. No product data, query matching,
  shared header, template design, or marketing text changes.

The messages do not promise that changing a condition will produce results.
EN and DE use the native commerce translation catalog. The existing empty
component test and the filter/chip tests cover the distinct selection cases
and the encoded search with sorting. A real browser still has to exercise
the affected controls and localized empty states in both viewport sizes.

## Copy review

The initial EN and DE drafts are the three search, filter and combined
messages in `ProductShortcodes.php` and `linker-commerce-de_DE_formal.po`.
An independent review checked them against the Linker copy rules and the
available recovery actions. It found the guidance truthful and the German
natural, and recommended retaining all three pairs as drafted. The existing
Clear all label sits beside the filter chips; check its context in the real
page because the action now retains the search term.

## Candidate review and local acceptance

The implementation at `2cf6152ae` passed independent Spec and Standards
review without a confirmed finding. The independent copy review is recorded
above. The existing affected PHP tests passed (52 tests, 229 assertions),
as did the changed-file coding standards and PHPStan checks, catalog validity
and translation coverage. The German MO was compiled and its new messages
read back.

On the existing live-snapshot instance, native HTTP readback covered EN and
DE search-only, filter-only and combined empty results. On both language
category paths, Reset, mobile Clear and Clear all retained an encoded search
and sort while removing the facet and page number. A browser exercised EN
and DE at desktop and mobile widths: Clear all, mobile Clear and rail Reset
retained the search and sort; All products cleared them and restored 53
product families. The Clear all control was clear in its filter-chip context,
and the four views had no document-level horizontal overflow.

The browser observations and screenshots are in
`/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/751-search-candidate-consumers.json`.
The temporary local candidate was removed and the original plugin link and
runtime source restored. These results are local acceptance; shared CI,
production publication and online readback belong to the integrated batch.
