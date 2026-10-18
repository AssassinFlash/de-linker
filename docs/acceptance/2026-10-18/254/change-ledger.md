# Owner-reviewed visual changes

| Surface | Authority and intended difference | Acceptance |
|---|---|---|
| German browser titles | #254: distinguish login, registration, password reset, archives, pagination and individual inquiries; preserve independent native German SEO copy. | Actual `<title>` values in the complete route table, entity/whitespace normalisation and uniqueness test. |
| German headings of renamed draft/document/service/category/accessory pages | #254: German vocabulary must agree with the destination. | Native object migration plus `present` pairing and visible EN/DE page checks. |
| Product detail presentation, both languages | In this session the owner explicitly rejected the dense compatibility cards and wrapping pill labels and requested a design adjustment. | Balanced gallery/information proportions, dominant model heading, quieter auxiliary controls, two-column documents; two-column compatibility reading list on desktop, one column on tablet/mobile; larger unobstructed product images; clear name/SKU/source hierarchy; quiet source text; native product links and keyboard focus retained. This product page is an additional English visual exception. |
| Inquiry submission, both languages | In this session the owner rejected the unstyled form and then the visual discontinuity with the rest of the site. The requested correction uses the approved two-column inquiry prototype and the existing site's type, spacing, colour, form and card tokens. | Form card with integrated heading/back link; consistent fields and consent/action; pale draft summary; native product thumbnail and quantity; desktop/mobile and guest/signed-in/error/confirmation states. This page is the explicit English visual exception. |

The inquiry change does not add fields, invent product facts, require an account or change submission behavior. The optional signed-in company/address fields retain their existing native contract. All composition changes live in LC exports and WindPress; PHP supplies product data and existing translated labels.

English marketing, product lists, categories, blog, navigation, draft and account pages retain the zero-pixel comparison requirement. Browser titles do not change screenshot pixels. No dynamic masks are presumed. Preliminary captures with unloaded lazy images or media spinners were rejected and are not used as passing evidence.

Visual fixture disclosure: videos are paused at their loaded first frame and animations/transitions/caret are disabled identically before/after. Lazy images must be scrolled into view and loaded. The error-state captures explicitly seed the existing local Woo session flash with synthetic details; the form consumes it normally. They prove error presentation, while the real submission/validation behavior is covered by the repeated OpenInquiry integration suite. Confirmation captures use owned local records and native keys. No production fixture, test message or test account is created.

The accepted EN baseline waits for the native image `decode()` promises and two paint frames in the local fixture, then confirms the readiness marker before capture. An earlier product baseline with blank compatibility images was rejected. No placeholder capture is used to claim parity.

Final scope clarification: after selecting the compatibility area as the primary concern, the owner explicitly accepted the related proportions, hierarchy, auxiliary controls and document-density optimizations and asked to see them again. Those refinements are included in the final product presentation. The original prototype A mobile glass action pill remains the authority for that control.

Prototype authority: product-page variant A is stored on `prototype/pdp-redesign` at `4d3733bd33cb6cdac5d24a8b90b52584ad46abec`, selected in `docs/specs/174-pdp.md`; the prototype contains no compatibility area. Inquiry variant B is selected in `docs/prototypes/2026-10-17-inquiry/DECISION.md`. Prototype copy and sample facts are not imported into product data.

## Additional explicit owner correction

After seeing stabilized before/after diagnostics, the owner said the designs themselves were poor and supplied three region screenshots. This authorizes these additional changes in EN and DE:

| Region | Final design intent | Native / data contract |
|---|---|---|
| Blog archive recommendation and adjacent reading rows | A compact open reading composition, useful image scale, full titles and a quieter summary; no stacked padded card shell. | The same LC loops, featured image, post title, excerpt and permalink. |
| Blog category topics | A labelled open index with naturally wrapped labels, two columns on mobile and a native current-topic indicator. | LC `lc_get_cats` → WordPress `wp_list_categories` → Polylang term links; “All topics” / “Alle Themen”. |
| Service introduction | Aligned existing photo group and a continuous capability list; mobile shows all four capabilities with readable type. | The stored LC content remains intact. New WindPress rules replace the visual effect of its photo dock in this region; native contact/navigation remains intact. |

The zero-pixel gate now applies to the nine unaffected English page types at both viewports (18 comparisons). Product, inquiry, blog index, blog category and service page screenshots carry the owner-authorized region changes; those changes are reviewed visually and listed here. No dynamic mask or colour tolerance is introduced.

### Final journal reference

The owner's later [light reference](owner-journal-reference-1.png) and [dark reference](owner-journal-reference-2.png) specify the desired content-platform composition. The final EN/DE index, category and search lists use a topic rail/sidebar, native search, featured cover, thumbnail feed and desktop more-reading rail. This supersedes the intermediate traditional archive-card treatment. All cards remain genuine written-post links; thumbnail ratios and visual grouping do not imply video functionality. The shared site chrome and individual post-reading template are preserved. Search is an additional explicitly verified visual state of this same discovery flow.

### Approved service and single-post reading

The owner approved the service screenshot, then supplied [mobile browsing](owner-mobile-reference-1.png), [mobile reading](owner-mobile-reference-2.png), [desktop reading](owner-reader-reference-1.png) and [contents/reading reference](owner-reader-reference-2.png). The final discovery flow uses compact mobile recommendation rows. Single posts use a chapter rail, a measured reading column, related reading and sharing; mobile joins the cover to the reading panel and collapses the contents disclosure. This is an additional explicitly authorized EN visual exception, verified in EN/DE at both widths. No existing written content is reauthored as a consequence of the design change.
