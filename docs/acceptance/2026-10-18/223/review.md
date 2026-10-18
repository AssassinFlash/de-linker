# Full source diff review

Fixed point: `0fddf100c267581dd8d3e781fa498b5d1471bf47` (origin/main).
Scope: `git diff <fixed-point>...HEAD`, then the working corrections to those files.
Two independent read-only agents followed the code-review skill; evidence files
were generated separately and their runtime results are listed in README.md.

## Standards

Initial findings: two documentation gaps — the four narrow shortcodes needed
per-item LC/Woo native-capability evidence; new footer thresholds needed source
comments. Both corrected. Spec §8 records the installed LC implementation and
Woo APIs; CSS comments point to unchanged LC footer rules. Follow-up review:
no remaining actionable Standards finding. PHP remains data, LC owns markup,
WindPress owns style. New entry copy follows the recorded EN/DE terms.

## Spec

Initial findings: filled-draft price cells lacked registration; the existing
draft summary offered registration to pending accounts / with Woo registration
closed; comparison text ran into its new link. All corrected through the shared
availability adapter, LC fragments and WindPress spacing. Follow-up review:
no remaining actionable source Spec finding. Real-browser tests additionally
cover every filled-draft cell, actual endpoint clicks and family model switching.

## Legacy channel check

`checks/legacy-added-lines.log` is empty: no newly introduced `tv_b2b_`,
`Linker_AI_` or `dlk-` identifiers. The header's existing hyphenated selectors
are retained to extend its current LC markup. Header `fit()` is unchanged;
no account processing, permission, model, translation synchronizer or engine
implementation is copied or replaced.

Source Standards: 0 remaining findings. Source Spec: 0 remaining findings.
The outstanding strict live pixel gate is explicitly **未完成**, independent
of these source-review conclusions.

## Final rebase and owner visual follow-up review

Two independent read-only code-review agents reviewed all 46 source files from
`0fddf100` through `c24326c3`, then the focused working changes to
`account-links.css` and `account-entries.spec.ts`. Standards: no actionable
violations or smells. Spec: one follow-up finding, the draft's padding override
lost to `#tv-storefront-cart .sf-cart-btn`; corrected by adding that root to the
new selector. Follow-up Spec: no remaining source findings.

The user rejected the dock's appearance after the scrim repair. The final
WindPress correction refers to the recorded OpenAI dossier A2/A4/A5/B4: top
account pills, regular 24/28 welcome heading, a joined welcome/composer group,
compact toolbar, and one outer sheet radius. Existing words, four controls,
conversation/model protocol and permissions remain intact. Reviewers explicitly
distinguished source review from final rendered acceptance.

Both agents reviewed the final clarified footer correction as well: no new
Spec or Standards finding. The welcome area flexes; composer, disclosure and
support links finish at the sheet bottom. The regression assertion checks the
reported bottom gap, replacing the intermediate initial-group preference.

The final owner-requested footer composition was independently reviewed:
`HelperFooter` keeps a visible short AI identity and puts full disclosure and
existing localized support links in native details. Spec source findings0;
new EN/DE copy independently approved (see copy-review.md). Translation
JSON/MO generation and actual German browser readback are separate evidence.

## Expanded frontend reply design review

Both independent reviewers examined the complete source diff and the new reply
presentation. Standards: zero actionable issues. Spec found three frontend
problems: long reply auto-scroll conflicted with goal9, completed reveal replayed
on reopen/history, and index keys let Copied state leak between different
answers. All three were corrected and independently rechecked with no remaining
source findings. Pending/new-question positioning is now distinct from restored
history; long answers never auto-scroll to the end. An explicit jump settles
after the disappearing button's layout update. Five new copy pairs were reviewed
independently, and the manual-copy failure sentence was revised accordingly.

Later rendered inspection measured dense 14px single-paragraph prose. The owner
requested typography refinement: 16px/26px dock body and visual sentence groups
for long plain prose, preserving original words/canonical requests/clipboard.
The existing Markdown/structured block shapes remain intact. Tests and screenshots
are separate runtime evidence, not implied by these source-review conclusions.

