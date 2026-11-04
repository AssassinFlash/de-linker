# Full-matrix pass — defect and divergence findings (2026-11-04)

Scope: findings from this pass's automated sweeps, targeted probes and bounded
production read-only checks. No product code was changed in this batch. Every
finding carries its root cause and reproduction evidence; "production" evidence
comes from read-only GET requests made on 2026-11-04.

## F1 — PDPs render no related-products section (production-confirmed)

- **Symptom**: On production, product detail pages in both languages show zero
  related-product links and no "Related products" heading.
  Reproduction: `https://de-linker.com/product/saj-ats1-t63-a/` and
  `https://de-linker.com/de/produkt/goodwe-gw60k-sts-g10/` —
  `document.querySelectorAll("[class*=related] a").length === 0`, no
  `related products` text (probe output in evidence/state-sweep-results.json,
  state-matrix rows `product:related-products:*:*`).
- **Root cause**: the LiveCanvas dynamic templates for single products (EN 234
  `template-for-single-product`, DE 6903) contain no related-products markup or
  shortcode — see `just wp fullmatrix post get 234 --field=post_content`: the
  template covers crumbs/gallery/purchase/specs/tools but no related loop.
  Because the LC template fully owns the PDP body, WooCommerce's native
  related-products template part never renders.
- **Why it matters**: AGENTS.md §5 "三件套原生优先" names Woo native
  `related` among the mechanisms the presentation layer should use, and
  state-matrix row `product:related-products` (4 rows) expects the state.
- **Decision for the main line**: add the related section to templates 234/6903
  via the native Woo related mechanism (or an explicit owner decision to not
  have related products — then the matrix rows become not-applicable with that
  ruling recorded).

## F2 — "Global JavaScript Code" partial (LC 30) is empty on production

- **Symptom**: `wp db query "SELECT LENGTH(post_content) FROM wp_posts WHERE ID=30"`
  returns 0 on production (read-only SSH, 2026-11-04) and on the local snapshot.
  Post is `publish`.
- **Root cause**: the LiveCanvas "Global JavaScript Code" partial was never
  populated; it publishes no code, so nothing executes from it. Site-wide JS is
  served by plugins/theme assets instead.
- **Consequence**: template-matrix row 30 cannot satisfy the coverage
  contract's "Global JavaScript must prove code execution and a consumer
  behavior" clause while empty. Populate it with the real global JS, retire the
  partial, or record an owner ruling before claiming not-applicable. Recorded
  as `empty-content-local-and-production` in evidence/template-bindings.json.

## F3 — Spec-vs-code divergence: missing PDF returns 410, contract says 404

- **Symptom**: `GET /wp-content/uploads/fullmatrix-missing.pdf` → **410 Gone**
  (both local snapshot and the gate's unit tests).
- **Root cause**:
  `plugins/linker-commerce/includes/Products/Publication/DocumentAccess.php:98-108`
  denies unresolvable/unauthorized PDFs with `'status' => 410` — a deliberate,
  tested choice. The coverage contract (§permissions) instead says "缺失文件也
  404" ("missing files also 404").
- **Decision needed**: either update the contract text to the implemented 410
  semantics (410 arguably communicates "withdrawn document" accurately for a
  publication-gated archive) or change the deny status. Not changed in this
  batch (product code out of write scope).
- Related local-only note: missing **non-PDF** uploads (e.g. `.jpg`) on the
  local snapshot 301-redirect to the homepage via the router's WP fallback;
  production's Apache serves a plain 404 for those. Local-acceptance artifact
  only.

## F4 — Local snapshot false positive: CookieYes hidden preference markup forces horizontal scroll at 390 (NOT a production defect)

- **Symptom**: on the local snapshot instance, `/privacy-policy/` and
  `/refund-returns/` at 390 measure `scrollWidth` 528/467 vs viewport 390 while
  the consent banner is open; after "Reject" hidden CookieYes preference-center
  elements (`.cky-preference-content-wrapper`, `.cky-accordion-*`) still lay
  out ~795px wide.
- **Production evidence (read-only, twice)**: production EN/DE legal pages at
  390 measure banner 366px and `scrollWidth === 390` — clean. The WindPress
  tailwind caches are byte-identical local↔production (919,685 bytes, both
  contain the intended `body .cky-consent-container` rules), and the CookieYes
  `_ckyStyles` payload is identical too — so the divergence is a runtime
  difference in the local environment, not shipped CSS.
- **Impact**: local-instance UI acceptance runs will flag false 390 horizontal
  overflow on pages carrying the CookieYes preferences markup. Local-stack
  owners should treat CookieYes-caused overflow as an environment artifact, or
  fix the local runtime difference. Production needs no change.

## F5 — Transient overlap: Genie floating prompt can intercept clicks on /solution/commercial-storage/ stage tabs

- **Symptom**: in the page sweep, clicking stage tab `#cs-stage-tab-4` at 1440
  timed out: `.linker-genie-app__prompt` intercepted pointer events at the
  tab's auto-scrolled position.
- **Root cause / classification**: the floating Genie prompt overlaps the tab
  row at certain scroll positions; scrolling 120px further exposes the tab and
  the click succeeds (probe confirmed). Per the owner's overlay standard
  (locally covering but avoidable by normal scrolling = acceptable), this is an
  observation, not a blocking defect. Recorded so visual reviewers don't chase
  the automated failure.

## F6 — Harness-fact records (not defects, kept to prevent false re-flagging)

- Mobile/desktop capability carousel "Previous" button is intentionally
  `disabled` on the first slide; Playwright click timeouts on it are correct
  behavior, not a touch-target defect.
- Product-archive loop cards have no direct add-to-cart control by design; the
  add path is the PDP CTA (`/proforma-request/?add-to-cart=…`), owned by the
  `inquiry-native-entry` contract. The `product-archive:add-to-draft` rows are
  recorded as observations on that basis.
- `/de/loesungen/` is a 404; the DE twin of EN `/solution/` (page 746) is
  `/de/loesung/` (page 6871, Polylang pair). Earlier evidence captured against
  the invented URL was quarantined and re-captured on the real twin.

## F7 — /solution-configurator/ renders no visible H1 at rest (observation)

- **Symptom**: EN configurator page at both viewports: HTTP 200, `lang=en-US`,
  but no visible `<h1>` in the server-rendered document at read.
- **Context**: tool-app pages own their design (owner ruling 2026-10-10); the
  React app may introduce its own headings after mount. Recorded as a
  page-matrix finding on both viewport rows so the manual visual pass makes a
  deliberate call (keep as tool-design, or add an H1 for document outline).

## Clean signals (first-time evidence, no findings)

Across all page-sweep rows completed in this pass: **0 failed images, 0 console
errors, 0 page errors, 0 mojibake**, and no real horizontal overflow other than
the F4 local artifact. Overflow-flagged elements on marketing pages are
decorative off-canvas bleed with `scrollWidth === clientWidth` (clipped by
design).
