# Current production and Genie integration — #533 / #563

## Source boundary

The live WordPress atomic manifest observed on 22 October 2026 was `20261022T122802818764Z-af41f307` (archived), source `af41f307091fb3a72246d12cf726223878139caf`. Main incorporates that release at `340a11a9`. Its existing public-intake safeguards derive from `003cedd3`; that protection revision is not the whole-site revision.

The earlier WordPress deployment guard expected the old manifest and stopped before `steps.deploy` or any production write. Publishing the isolated Genie source would have replaced newer visual/contact work. This integration instead merges reviewed Genie PR #566 (`033b74a6`) onto main `340a11a9`, producing source merge `16a8052f` without conflicts or manual runtime edits.

[Source composition](source-composition.json) compares both parents against the chosen source comparison baseline `1f054757` (the actual merge-base of the two current parents is `003cedd3`). The 40 runtime/test files changed on current main and the 32 changed in the Genie branch do not overlap. All 72 final files match their corresponding parent exactly. The deployment-tool delta is empty. Main then advanced to `3bb95556` through reviewed navigation/image-loading PR #567 (functional `a975b7ca`). It was merged without conflicts at `fb5da4b3`; the proof above has been recomputed against this newer main and preserves its lazy-loading, focus, mobile CTA and print changes. At this point the other chat owns the next WordPress publication window; its resulting manifest is still required before this integration may publish. This proves source preservation, not combined execution, visual parity, CI or production acceptance.

## Existing execution evidence

The [Genie acceptance](../563/README.md) records the independent full-diff Spec and Standards passes at functional head `252f331b`, all native/unit/static checks, and the final eight-cell built workspace/Hero × EN/DE × desktop/mobile matrix. Its native completion/recovery path uses local provider stubs; each Retry adds zero turn POSTs or provider calls. That earlier source/instance evidence does not become a combined-site or live result merely because this merge is conflict-free.

Genie backend source `252f331b` was atomically activated separately at 13:32 UTC on 22 October 2026. Readiness returned HTTP 200 after 2.099 seconds; engine, judge and TLS processes were unchanged. The previous release is retained for rollback. This backend health check made no paid model call or mail attempt. WordPress was still on the newer visual/contact release at the time this document was written.

## Publication contract

Combined CI, native relevant checks, local browser checks and independent review must precede WordPress publication. The two active website chats have explicit owner permission to coordinate versions and publication windows. The current atomic publisher stages to a shared directory; the chats must serialize publication and verify the latest manifest again immediately before writing. A changed manifest requires re-integration rather than bypassing the guard.

The normal deployment makes a fresh local database snapshot, retains the prior code release and requires native WindPress compilation and final readback. Rollback restores the preceding atomic WordPress release; the backend has its independent prior symlink. No schema migration or existing inquiry deletion is part of this integration. Administrator MFA enrollment, aggregate intake/mail capacity and public-registration capacity remain separate, unshipped work. No production test mail is authorized by this integration.

## Combined native acceptance at cf7c8471

The final integration checkout uses a fresh 22 October 14:04 UTC snapshot (`20261022-2159`) in its own instance `si533` on port 9341. Published product and attachment counts match the snapshot (212 / 2756); attachment files are complete. Native `present` installed the current bilingual templates, the actual WindPress administration page compiled the cache, and a second `present` readback confirmed its freshness and required classes. The account was then logged out through the native logout link for guest acceptance.

Real native checks on this combination pass: Contact selection, public submission, form mount and bilingual navigation, **18 tests / 588 assertions**; enforced Genie permit → actual Proxy → Thread → Ledger/Replies → owned GET completion lifecycle, **4 tests / 135 assertions**. The existing unrelated source suites are independently covered by CI.

The browser loads the committed Genie and Hero assets of the reviewed functional source. A guarded local-only MU fixture uses the existing SDK/siteverify and `pre_http_request` provider seams, with no REST route replacement. It aligns the synthetic document URLs to this instance. Native admission, server completion and reply storage run before `rest_post_dispatch` turns each successful response into a synthetic browser 502. Explicit Retry reads the owned completed Thread and returns the answer without another turn POST or provider-stub call.

