# Final fixed-main acceptance

Runtime/source: `90089f1177ad7132b11ab0b44851acab2ec127b5`. Fixed main: `2789721a37de66274a6b359050d706c3420d4f6e`. The final delivery adds evidence only; executable source is checked byte-identical. This is the validation cutoff for this handoff. Older acceptance directories retain their actual source pins.

The final rebase retains main's Genie inquiry-confirmation card, all native callbacks and front-end/build outputs, optional Sender summary argument, language-aware summary cache and verbatim customer note. Of 67 cumulative feature code/data/test files relative to the preceding accepted source 103a70ee, **65 are byte-identical**. The two summary files equal fixed main with only the already-reviewed `existing_id()` read-only form-context repair and corresponding unit fixture override. Entire linker-i18n, LC/WindPress, inquiry form, ticket email implementation and migration scripts are unchanged. [Source comparison](source-delta.json).

## Completed checks

- [just check](../checks/latest-just-check.log) and [just test](../checks/latest-just-test.log) passed on source 90089f11.
- Explicitly enabled c254 URL/title/discovery fixtures: **30 tests / 35,611 assertions, twice**; [run 1](integration-1.xml), [run 2](integration-2.xml).
- Native inquiry/reader fixtures: **24 tests / 197 assertions, twice**; [run 1](inquiry-reader-1.xml), [run 2](inquiry-reader-2.xml).
- All four acceptance runs have zero failures/errors/warnings/skips. Default skipped integration suites are not acceptance.
- [Full actual HTTP table](completion.md): **184 reviewed addresses, 97 changed addresses with first-hop 301 to their final path, 175 distinct canonical titles, zero defects**. [Machine-readable routes](route-results.json) also verify links/canonical/hreflang/share consumers and native sitemap sets: DE149 / EN148, English paths unchanged.
- [Final public CLI readback](migration-final-state.txt): dry run has zero pending changes, verify and native presentation check succeed. Repeat apply, first-backup protection, drift/conflict rejection, rollback/restoration, source save, `present` persistence and retired-bootstrap persistence are covered by the repeated fixtures.
- [Local mail and functional states](mail/) preserve native UTF-8/8bit bytes, tester-only one delivery, Outbox routing and front-end/staff/cron recipient-language links. Native reset keys, confirmation keys and logout nonce behavior remain valid. No production mail was sent.
- [Native catalog regeneration](catalog-preservation.json): 836 commerce, 443 tools and 28 preexisting i18n German translations all preserved; feature i18n has 50. Native make-json reproduces both published tools files. [Output](../checks/latest-catalog-regeneration.log).
- [Final instance state](instance-final-state.json): zero owned users/posts/orders; temporary MU instrumentation and test-mail override removed. SQL/cache activation agree and **77 original objects** remain backed up. The final guarded [empty-conversation readback](empty-conversation-final-state.json) contains zero owned empty threads.

The SQL-absent/cache-active failure and its narrow native-key repair retain their original red/green proof in the preceding [addendum](../rebase/README.md). The summary context read likewise retains its EN/DE red/green proof there. All previously failed attempts were rejected and remain in the private debug archive; none is counted as passing acceptance. The initial ghost-producing process is not proven.

## Actual current-source browser readback

Computer Use repeated inquiry and journal on source 90089f11 at EN/DE × 1440/390. [Observations](visual-readback.json) accompany eight actual PNGs. All fonts are loaded and pages have no horizontal overflow. The four consent rows use flex, 12px gap, normal 400 weight and zero margin. Both desktop topic rails measure **224px**, with **17px equal left/right selected-item insets**, one selected topic and a restrained `rgb(241,249,248)` surface. Mobile retains its filled current-topic pill. The same visual source uses the native WindPress generation at 2026-10-18 19:27:34 Asia/Shanghai / 645 kB. Temporary viewport/animation instrumentation was removed by resetting the viewport and returning to the German journal.

- [DE desktop journal](journal-de-1440.png), [DE mobile journal](journal-de-390.png).
- [EN desktop journal](journal-en-1440.png), [EN mobile journal](journal-en-390.png).
- [DE desktop inquiry](inquiry-de-1440.png), [DE mobile inquiry](inquiry-de-390.png).
- [EN desktop inquiry](inquiry-en-1440.png), [EN mobile inquiry](inquiry-en-390.png).

The strict [English pixel report](../pixel-results.json) remains honestly pinned to its actual main 1f271843/source aa552bdf whole-page captures: **18 unaffected EN comparisons, exactly zero changed pixels, no masks or tolerance**. Those captures are not relabelled as new fixed-main screenshots. Unchanged presentation source supports carrying that evidence forward; the inherited consent-weight correction belongs to the explicitly authorized inquiry redesign and appears in the fresh four-state readback. The full original product, service, inquiry states, reader/search/TOC and dashboard captures remain in the [change ledger](../change-ledger.md) and [prototype comparison](../prototype-comparison.md).

## Independent reviews and handoff

Both reviewers checked the complete cumulative fixed-main-to-source diff: **Spec 0 blockers / 0 unresolved; Standards 0 hard violations / 0 unresolved concrete issues / 0 new heuristics**. Two earlier nonblocking responsibility/repetition observations remain recorded. [Review record](../review.md), [current legacy absence](legacy-absence.json): no added executable legacy identifiers or feature engine/NLU changes. Final completed evidence is independently reconciled in the review record; CI is the exact final PR-head result, separate from local evidence.

[verification.json](verification.json) contains completed counts, timings, source pins and cleanup. The instance is **c254 http://127.0.0.1:9129**, snapshot 20261018-1043, taken 2026-10-18T02:52:16Z and loaded 02:54:26Z. Main checkout was not edited. No merge, deployment, production write or real mail was performed. Claude's [production runbook](../production.md) includes first-presentation backup export before the second present, dry run before data apply, native cache generation, readback and exact rollback order.
