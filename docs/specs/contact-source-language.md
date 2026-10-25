# Contact source language and static homepage identity

Marked links in saved page content send visitors to Contact with a public source
URL. The German destination was localized while its `source` query still named
the English page. On the German homepage this omitted the source summary. A
control request with `/de/` restored a summary titled `Deutsch`: native
`url_to_postid` returned zero and a public language taxonomy won the fallback.

The current snapshot contains 78 marked anchors across 18 published pages. The
39 German anchors span nine pages. This is a saved-content inventory, not proof
that every dynamic entry or consumer has been exercised.

Actual browser acceptance exposed a second native context: Polylang filters
`home_url` while the theme renders a German page. WordPress `url_to_postid` then
misses English source pages such as Services & Support. A direct CLI localizer
with `PLL_Admin` does not reproduce that frontend behavior. The existing
resolver therefore needs a canonical, public native page lookup when URL lookup
returns zero. The live FAQ template also replaces its saved page content: its
two stored marked anchors are inventory records, not currently rendered entries.
An actual HTTP diagnostic additionally proves native URL lookup can return the
current German twin for an English source URL. The object's language alone must
not classify that English URL as already localized.

The rendered German utility invitation exposed a separate empty-link failure.
Its native shortcode output contains a valid raw `Großspeicher` query title.
Under the frontend's native URL parser, one byte of `ß` becomes an underscore;
rebuilding from that parsed query produces invalid UTF-8 and HTML encoding
empties the href. Address parsing remains necessary for origin and identity
checks, but query and fragment transport must use the original bytes. The
already-localized destination, a translated destination and reverse navigation
all require the same preservation.

## Required behavior

- An anchor explicitly carrying `data-linker-contact` localizes both its main
  destination and its same-origin `source` URL into the rendered language. This
  also works when the destination already belongs to that language. English
  navigation can restore the English source.
- Only the source URL value changes inside the query. Other query bytes,
  selected searches and filters, fragments, marker JSON, media, scripts and
  backslashes retain their values. The public `LinkLocalizer::url` API and
  unmarked anchors retain their existing query contract.
- Foreign hosts, alternate schemes or ports, credentials, protocol-relative
  addresses and relative source URLs cannot be converted into accepted public
  sources. Unknown source paths remain unknown. Source titles and IDs supplied
  by the browser remain non-authoritative.
- Source conversion separately requires a current public object at its exact
  canonical path. Unknown taxonomy parents and retired aliases must not become
  accepted sources; ordinary link redirect compatibility remains separate.
  Private or password-protected source pages cannot gain validity by conversion
  into a public twin. Repeated source resolution uses the existing request cache.
- Native static homepage options and Polylang pairs identify the actual public
  page before post or taxonomy resolution. Both language roots work regardless
  of the ambient request language or a filtered `page_on_front`. A missing,
  unpublished, protected or non-page front object is rejected; it must not fall
  back to the public language term.
- If the companion language plugin is unavailable, WordPress still resolves the
  static front page and ordinary public sources without a missing-class error.
- Contact language switching carries a verified homepage using the native
  language root, rather than the front page slug returned outside the frontend.
  Existing intent and selected search/filter semantics continue to apply.
- When the frontend home filter causes URL lookup to return zero, resolve a
  page through native `get_page_by_path` only if its current canonical path,
  published page type and empty password match. Do not change locale, suppress
  global filters or accept a private page or a noncanonical alias.
- When native query translation returns the current-language twin, use its
  native pair in the URL's own language and verify the canonical path before
  deciding whether the URL already belongs to the target language.

## Implementation boundary

LiveCanvas already owns the anchors and WordPress/Polylang already own page
identity. Neither LC tags nor WooCommerce rewrite a URL embedded in a contact
query. Extend the existing HTML-token localizer and existing Contact source
validator; use the existing `Languages` adapter for native root URLs and pairs.
No new link handler, layout, CSS, form protection, page title, saved prose,
translation model call, submission or stored-content migration is needed.

Source rollback restores the two runtime PHP files from the preceding fixed
commit. There is no page or metadata write to undo. Keep the already verified
local database baseline and the earlier reviewed homepage content receipts.

