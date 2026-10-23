# Contact source language and static homepage identity

Marked links in saved page content send visitors to Contact with a public source
URL. The German destination was localized while its `source` query still named
the English page. On the German homepage this omitted the source summary. A
control request with `/de/` restored a summary titled `Deutsch`: native
`url_to_postid` returned zero and a public language taxonomy won the fallback.

The current snapshot contains 78 marked anchors across 18 published pages. The
39 German anchors span nine pages. This is a saved-content inventory, not proof
that every dynamic entry or consumer has been exercised.

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
Real browser consumers must verify EN/DE at 1440 and 390, including navigation,
source summary, inclusion choice and contact language switching without submit.
Relevant checks and both independent review axes precede integration. Production
and full-site coverage remain separate gates; local proof does not sign them.
