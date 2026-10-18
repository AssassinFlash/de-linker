# Full-diff reviews

Fixed point: `c2106969d19be6797107fa50b35d4c8a58ad5d5f`; initial reviewed head `2f0ad8a571db688010ffb551f17e5139368ead9f`. Two independent reviewers inspected `git diff <fixed-point>...HEAD`, including both implementation commits. Standards sources: AGENTS.md, CONTEXT.md and kickoff “通用规则”; Spec sources: issue #254, the approved plan and `docs/specs/254-german-urls.md`.

## Standards

0 documented violations; 1 non-blocking judgement call. Possible Feature Envy: the route-history methods call `GermanUrlMigration::old_url()` only to preserve the request query, creating a small ownership cycle. The function is the shared native history filter and its observed behavior is covered; no behavior change is required for this heuristic.

The reviewer confirmed approved terminology, LC/WindPress ownership of presentation, native WordPress/Polylang/Woo mechanisms, `present` ownership of repository templates, and no added executable legacy callback dependency. Legacy identifier matches are migrated data/meta, cleanup/removal hooks or pre-existing material. Engine/NLU paths are unchanged.

## Spec

1 medium finding: the first-run preflight checked slugs but could replace an independently edited curated title, SEO title or category name. The approved plan requires a value other than the reviewed old/new value to fail before writing. Resolved with the seven-object `german-titles.json` manifest and first-run preflight for post titles, SEO titles and category names. The new public CLI regression first failed because dry run accepted a manual post title (exit 0), then passed for all three field types in both dry run/apply without a backup or earlier data write. It also covers resuming a reviewed new post title with its old SEO value.

The reviewer found no unrequested scope. The inquiry redesign is owner-authorized; mail language, endpoint aliases, slug preservation, existing redirect entry and `present` pairing support the plan. All 184 target routes translate descriptive English; retained brand/model/technical tokens match the explicit inventory. Reviewed German copy is appropriate, including established loanwords in preserved rich titles.

Initial worst finding per axis: Standards — minor ownership heuristic; Spec — first-run title drift. Final acceptance evidence and follow-up review are appended once complete.

## Follow-up at 092c15d5

Both reviewers re-read the full diff after the fix. Standards: **0 hard violations, 0 new concrete smells**; the earlier non-blocking ownership heuristic remains. Spec: **the first-run drift finding is resolved, with no new concrete code-level finding**. The reviewer confirmed all seven old/new field sets, pre-write validation and partial SEO resumption. Both reviewers kept route/visual evidence as a separate pending acceptance gate and performed no instance mutations.

## Metadata follow-up at 0a9bce66

Computer Use exposed a real final-markup defect: SEOPress passes complete canonical/Open Graph tags, while the first implementation returned a bare URL. The HTTP regression failed, then passed after switching to WordPress's native tag processor. Both reviewers re-read the full pinned diff: Standards **0 hard violations, 0 new concrete smells**; Spec **0 remaining concrete code findings**. The existing small ownership heuristic remains non-blocking. The subsequently strengthened route report confirms both metadata tags and zero defects.

## Final scope and prototype review at 0eea4005

Both reviewers read the full cumulative diff after the owner's final approval of the compatibility group plus the related proportions, type hierarchy, auxiliary controls and document density. Standards: **0 hard violations, 0 new concrete heuristics**. Spec: **0 concrete remaining implementation findings**. The earlier small ownership heuristic remains non-blocking.

The reviewers verified the actual prototype branch/commit, variant A selection, and the absence of a compatibility group in that prototype. The final stylesheet retains A's 1360px container, section spacing, upper-grid sticky boundary and mobile glass pill. All increments remain WindPress presentation; native product facts, copy, links, actions and focus remain intact. The document-grid regression no longer freezes an obsolete column expression, while retaining protection against fixed-pixel tracks.

The remaining minor screenshot-reference path correction was applied. Final screenshot/pixel/JUnit results are recorded separately in the acceptance report; reviews alone are not treated as passing those gates. No reviewer mutated files, browser state or any instance.

## Journal / reader and final detail review at 3709e287

Both independent reviewers re-read the entire cumulative `c2106969…3709e287` diff, including the owner's content-platform, mobile discovery, reading and card/share requests.

