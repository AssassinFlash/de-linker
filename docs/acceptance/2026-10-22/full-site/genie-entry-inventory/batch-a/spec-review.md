# Batch A — final independent Spec and visual review

Verdict: **PASS for the bounded Batch A implementation and its local rendered states.** No remaining actionable blocker was found in this scope. This is not a whole-site PASS, a production readback, or approval of the separate ordinary-failure / Installer desktop / project-brief work.

Reviewer: `/root/spec_review`. Review was read-only except for this report. No product source, shared browser state, production data, inquiry, email or microphone capture was changed by the reviewer.

## Exact reviewed state

The full Batch A source changes from baseline `4f722c26` were reviewed against the Batch A sections of `../repair-design.md`, the current user request for detailed EN/DE desktop/mobile inspection, and the repository's product and copy contracts. Library and the already reviewed native inquiry/history changes retain their separate conclusions.

| Artifact | Independently read-back SHA-256 |
| --- | --- |
| Final 20-product-source mapping aggregate | `38342862231861ddf57a6e8792c04e323e5cddbfaea66fc7f59907f2681a8fd1` |
| Adjacent source used by the complete 32-case browser matrix | `94d6c8fe960b59833ddee9f589ad23478ffb39bb1031aa51e60ef758b8244d0f` |
| `plugins/linker-commerce/content/windpress/account-links.css` | `2c55f55dcdbaef00f5b1379b61130732649e879ecdc293fd763d3fa4e0d24029` |
| `plugins/linker-commerce/content/windpress/control-details.css` | `e9bc143282f31f601a9db1ce1edfa71962b48f23c32d202bddf68ca291566831` |
| Final `plugins/linker-tools/build/manifest.json` | `56264733bd5a790a83b17d8ed65668201713d7a5ecfee2166c96e9cb158f58c4` |

The final source aggregate uses the documented SHA-256 of sorted, compact JSON mapping of the 20 file hashes in `source-hashes.json`.

All 20 current product-source hashes match that file. The final source differs from the adjacent reviewed source only in `App.tsx`: when browser dictation is supported, the duplicate plain paragraph “Dictate / Diktieren” is omitted. The explicit Dictate / Stop dictation action, `aria-pressed`, handler, unavailable-browser explanation and error feedback remain. Independently reversing only the exact `voice-presentation/App-only.diff` hunk restores the adjacent App SHA `a1da902024c4a5370ac07368c03330d305508f350e65b61bace16e13511f238b`. The other 19 product sources are unchanged. This is a presentation delta; it does not reopen the reviewed owner logic.

The final official WindPress compile is recorded by the parent as `1792617293`, `701525` bytes. Its two CSS source files above are unchanged from the complete 32-case run's final CSS. Generated bundles and i18n were rebuilt after the App delta; the manifest hash was independently read back.

## Source and consumer contracts

| Requirement | Conclusion and substantive checks |
| --- | --- |
| Marketing question reaches its real consumer | PASS. Binding is limited to the named residential/commercial editors and Installer mobile editor. Ordinary links and the resting homepage retain their entry behavior. Exact typed text is handed to the actual App; same-tick gestures are deduplicated. |
| Source, edits and files are not silently consumed | PASS. Accepted receipt follows durable write and exact readback. Blocked `ask` returns false and keeps the durable entry instead of sending a settled acknowledgement. A failed file remains an explicit refused item; after reload, file names require reselection or removal. Missing files cannot silently accompany a send as though bytes remained available. |
| Current browser identity owns recovery | PASS. Native scope is checked before private recovery bytes are painted, then refreshed after queued thread work before transport. Unavailable identity remains retryable without exposing the old question; confirmed mismatch removes only the matching old owner. A superseded late result cannot delete or unlock a new record. Native price/account permissions do not substitute for recovery ownership. |
| Async recovery preserves new work | PASS. App and actual Hero initialization, retry and explicit Restore check current input/version, files, omitted names and busy state after awaits. Old candidates are restored or atomically parked without overwriting new text/files or an occupied parked slot. Initial pending ownership blocks send/retry from overwriting the sole unresolved failure. |
| Closing an unavailable helper is operable | PASS. Native fallback provides title, Close and Retry before React CSS exists. Close/Escape cancel the delivery intent and retain the source/recovery record. Retry preserves the original opener. Late ready does not reopen or send a dismissed intent. Mobile role/inert/overflow and focus are restored; workspace has no Close or Escape-to-hidden behavior. |
| Keyboard belongs to the visible sheet | PASS. The actual helper mount includes the account row in its mobile boundary. Closed details descendants that native Tab cannot enter are excluded. Actual opener focus is restored. |
| Composer can display restored and long text | PASS. The callback-ref size hook measures the actual mounted node, opening/value/width/font changes, and cleans observers. It retains the six-line maximum and scrolls beyond it. Native Hero's separate two-line height is handled only on the expanded Hero. |
| Styles match real local surfaces | PASS. WindPress selectors target the explicit source editors, App controls, native boot error, and expanded Hero. They do not restyle the unopened Hero or change marketing body copy. Actual source IDs and actual focus/hover background states are used; absent `aria-disabled` is not treated as proof of enabled state. |
| EN/DE customer copy | PASS within A. Sie-form German, existing Genie identity and existing commerce terms are retained. Recovery text does not promise persisted attachment bytes. Unavailable/start-failed dictation messages preserve the type-your-question alternative. The final cleanup removes a duplicate word without introducing new copy. |