## Acceptance

Unit regressions cover marked and unmarked transport, both languages, preserved
query/script bytes, rejected origins, homepage pair identity, unavailable homes
and language switching. Read-only native snapshot fixtures must verify the
marked-page inventory against actual Polylang pairs and public source results.
Include the native frontend home filter in a separate control: CLI language
switching alone does not prove the request-time lookup.
Real browser consumers must verify EN/DE at 1440 and 390, including navigation,
source summary, inclusion choice and contact language switching without submit.
Relevant checks and both independent review axes precede integration. Production
and full-site coverage remain separate gates; local proof does not sign them.
Native rendered acceptance also covers the generated German utility invitation
itself, including actual navigation to a verified `Großspeicher` source summary.

## Delivery completion on the current main branch

The current Contact selection classes already contain the accepted source and
request-label behavior. Production still loads the earlier `LinkLocalizer`:
its marked-link control translates the Contact destination but retains the
English Services source. Complete the existing repair by restoring only the
accepted localizer and its existing regression tests from `aaf46e95`; retain
all newer Contact, REST, marketing-content and presentation changes.

Reuse the fixed-source native and browser acceptance in
`contact-source-acceptance-final.md`. On the current reused snapshot, check
the localizer regressions and the affected source/language consumers. Publish
only `linker-i18n/includes/LinkLocalizer.php` through the existing atomic file
deployment, after a full SQL snapshot and a guarded current-runtime readback.
No stored-content write, new test matrix, CSS compile, model call, registration,
inquiry submission or email is required. Verify the same affected consumers
online and preserve all other runtime bytes, protected page objects and the
current WindPress cache. The native previous-file receipt supplies rollback.

## Accurate source headings and inclusion guidance

The delivered Services source card has no selected product but is headed
`Product selection` / `Produktauswahl`. Label its contents consistently in the
form and existing team/admin consumers: a native product source or requested
product label retains `Product selection`; a source without selected fields is
a `Related page`; filters, document-only requests and unavailable recovery data
use `Related details`. This describes request data and grants no product identity,
stock, availability or document permission. Existing transport and validation
remain authoritative and unchanged.

Use one semantic heading helper in the existing SelectionView. Reuse the current
native source type and normalized fields; do not query a second product source.
Generic inclusion/exclusion feedback refers to details, and the unavailable-data
message identifies the exact inclusion checkbox rather than the privacy consent.
The same reviewed error text replaces the product-only submission error; its
error code and rejection behavior stay unchanged. Customer receipt content stays
unchanged. The existing WindPress markup and CSS require no change.

Copy review: the first draft used `beifügen` and said the customer could leave
details out. Independent review accepted the two headings and exclusion feedback,
but requested clearer sending language and an explicit checkbox label to avoid
file-attachment or privacy-checkbox confusion. The final wording is:

| English | German |
| --- | --- |
| Related page | Zugehörige Seite |
| Related details | Zugehörige Angaben |
| Include these details with my message | Diese Angaben mit meiner Nachricht senden |
| These details will not be sent. | Diese Angaben werden nicht mitgesendet. |
| These details could not be loaded. To send your message without them, uncheck “Include these details with my message”. | Diese Angaben konnten nicht geladen werden. Um Ihre Nachricht ohne diese Angaben zu senden, entfernen Sie das Häkchen bei „Diese Angaben mit meiner Nachricht senden“. |

Extend the existing semantic view regressions for the reported page-only defect
and retained product/filter cases. Reuse unchanged transport, escaping and
inclusion tests. Native unsaved order rendering proves matching team/admin
headings without creating or sending an inquiry. Browser checks use the existing
snapshot for the distinct page/product/filter/document cases and inclusion/error
feedback; no whole-site rerun or new test framework. Publish the two changed PHP
files and the catalog sources/compiled German catalog in the existing Commerce
artifact, with a staged delta of exactly those five files. Protect the current
resolver, page objects and style cache, and read back the affected online consumers
before archive. No WindPress volume install or Generate is needed for text-only
semantic changes when the existing cache remains valid.
