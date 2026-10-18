# Current-main integration addendum

Runtime/source: `103a70ee4b2c68065e9d83a6fac583545583bdbd`. Fixed main: `4cf4936355f93c8b1ca38747985c7373873b7b31`. Final delivery may add evidence only; verification checks that executable source remains byte-identical.

PR #316 was first opened at 6a9e397a. Main then accepted the pending-account, inquiry-summary, consent, presentation-publication and deployment/autoload fixes. GitHub reported conflicts and withheld PR workflows until rebasing. The final integration retains all of these changes, including native `present --allow-stale` and the after-present OPcache reset. The additional deploy fixture uses the existing target boundary and rejects publication without the native flag. [Source comparison](source-delta.json) distinguishes inherited changes and feature repairs.

Of the original 63 feature code/data/test files, **59 are byte-identical**. `Form.php` retains upstream's summary note/message wiring; `auth.css` retains the account-status selector and normal consent font weight alongside the authorized inquiry redesign. The other two differences are the migration activation cache repair and its regression described below. Journal/product/service visual source remains unchanged. [Catalog preservation](catalog-preservation.json): native extraction/regeneration and make-json match the published active translations; all current-main German strings are preserved. The retired English source “Prices after approval” retains its prior German as an obsolete PO entry.

## Observed failures and narrow repairs

The native inquiry fixtures exposed a form read that opened an empty conversation and wrote cookies after output. Two EN/DE HTTP assertions first failed by observing newly created records. `InquirySummary::answer()` now uses native `existing_id()` for an unspecified context; it preserves existing valid visitor/customer conversations and explicit IDs without creating one merely to render a form. Queries use native `cache_results: false` because HTTP runs in another process. [Red record](summary-read-red.xml), [red output](../checks/summary-read-red.log), [first green output](../checks/summary-read-green.log). The native suite passed without output buffering, warning suppression or disabling summaries. Thirteen exact, empty local fixture/page-view conversations were privately backed up and removed with empty-content/native-opening-metadata guards; populated or existing-user conversations were preserved. [Cleanup](empty-conversation-cleanup.json).

A subsequent repeated URL run exposed an independent option-cache inconsistency: SQL had no ACTIVE row but its individual nonautoloaded cache held `'1'`. Native `delete_option()` returns early for an absent row, leaving that cache; `update_option()` trusts the ghost value and can skip insertion. This explains all four rejected assertions, including the bootstrap importer reading SQL while HTTP read the cache. The originating process is **not proven** and is not attributed to concurrent checks. [Exact public-command diagnostic](activation-diagnosis.json).

Both apply and rollback now invalidate only their own ACTIVE option key at entry, through native `wp_cache_delete()`, before preflight/native writes. Dry run is unchanged; no Redis database or another instance is cleared. A public CLI/HTTP regression injects precisely the observed state twice: rollback must restore old-address HTTP 200, and apply must persist SQL activation and return 301 with successful verify. [Red JUnit](activation-red.xml) / [red output](../checks/activation-red.log): **1 test / 17 assertions**, failed on the surviving `'1'`. [Targeted green JUnit](activation-green.xml) / [green output](../checks/activation-green.log): **5 tests / 177 assertions**, covering the new case and all four previously failing scenarios.

The first evidence-only rerun also had four failures caused by a missing optional output directory. That attempt was rejected, the directory was created and the unchanged commands were rerun. All rejected attempts and their complete logs remain in the private local debug archive; none is counted as passing acceptance.

## Verification and reviews

[Root check output](../checks/rebased-just-check.log) and [root test output](../checks/rebased-just-test.log) are successful runs on the final executable source. The two explicitly enabled URL/title runs and the two inquiry/reader runs are separately recorded in this directory; [verification.json](verification.json) is the authority for completed counts, timestamps and final readback. Default skipped integration suites do not substitute for these records.

Both independent reviewers inspected the full cumulative main-to-source diff and the final cache regression. **Spec: 0 blockers / 0 unresolved findings. Standards: 0 hard violations / 0 unresolved concrete issues / 0 new heuristic suggestions.** The two earlier nonblocking responsibility/repetition observations remain recorded. [Current legacy absence scan](legacy-absence.json): zero added executable legacy identifiers and no feature changes to engine/NLU code. Reviewers were read-only and did not certify unfinished tests on this session's behalf.

## Actual browser readback

Computer Use repeated inquiry and journal at EN/DE × 1440/390 on source 103a70ee. The last native WindPress generation remains **2026-10-18 19:27:34 Asia/Shanghai / 645 kB**, with the same visual source. [Actual observations](visual-readback.json) contain all eight captures: fonts loaded and no page overflow; four consent rows use flex, **12px gap, 400 weight, zero margin**; both desktop rails measure **224px** with **17px equal selected-item insets**, one selected topic and `rgb(241,249,248)` tint. Mobile uses the approved filled topic pill. Temporary viewport/animation instrumentation was removed by resetting the viewport and navigating back to the German journal.

- [German desktop journal](journal-de-1440.png), [German mobile journal](journal-de-390.png).
- [English desktop journal](journal-en-1440.png), [English mobile journal](journal-en-390.png).
- [German desktop inquiry](inquiry-de-1440.png), [German mobile inquiry](inquiry-de-390.png).
- [English desktop inquiry](inquiry-en-1440.png), [English mobile inquiry](inquiry-en-390.png).

The original strict pixel report retains its actual **main 1f271843 / source aa552bdf** captures: **18 unaffected EN whole-page comparisons, zero changed pixels, no mask or tolerance**. Older captures are not relabelled as current-main captures. The unchanged visual source supports carrying those comparisons forward; the inherited consent weight correction is part of the explicitly authorized inquiry redesign and appears in fresh four-state screenshots. The approved change ledger governs the redesigned EN/DE surfaces.

Claude's [production runbook](../production.md) includes the deployment's native publication/cache sequence, the first-presentation backup exported locally before a second present can overwrite it, dry run before migration apply, verification and exact rollback order. This implementation session used c254 only and performed no merge, deployment, production write or real mail delivery.