Focused follow-up on final typography: Standards found no actionable issue.
Spec confirmed words/canonical data unchanged and identified two narrow gaps:
DE fixture needed an explicit de locale, and the post-layout RAF must only run
for an explicit jump. Both are corrected. Restored history starts at the beginning;
new-question positioning performs no deferred scroll into a fast complete answer.
The anchored full-response control is exercised by actual pointer clicks and a
stable-coordinate assertion during body growth.

## Review round 2 — full source, 2026-10-18

Fixed point 4cf49363; source head e990377542a2394e230f17cc178eb5eb43d6f2c9.
Both independent reviewers read the complete source diff, not only the repair
commit. **Spec: 0 actionable implementation findings. Standards: 0 actionable
findings.** They checked the independent controls band, composer separation,
last-paragraph and focus tests, narrowed comparison/mobile declarations, public
inquiry and updated empty-state tests, both inquiry-email return paths, LC DOM
order before the React root, retained #236 attachment flow, and absence of
backend/model/transport changes. New-line legacy identifier scan was clean.

Both reviewers explicitly left final screenshot/pixel and completion-table
acceptance pending for this session to assess; source review alone is not a
pixel-gate pass. The final recapture is pixels-review2/; historical failing
folders remain available as before evidence.

## Final rebase and reply-preservation addendum

Fixed point `2789721a37de66274a6b359050d706c3420d4f6e`. Both reviewers
rechecked the full source through `e5c190b3`: Spec 0 actionable, Standards 0
actionable. The rebase retains #236 uploads/busy-send and #250 inquiry cards
inside Transcript. A subsequent PO reference correction (`e4ecc95d`) makes the
existing “Netzanschluss” entry load in the Genie script as well as Configurator;
actual browser readback verified the German label.

Real Computer Use then exposed a separate cause of lost reply structure:
WordPress removed SSE JSON backslashes when saving post meta. Both reviewers
independently examined `e4ecc95d..be07829d`: Spec 0 actionable, Standards 0
actionable. `wp_slash()` is paired with WordPress's own storage unslashing for
messages and raw stream, preserving the already received reply. It changes PHP
persistence escaping; answer generation/model/tools/protocol remain unchanged.
The public GET round-trip fixture covers Markdown newlines, Unicode, quotes
and literal backslashes. Old stored histories are not migrated or guessed.


## Final owner corrections and formatting-authorisation review

Final source base `05a3fbc1` (main deployment-tooling merges), source head
`160623c9` (format contract27a128ab plus native-scroll browser fixture). Earlier source
reviews covered the full diff against `c7b70232`; the base-only rebase changes
no storefront/Genie behavior.

### Standards

Independent reviewer: **0 actionable source findings**. The prompts append
formatting only and retain prior factual, grounding, exact-wording and short
answer rules. Model/routing/tools/API/permissions stay intact. Ask retains the
original options and onAsk payload, with styles exclusively in WindPress and
no PHP layout. Native lazy/srcset decoding does not alter images or relax RGB
or dimension checks. The new two copy pairs are now recorded in copy-review.md.
No judgement smell justifies further refactoring; added legacy identifiers:0.

### Spec

Independent reviewer initially found a real dead dock selector (`--dock` was
not an emitted root class). Fixed to the actual non-workspace root; official
WindPress recompilation and Computer Use screenshots confirm single-column
choices at1440/390. Final narrow confirmation: **0 remaining actionable source
findings**. The last prose line and the taller option group are each fully
reachable by native scrolling; both reader bounds remain asserted, followed by
an explicit jump where needed. This preserves the composer-occlusion test.
Actual EN/DE model replies use headings/lists and match after reopening.

Remaining delivery limitation is explicit: hero inline conversation wiring is
**未完成 within223**, without a new ticket or invented completion claim. Source
review is separate from final browser/pixel/check/CI evidence.

Standards:0 findings. Spec:0 remaining implementation findings; hero inline
scope remains unfinished. See README for the complete acceptance table.
