# Recover from missing pages through the native site search

## Observed problem

The live English 404 form promises products and solutions. An actual search for
SAJ ATS1 reaches `/?s=SAJ+ATS1`, but the query is narrowed to posts and the only
search template calls the result a journal search. It returns no matching posts
although the named public product exists. The same entry must search the content
it promises; reducing its promise to the journal or products alone would leave
the missing recovery capability unresolved.

## Native implementation and boundaries

WordPress owns the main search, publication permissions and pagination.
LiveCanvas owns both language templates and their native contextual loops.
WindPress supplies the existing journal/search classes. The existing search
stylesheet gives the search input a44px minimum touch height; no new stylesheet,
app, endpoint, model, query transport or PHP layout is introduced.

- Implicit public searches use post/page/product. Attachments and internal
  document types are outside the public results. Explicit requests, including
  journal forms with post_type=post, retain their native type scope. The
  existing header/footer language switch preserves that exact journal scope;
  malformed type lists are not promoted into it.
- The search LC templates preserve the complete existing journal branch when
  post_type is post. General search gets an appropriate results branch, public
  navigation, generic titles/images and a query input; it does not show product
  rows as dated journal articles or display product prices.
- Product publication must also hold within mixed post-type queries. A global
  product-only post__in would erase matching pages and posts. Read the native
  product status census, exclude forbidden product IDs, and retain other types.
  If a caller already has post__in, normalize its IDs with native absint
  before filtering that list directly: core WP_Query
  gives it precedence over post__not_in. An emptied include list becomes [0].
- Product-only collections retain their existing path. Engineering reference
  inputs, unpublished source/mirror pairs and private products stay outside
  customer results. No product facts, status or metadata are written.
- The actual German404 search form also submitted to the English root.
  Correct that single GET form action in its existing LC twin through native
  WP_HTML_Tag_Processor and explicit pll_home_url(de). Preserve all remaining
  markup, wording, metadata, pairs and backslashes; do not add a template,
  PHP layout or client redirect. Its source has no role attribute, so match
  the unique GET form and require exactly one before any save.
- Marketing/privacy bodies, source context, business forms and notifications
  are outside this change. The404 search promise stays intact.

## Minimum acceptance and current evidence

The live search above is the original red consumer. The existing SearchScope
and VisibilityRead tests were extended in place; before source changes they
failed on site scope and the product-only allow-list. After the source change,
7 selected cases have 41 assertions, with 3 existing native-only skips. This is
unit proof only, not template/native/browser/production acceptance.

Reuse the current local snapshot and instance. Verify both native branches,
public product plus solution/page and post results, no-match, pagination and
quoted/escaped query handling. Prove mixed result counts and exclusion of a
local reference/private/withdrawn product through the real main query. Check
EN/DE at1440/390 and actual 404 form → results → matching product. No customer
business form, mail, model or new snapshot is needed. Final Spec/Standards,
precise CI, backup, scoped template/code publication and online readback remain
required before closing the issue.

## Journal input retention

The EN/DE journal search input displays the submitted phrase through LiveCanvas's native `lc_the_search_query` shortcode. Its escaped value remains editable after a search, including quotes and ampersands. The existing general-search `Url query=s` binding and all search scopes, forms, words, result loops and pagination stay unchanged.

## UI wording draft

EN / DE: Search the site / Website durchsuchen; Search sections / Suchbereiche;
Results / Ergebnisse; No matching results found. / Keine passenden Ergebnisse
gefunden.; Try another search term. / Versuchen Sie einen anderen Suchbegriff.
Other navigation and search labels reuse existing terms. Adversarial review approved the four other pairs and changed only the EN
ARIA draft Search routes to Search sections. These are necessary interface
labels, not marketing-body edits. Native/browser/production acceptance remains
pending.
