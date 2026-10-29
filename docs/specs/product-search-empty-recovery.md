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
