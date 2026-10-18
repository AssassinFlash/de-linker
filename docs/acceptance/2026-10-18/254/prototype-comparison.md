# Existing prototypes and this session's approved increments

The existing product reference is **variant A** on branch `prototype/pdp-redesign`, commit `4d3733bd33cb6cdac5d24a8b90b52584ad46abec`, path `docs/design/2026-10-15-pdp-prototype/index.html?variant=a`. The source is not on main; the selected version and original acceptance are recorded in `docs/specs/174-pdp.md` and `docs/acceptance/2026-10-15/174/acceptance.md`. Existing reference screenshot: [saved prototype screenshot](../../2026-10-15/174/shots/proto-en-1440.png).

The inquiry reference is **variant B**, selected in `docs/prototypes/2026-10-17-inquiry/DECISION.md`, with the saved `screens/iq-B.png`.

A c254-only static preview of the original product A was opened for the owner at `http://127.0.0.1:9129/wp-content/uploads/254-reference-pdp/index.html?variant=a&lang=en`. Only upload/font URLs were projected to this instance; the Git source was preserved. It creates no WordPress object or sitemap entry and is never deployed. Prototype sample facts/copy are not imported into product data.

| Area | Existing authority | Final treatment |
|---|---|---|
| Product composition | A: gallery + intro on the left, inquiry rail on the right; rail confined to upper grid | Structure and sticky boundary retained in LC/native handlers. |
| Gallery/information proportions | A: 2:1 columns, 4:3 gallery | Owner explicitly accepted a more balanced 1.2:1 split and 6:5 gallery in this session. One container rule still serves every section. |
| Type hierarchy | A's original product and section headings | Owner accepted a stronger product-model H1 and quieter section H2; native text remains unchanged. |
| Auxiliary controls | A: Compare / Ask Genie / Documents | The same actions become a quieter horizontal tool row; handlers and keyboard focus remain native. |
| Documents | A: fluid document cards | Owner accepted two wider columns to avoid cramped long filenames; mobile remains one column. Native links/metadata unchanged. |
| Technical data / scenes / FAQ | A: three specification groups, full-width sections and optional FAQ side picture | Existing composition retained. Real product fields determine which sections exist. |
| Mobile primary action | A's final selected floating glass pill | Retained after checking the actual prototype decision. Its measured-height clearance and safe area behavior remain intact. |
| Compatibility | The product spec explicitly says this group was absent from the prototype | Added as a two-column reading list, one column below the existing tablet breakpoint; larger images, clear name/SKU/source hierarchy, no wrapping source pill. Native facts and product links remain unchanged. |
| Inquiry | B: left form, right editable draft; signed-in details collapsed | Same composition, existing site tokens and copy; full native guest/customer/error/confirmation states verified separately. |

The owner first identified the compatibility group as the primary concern, then explicitly accepted the related proportions, hierarchy, controls and document-density refinements and asked to see them again. These are the final approved increments to A. The earlier standalone solid mobile bar was withdrawn after confirming A's explicit mobile treatment.

## Journal and service references added by the owner

The owner explicitly approved the revised service introduction, then selected a content-platform direction for the blog and supplied mobile/news/reading references. Those direct instructions authorize the journal index, category, search and single reading templates to move beyond their earlier reconstruction. [Light reference](owner-journal-reference-1.png), [dark reference](owner-journal-reference-2.png), [mobile discovery](owner-mobile-reference-1.png), [mobile reading](owner-mobile-reference-2.png), [desktop reader](owner-reader-reference-1.png), [contents reference](owner-reader-reference-2.png).

The final design uses Linker's existing tokens, original post data and actual links. It includes a desktop topic sidebar/search/featured cover, two-column content cards, compact mobile discovery rows, left contents/central prose/right related reading, a native collapsed mobile contents disclosure, and uniform native sharing targets. It does not add social accounts, saved state, playback, ratings or popularity claims. Service uses the stored LC photos/capability content with a WindPress composition; its four mobile rows are visible. Final actual screenshots and action readback are linked from README and design-layouts.json.