The source review included the final init-pending, external-entry acknowledgement, mismatch/superseded-owner, busy preparation and parked/failure restoration counterexamples. Their earlier P1 findings are closed for **entry-derived Batch A**. Ordinary unscoped legacy failure storage remains a separate open contract and is not covered by this PASS.

## Executed evidence and limits

The reviewer independently ran the real inline-loader PHP test suite: `EntriesTest`, **30 tests / 176 assertions passed**, including the actual captured PHP bootstrap executed in JSDOM for helper/workspace at 1440 and 390. The reviewer also independently ran the final supported/unsupported voice component cases: **2 passed**, with the other cases intentionally excluded by the narrow test filter. Earlier independent ownership counterexamples and full source review remain applicable because their implementation bytes did not change.

The implementer/parent records the complete final JS suite as **52 files / 451 tests passed**, and the final complete repository checks/tests as exit 0; these are their execution evidence, not executions claimed by this reviewer. Existing unrelated skips/expected failures remain disclosed in the parent package. A green command alone was not used as a visual verdict.

Browser evidence is deliberately a versioned combination:

| Run | Source | Coverage | Review use |
| --- | --- | --- | --- |
| [20261021T210303171Z](20261021T210303171Z/summary.json) | Adjacent `94d6c8fe…` | 32/32 actual local browser cases; 74 original PNGs and matching geometry | All 74 PNGs were individually opened and visually inspected. This closes boot, source controls, App/Hero text sizing, recovery layout, welcome scroll origin and empty-source-error styling. Its duplicate supported-voice paragraph is superseded by the final delta below. |
| [20261021T212024202Z](20261021T212024202Z/summary.json) | Final `38342862…` | 8/8 affected available/noSpeech cases, EN/DE × 1440/390; 24 original PNGs | All 24 PNGs were individually opened and visually inspected. Explicit voice action remains; duplicate paragraph is gone; unavailable explanation, conflict/reselection and retained text remain readable. |

The final 8 cases are affected-scope validation of a proved one-hunk presentation delta. They are **not** represented as a second complete 32-case run on the final source. Original image names, dimensions and digests are listed in each run's `images.json`; no contact sheet or transformed image was substituted for an original in this review.

### All original views inspected

Each family below includes every named locale, width and state in its run; every listed original was actually viewed. “PASS” refers to the A surface and state, with the global background-page limits below.

