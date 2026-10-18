# Public seams and red/green record

The user confirmed two seams: public shortcode/page output, and real browser actions/rendering. They also confirmed coverage of password recovery, private-document denial and Genie, preserving ownership checks.

1. `AccountLinksTest::test_guest_gets_a_direct_create_account_link`: red with missing `AccountLinks` class; green after adding an LC fragment populated with the native registration URL (1 test / 3 assertions).
2. `test_guest_entry_group_uses_german_account_addresses`: red with missing `guest_links()`; green with the German native account and endpoint addresses (2 tests / 5 assertions).
3. Comparator CLI: declared-region fixture initially failed for the permitted pixel and lacked an outside-region count. After implementation both the permitted pixel and the escaping pixel have the expected results; the original exact-RGB/dimension fixtures still pass.
4. `test_footer_exposes_two_independent_account_destinations`: red with missing `footer()`; green after adding the LC tile and its data. Visitor/registration-setting tests also pass (5 tests / 12 assertions).
5. Browser header tracer: `checks/header-red.log` records a real 1440px guest page with no registration entry in the account dropdown.
6. Inquiry and password recovery: actual missing-entry browser failures (`inquiry-red.log`, `lost-red.log`) followed by passing localized endpoint clicks in `entries-report.json`.
7. Product detail and private document: `product-red.log` and `document-red.log` show the missing entries. Document output retains the HTTP 403 and original-account message; the real local guest and separate new account both remain denied.
8. Genie workspace output red, then LC group green; browser inspection found two additional real failures (workspace viewport-height inheritance and mobile backdrop interception). `entries-layout-red.log` / `mobile-genie-green.log` retain the failure/fix evidence.
9. Filled draft output: `filled-price-red.log` shows the exact guest price output without registration. `filled-price-green.log` and `filled-green.log` verify LC price cells and a summary that suppresses registration for pending accounts and registration-disabled guests.
10. Footer geometry: `footer-geometry-red.log` records a 96px first row against the existing 70px desktop tile. A stronger WindPress selector restores parity with the untouched last tile; the browser test compares actual neighboring tile geometry, including mobile where a 47px minimum plus its icon/padding yields 48px.
11. The complete entry matrix exercises EN/DE × 1440/390, visible native endpoint clicks, filled drafts, real family-model switching through the SAJ brand facet, and private-document isolation. Two consecutive runs and the separate three-engine header run are preserved in `checks/`.
12. The output seam checks URL/translated-label escaping at the WordPress boundary. The full commerce suite after this check is 1063 tests / 5594 assertions.

## Reboot recovery and final visual regressions

- Both full account-entry runs contain63 tests, including endpoint clicks,
  model switching, owner separation and locally captured filled drafts.
- `genie-sheet-red.log`: dock main background was transparent; opaque white
  surface and input-focus assertions added before the WindPress repair.
- `genie-design-red.log`: anonymous sign-in remained a transparent text link;
  recorded OpenAI44px black/outline pills and regular greeting now asserted.
  Dock prompt-to-composer separation is bounded at32px using the reference's
  4px spacing rhythm, with24px chosen for the final group.
- `draft-height-red.log`: DE390 actions measured106px against live104px.
  Padding correction includes the existing root selector so it actually wins.
- Final WindPress compile and present readback are retained in `checks/`.
- The exact comparator's two tests pass: a one-channel one-pixel change is
  counted, declared regions are separated, and dimension mismatches fail.

- Final owner clarification supersedes the prompt-to-composer gap choice above.
  `genie-footer-red.log` fails on190.75px below the disclosure/support footer;
  the final test bounds that bottom gap at0–16px, matching the reported defect.
  Final CUA measurement is0px; no text or route is removed.

### Frontend-only reply presentation

Approved seams remain public component output and real browser interactions.
MessageBody semantic rendering and safe HTML behavior, Reply gradual/immediate
and reduced-motion output, App pending-request status/disabled send, and CopyReply
clipboard confirmation were exercised red before implementation. See
`checks/reply-*-red.log` and final green reports. Real-browser fixture first failed
on the missing waiting state; it then covers locale/viewport/surface, formatted
long answers, the owner's no-auto-scroll contract, explicit jump, and pinned
composer. Fixtures intercept the existing JSON response at the browser boundary;
they do not write server configuration, send mail or alter the model. Abandoned
backend streaming experiments are superseded by the owner's frontend-only scope.