**Standards:** 0 documented violations. LC owns card/reader composition and native queries/sharing; WindPress owns all design. The script only derives accessible sharing names from native platform labels. The single-line DOM `textContent` sniff exception identifies the native API. No PHP layout or new executable legacy dependency was introduced. Two non-blocking judgement calls remain: the earlier route/migration query-preservation responsibility cycle, and repeated common navigation/search/card markup across per-face LC exports and their German twins. Neither is an observed behavioral defect.

**Spec:** 0 remaining code-level blockers. Desktop double-column cards, full images, category/title/date hierarchy, compact mobile rows and equal sharing targets match the direct owner feedback. Native destinations and original body content remain. The service mobile implicit grid fix remains in place. Native chapter mapping, related-post data and localized search continue through their existing interfaces.

The reviewers performed no instance mutations and explicitly kept final visual/repeated-fixture/CI verification separate. Those results are recorded in verification.json and the current JUnit/capture reports.

## Final short-copy / dashboard review at b5b10edb

Both independent reviewers confirmed the entire cumulative `c2106969…b5b10edb0b7e48dc7d8913c8f8b2599f0b1cb026` source diff. Standards: **0 hard issues, 0 new judgement suggestions**; the two existing non-blocking heuristics remain. Spec: **0 remaining blockers**. The five adversarial copy corrections were all incorporated, and all ten bilingual label pairs were assessed as accurate and natural.

They independently checked the installed LC/Tangible `add_field_filter` contract and the exact current-item/null-return behavior. The native field supplies escaped text only; unknown/changed posts retain their native title. Full native H1, SEO, prose and URL remain unchanged. Existing strict mock fixtures now acknowledge the native init registration and their lack of Polylang source data. The HTTP test independently checks different cards in both languages plus full reader/document headings. No reviewer changed files or instance state. Final images, repeated full fixtures and CI remain separate evidence.

## Final sidebar and stored-title review at 793ff8f1

Both independent reviewers confirmed the full cumulative `c2106969…793ff8f16e8fb1272e98c1b00b8380146f5db37e` source diff. **Spec: 0 remaining blockers. Standards: 0 hard issues and 0 new judgement suggestions.** The two previously recorded non-blocking responsibility/repetition heuristics remain.

The sidebar fixes constrain native grid tracks and restore equal insets without changing topic destinations or selection semantics. Actual EN/DE index and native category-click observations separately measured 17px on each side. The final copy guard compares the reviewed manifest against raw `$post->post_title`, preventing entity formatting of C&I from selecting the full-title fallback. Unknown or edited posts still use the filtered native title. The new EN/DE HTTP assertions cover the observed defect and retain full reader/browser-title checks; no database title is overwritten.

Reviewers performed no instance mutations. The current-source repeated fixtures, pixel reports and CI are separate acceptance gates, recorded in verification.json and the PR checks.

## Mail evidence follow-up at 278704ce

Both reviewers confirmed the cumulative `c2106969…278704ce84977ab5048923e7a9fcf924468479a9` source diff: **Spec 0 blockers; Standards 0 hard issues and 0 new judgement suggestions.** A final artifact check exposed redundant quoted-printable decoding of a native UTF-8/8bit local message. The test now preserves the original bytes and asserts the transfer-encoding header and valid UTF-8 before storing evidence. Existing tester-only, one-delivery, localized-link and restored-language assertions remain. Runtime and visual implementation are unchanged from 793ff8f1. Repeated current-source fixtures and CI remain independent gates.

## Final rebase review at aa552bdf

Both independent reviewers re-read the cumulative `1f271843c0e65d0cbdc59f52fd8be120211be87b…aa552bdf3ba4423ff34d032e116dadb1af8fd615` diff after upstream Genie attachment work landed. **Spec: 0 implementation blockers. Standards: 0 hard issues and 0 new judgement suggestions.** The 63 feature code/data/test files were independently verified byte-identical to the pre-rebase source; upstream changes were retained. The two earlier non-blocking heuristics remain.

Reviewers required fresh provenance rather than relabelling old evidence. All 28 latest-main baseline frames and 56 final frames were newly captured; all 10 native-action/layout records, 12 reader/search states and 4 product readbacks were repeated on aa552bdf. The final source was restored byte-for-byte after baseline capture, and the restored compiled CSS equals the final-capture CSS. Recomputed English strict comparisons remain 18 × 0 changed pixels, no masks/tolerance. Current-source root checks passed; the complete repeated fixtures and CI are recorded separately when complete. Legacy absence was regenerated against the new fixed point. No reviewer changed an instance.