| Original family | 32-case run images | Final delta images | Visual conclusion |
| --- | ---: | ---: | --- |
| `residential-{en,de}-{1440,390}-{cold,answered}` | 8 | 0 | Source editor, 44px icons, actual question/answer, modal title and controls readable. |
| `commercial-{en,de}-{1440,390}-{cold,answered}` | 8 | 0 | Same; long German labels and source/consumer text visible. |
| `installer-{en,de}-390-{cold,answered}` | 4 | 0 | Mobile source controls and consumer layout pass. Scroll-framed top badge is not classified as a defect. |
| `draft-{en,de}-{1440,390}-{prepared,missing,voice-conflict}` | 12 | 12 | Refusal/reselection, remove controls, draft decisions and typed content remain readable. |
| `draft-{en,de}-{1440,390}-voice-unavailable` | 0 | 4 | Correct current-language explanation; retained draft and file-name recovery state are visible; unavailable voice action is absent. |
| `capabilities-{en,de}-{1440,390}-{prepared,eight-lines}` | 8 | 8 | Final images show one explicit voice action and complete welcome title; six visible text lines plus scrolling retain the eighth line. |
| `recovery-{en,de}-{1440,390}-boot-failed` | 4 | 0 | Native title, Close, Retry, error background and focus/keyboard affordances are usable. |
| `native-scope-{en,de}-after-logout` | 2 | 0 | Actual native-scope logout surface contains no prior private draft. Scope assertions supply the behavioral proof. |
| `home-recovery-{en,de}-{1440,390}-{outage,parked,restored}` | 12 | 0 | Error/recovery, full German two-line Hero input, nameplate wrapping/content inset and send arrow contrast pass. |
| `bootstrap-{en,de}-{1440,390}-{helper-failed,safe-reopen,new-intent,workspace-failed}` | 16 | 0 | Long German fallback title, focus, old/new questions and decisions readable. Accepted source error no longer leaves an empty pink bar. |
| **Total original PNGs viewed** | **74** | **24** | **98 originals; no outstanding A visual blocker.** |

The original geometry supports, rather than replaces, the image inspection:

- Complete run: 178 source-control observations and 16 attachment-remove observations have minimum 44×44; 144 prompt-action observations have minimum height 44. App height checks cover 40 visible fields, including four 144px-client / 192px-scroll / `overflow:auto` eight-line fields.
- Hero: 12 field observations show full fixture content, minimum client height 62; nameplate controls stay inside the actual content box. Actual dark-on-gray and white-on-deep-teal send/SVG states have minimum contrast 13.4756 in this run.
- Welcome: 30 complete-run observations preserve the title's scroll origin; 10 overfull welcome boxes scroll from the top. [Actual consumer scroll readback](20261021T210303171Z/welcome-scroll-readback.json) reaches the final 44px suggestion entirely inside the welcome viewport. Natural content cropping inside an operable scroller is distinguished from the fixed negative start that was repaired.
- Final voice delta: 168 target observations retain minimum 44×44; all 24 welcome-title and composer observations pass, including four eight-line scrolling fields. The reviewed screenshots show the corresponding readable result.

The [native DE390 screenshot](voice-presentation/native-de-390-open.png) and its DOM/escape readbacks were also inspected: one visible helper, composer focus, one `Diktieren` action and zero duplicate paragraphs; Escape returns to the native Spracheingabe opener. This proves the native entry UI. It does not prove physical speech capture, microphone permission, acoustic recognition quality or a model response.

## Known boundaries that remain open for the full-site goal

- Residential/commercial transparent photo headers retain low-contrast EN/DE language links. This is a separate global visual finding, not fixed or accepted by Batch A. The background marketing pages therefore do not receive a whole-page visual PASS from this report.
- Installer DE390's badge initially looked hidden in a source-input capture. The parent's actual `scrollY=0` CUA/DOM readback in `../../marketing-layout/installer-de-390-scroll-zero.{png,json}` proves header 0..81 and badge 199..213: the earlier frame was naturally scrolled. That DE suspicion is closed diagnostically; it is not evidence of an EN implementation change.
- Installer desktop planning inputs/project brief, Saved Solutions and downstream inquiry consumers are explicitly Batch B. They remain open in the full-site contract. Ordinary legacy unscoped failure ownership is separately pending.
- Browser model/history/SpeechRecognition fixtures have the boundaries stated in the run summaries. These results do not validate generated technical facts, actual dictation capture, all products, real inquiry/email delivery, the entire route/state matrix, or production deployment.
- The current batch does not edit the legal/privacy body. Its PASS does not replace the separate legal backup, content-preservation, printing, replay or production acceptance evidence.

Older automatic green runs with identified visual defects remain diagnostic history. In particular, `20261021T205430972Z` does not become visually passed retroactively. This verdict is tied to the exact final source/CSS hashes and the explicit 32-plus-8 evidence above.