## Review round 2

The same agreed public-output and real-browser seams are used. The new reader
layout assertion first failed at DE390: jump y=728, reader bottom=792. The
comparison output assertion first failed because the visible action was the
long price sentence instead of Sign in. Both failures were reproduced before
implementation. The final browser suite checks EN/DE x1440/390 x dock/workspace,
reader/control/composer non-overlap, complete last paragraph, pointer outline
absent and keyboard focus visible. Empty-draft tests now assert independent
native destinations and the public inquiry form. Registration in inquiry email
labels is explicitly rejected in the inherited current-access fixture.

Filled-draft parity exposed desktop intrinsic-column growth and DE mobile
wrapping, plus a 1px-per-row nested-inline strut increase. The final mobile
inline-flex pair retains the original 21px line strut; no page padding or image
resizing was used.

## Round 2 reply hierarchy and inquiry geometry

The agreed rendered-output seam now expects the actual `phase` choice to be a
named “Grid connection” group. Red: App fixture failed that accessible group
assertion, 42 other tests passed (`checks/structure-red.log`). Green: the same
App fixture plus safe-body and document-link fixtures pass, 48 tests total.
The option strings still pass unchanged to `onAsk`; browser fixtures exercise
EN/DE options in both surfaces and verify the next request's user text.

The inquiry registration link stays on its own line. Its 21px line plus 8px
separation uses the existing space after the last guest block. The original
form, following draft and footer retain their exact positions. The narrowed
region is only the new anchor; six inquiry/recovery recounts all return zero
outside their declarations (`checks/pixel-five.log`).

## Real reply reopening: red → green at the public REST seam

Computer Use saw a new answer with paragraphs, then the same answer reopened
with literal `nn` where blank lines had stood. The real WordPress fixture
writes an already received answer and reads the public GET
`/linker-ai/v1/genie/conversation`. Red: exact SSE comparison fails, showing
`\n`, Unicode and escaped quotes stripped by the native meta write.
Green: `wp_slash` compensates that write's unslashing; complete stream and
messages, plus the final transcript text, are identical. Full conversation
route fixtures twice: 18 tests / 166 assertions, no mail submitted. Their
per-run in-memory collections reset at setUp for repeatability.

Manual c223 verification also received a new German answer and refreshed the
page: the rendered answer before/after reopening compared equal (one answer).
No response wording, prompt, model, transport or old stored record was changed.


## Superseding inquiry spacing and actual-answer checks

The owner rejected the absolute registration entry, which left only 3px above
the solution-draft card. A public browser layout assertion requiring separation
first failed (`inquiry-gap-red.log`); normal-flow markup plus WindPress spacing
now measures 32px in all EN/DE ×1440/390 cases, twice (8 passed). The mobile
following draft card moves by the actual 29px added row; that precise component
is a declared layout change. Footer and full image dimensions still compare
exactly. Earlier absolute-position evidence is rejected, not final acceptance.

The previous hand-written Markdown fixture proved renderer behavior only.
The real-model test, with an ordinary multi-topic buyer question and no response
interception, first failed because the generated EN answer had no headings.
The initial formatting contract was insufficient (EN no heading, DE no list);
placing a precise, formatting-only contract after the existing rules and
requiring each needed project detail as a bullet produces actual EN/DE headings,
lists and emphasis. The final actual-model pair passes, with exact reopened text
in dock/workspace and EN/DE ×1440/390 raw screenshots. A sidebar locator collision
in the fixture was corrected without altering the app. Each fixture removes its
own disposable conversation through the public route.

The public App test first failed on the missing “Reply with an option” group;
the explicit immediate-send panel passes (54 related unit tests). Browser
fixtures also click the real option button and assert the next request contains
that exact option. The generation test and frontend fixture cover distinct
seams and neither substitutes for the other.


Additional integration audit: blindly repeating the entire integration suite in
one bootstrapped WordPress request exposed the existing User Switching request
flag remaining on the shared Conversations listener in the second iteration.
That broad run reports1failure in the unchanged new-account-claim fixture. It
is not hidden: the touched ConversationRoutes suite passes18tests/166assertions
with --repeat2, and both independent fresh-PHP full suite runs pass their28
enabled tests (22 unrelated environment-dependent tests skipped in each). No
production behavior was changed to make a multi-request fixture share a single
request flag. These additional runs do not replace the real account ownership
browser fixture, which passes in both126-case runs.