| Surface | Language / actual configured viewport | Before Retry POST / stub | After Retry POST / stub | Images |
|---|---|---|---|---|
| workspace | EN / 1440 × 1000 | 3 / 3 | 3 / 3 | [failure](native-cf7/workspace-en-1440-failed.png), [recovered](native-cf7/workspace-en-1440-recovered.png) |
| workspace | EN / 390 × 844 | 4 / 4 | 4 / 4 | [failure](native-cf7/workspace-en-390-failed.png), [recovered](native-cf7/workspace-en-390-recovered.png) |
| workspace | DE / 390 × 844 | 5 / 5 | 5 / 5 | [failure](native-cf7/workspace-de-390-failed.png), [recovered](native-cf7/workspace-de-390-recovered.png) |
| workspace | DE / 1440 × 1000 | 6 / 6 | 6 / 6 | [failure](native-cf7/workspace-de-1440-failed.png), [recovered](native-cf7/workspace-de-1440-recovered.png) |
| hero | DE / 1440 × 1000 | 7 / 7 | 7 / 7 | [failure](native-cf7/hero-de-1440-failed.png), [recovered](native-cf7/hero-de-1440-recovered.png) |
| hero | DE / 390 × 844 | 8 / 8 | 8 / 8 | [failure](native-cf7/hero-de-390-failed.png), [recovered](native-cf7/hero-de-390-recovered.png) |
| hero | EN / 390 × 844 | 9 / 9 | 9 / 9 | [failure](native-cf7/hero-en-390-failed.png), [recovered](native-cf7/hero-en-390-recovered.png) |
| hero | EN / 1440 × 1000 | 10 / 10 | 10 / 10 | [failure](native-cf7/hero-en-1440-failed.png), [recovered](native-cf7/hero-en-1440-recovered.png) |

[Counts, dimensions, cleanup and image SHA-256](native-cf7/evidence.json) record **ten unique native operations**: one normal seed, one separate preflight completion and the final eight completed matrix turns. All eight Retry actions add **zero** POSTs or provider calls. The initial preflight used the prior fixture's document URL and remains private, separate from these eight correctly aligned rows. A requested-product phrase in that preflight does not determine the fixed synthetic response; none of this is a live model relevance test. The matrix uses one guest identity and the growing native conversation; it does not rotate identities or reset quotas.

DOM viewport reads are 1440×1000 or 390×844, with document scroll widths 1425 or 375. The actual 16 PNGs are **1425×990 or 375×812**, rather than the configured viewport dimensions. Native transcript/outer-page scroll positions differ: some captures show part of the current card or history, while the visible DOM and native response contain the complete localized card, actions and document links. Existing history retains its original language when the surrounding site language changes. No card, inquiry, email or feedback action was invoked. Root inspected all sixteen captures as a contact sheet and the desktop result at full size; these are functional state captures, not a new pixel-parity claim for every page.

One rapid Playwright Send action after switching desktop to mobile produced no POST and left the input in place. A subsequent native AX button action submitted normally. The cause is not established, and no speculative source patch or automatic resend was made. The normal final matrix uses fresh UI state before submission. The other page chat has a separate immediate-after-language-switch menu observation; a common cause has not been established.

The local fixture is removed. Native CLI reads protection mode `off`, no service-token constant, and the instance's local service URLs; local mail capture files remain zero. The synthetic Thread, completed ledger and replies remain under normal retention. No quota or journal is reset; the viewport override is reset and the temporary local browser tab is closed.

## Review and CI at the functional integration head

Independent full-diff Spec and Standards reviews of `3bb95556…cf7c8471` both pass. Both independently verify all 72 parent-file hashes and the relevant runtime boundaries. The Spec reviewer identified the inaccurate earlier phrase “shared base”; the wording above now accurately calls `1f054757` a chosen comparison baseline. No runtime change is needed.

CI [39792269179](https://github.com/AssassinFlash/de-linker/actions/runs/39792269179) is completed **success** for functional integration head `cf7c8471`: all checks/tests, native smoke and build reproducibility pass. This following commit adds only this evidence and the wording correction. Its own CI, PR merge, production window and final live readback remain separate gates. The production navigation release is now `20261022T140915063117Z-a975b7ca`; a subsequent deployment must verify that exact latest archived manifest, preserve any further page-chat changes and wait for that chat to release the performance-readback window. No WordPress publication is claimed here.
