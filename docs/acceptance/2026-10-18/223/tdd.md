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
