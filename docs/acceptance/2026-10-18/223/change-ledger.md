# #223 ruled visual changes

Authority: owner instruction in the ticket/session, including the confirmed
extension to recovery, private-document 403 and Genie. New copy is recorded in
[copy-review.md](copy-review.md). No tolerance or dynamic mask is introduced.

| Change | Before | After / bounded region |
|---|---|---|
| Account dropdown adds registration | before/*-header-1440-before.png | pixels/*-header-1440-local.png; dropdown box and its existing shadow (50px blur in chrome.css) |
| Mobile menu adds registration | before/*-mobile-390-before.png | pixels-review2/*-mobile-390-local.png; account utility row only (.tv-mobile-utility-row) |
| Footer login tile has two destinations, count 04 | before/*-footer-*-before.png | pixels/*-footer-*-local.png; first account tile and count only |
| Separate empty-draft entries | before/*-draft-*-before.png | pixels/*-draft-*-local.png; action row only |
| Inquiry optional create link | before/*-inquiry-*-before.png | pixels-review2/*-inquiry-*-local.png; new registration anchor only |
| Recovery links paired | before/*-lost*-before.png | pixels/*-lost*-local.png; recovery link row only |
| Document denial secondary registration | before/*-document-*-before.png | pixels/*-document-*-local.png; existing denial card, retaining 403 |
| Visible product-card actions paired | before-products/*-shop-*-before.png and *-category-*-before.png | pixels-products/*-local.png; each card action row, with existing 44px minimum |
| PDP login price area paired | before-products/*-product-*-before.png | pixels-products/*-product-*-local.png; price areas in rail/mobile bar |
| Comparison guest price row paired | before-products/*-compare-*-before.png | pixels-review2/*-compare-*-local.png; guest price cells only |
| Genie guest entry row | before-products/*-genie-*-before.png | pixels-products/*-genie-*-local.png; tool panel, including its necessary height allocation |

The scenario JSON records exact selectors and the capture manifest records their
measured live/local rectangle unions. The header shadow rectangle uses the existing CSS shadow extent: 24px
vertical offset plus 50px blur, hence 74px padding (the initial 50px
measurement omitted its lower tail). Regions must not be expanded to hide a
failure. Raw full-page differences and dimension mismatches remain evidence.
Unrelated live/local drift is reported as incomplete acceptance.

The header's pre-existing approved contract remains unchanged: 95 sampled widths
per engine, no EN/DE mismatch in Chromium/WebKit; exactly Firefox 1283–1287,
EN expanded / DE folded. The fit algorithm and its safety budget are unchanged.

Two rendered integration defects found in this ticket were fixed in WindPress:
Genie's workspace wrapper applied full viewport height to the new sibling row;
and its mobile backdrop intercepted clicks on that row. The row uses content
height and a positioned stacking level above the backdrop's auto paint order,
while remaining below the existing conversation-history overlay.

Rollback: revert this ticket's source and translation changes, then run present
and the normal WindPress admin compilation. No database migration is introduced.

The nonempty draft pairs both Woo price cells and its summary with Create account.
`before-filled/` and `filled-draft/` preserve the local before/after state.
Review round 2 adds live parity through a disposable anonymous Woo session; its
own nonce-bearing remove link clears the line after capture, including failures.
No inquiry/order is submitted and no mail is sent. The footer reset
uses a stronger selector than its existing LC style so nested links do not
inherit 70/50/47px tile dimensions; surrounding items keep their original size.

### Owner ruling and superseding comparison decision (2026-10-18)

All comparison and Genie presentation changes remain in #223 and PR #312;
no ticket is split. The owner explicitly returned the branch for repair.
The earlier whole-body comparison declaration is superseded: the live LC shell,
typography, table widths and image geometry are restored. Only the guest price
cells change, with concise existing Sign in / Anmelden and Create account /
Konto erstellen actions; the full original price explanation is in the native
sign-in link's escaped accessible label. No broad .sf-compare region remains.
Whole-page dimensions remain a separate exact failure condition. The mobile
menu declaration is narrowed to .tv-mobile-utility-row, with no panel-wide mask.

Filled-draft links preserve the existing native layout. The right-hand desktop
registration action uses the space under its price label without increasing the
intrinsic price-column width. Mobile links use the existing storefront 12px
control type within the original 21px line strut, preventing wrapped registration
from moving the quantity field or footer. Declared regions cover only price cells,
the new link rectangles, and the existing summary account area. Original raw
images and failures remain in before-filled-round2/.

### Owner follow-up: Genie expanded surface

The owner reported a grey sheet, then rejected the white but disconnected
layout as lacking the requested OpenAI design. Preserve both rejected views:
`computer-use/de-genie-dock-mobile-390-rejected.png` and
`computer-use/de-genie-dock-mobile-390-design-rejected.png`. The final surface
uses the existing OpenAI research dossier A2/A4/A5/B4: a top account nudge with
44px black / outlined pills; a regular 24/28 welcome title; compact toolbar;
one outer sheet radius and a compact composer footer. Main
column inherits the app's opaque white background, leaving the scrim behind the
sheet. New final images are in `computer-use/` and `pixels-final-fixes/`.
No copy, model, protocol, account or inquiry permission is changed. Tool surface
redesign is authorized by the owner's current visual correction and AGENTS §2.
These screenshots are implementation evidence, not a claim of owner approval.

The final DE390 empty-draft action region preserves the measured live104px:
45px primary row +12px gap +47px secondary row. The narrowed sign-in button's
border is deducted from its padding; the root-scoped selector wins the existing
storefront declaration. No page-height padding or image resizing is used.

The owner clarified the lower disclosure / support links / blank block as the
specific remaining defect. The intermediate centered-group layout is superseded.
`computer-use/de-genie-dock-mobile-390-footer-rejected.png` shows190.75px
below the footer. The final panel lets welcome content use the flexible area
while composer/disclosure/support links finish at the bottom (measured0px).
Disclosure remains12/16; support links11/16, with4px gap and12px bottom padding.
No text or destination is removed. `genie-footer-red.log` records the failure.

The owner then clarified that the bottom words and flat links themselves also
lacked design. The final helper footer is one quiet row: the reviewed short AI
sentence plus a native “Help & privacy / Hilfe & Datenschutz” disclosure. Its
popover retains the full AI introduction and all three original links. Escape
closes it and restores the trigger focus. This supersedes the flat support row
in the previous screenshots. Account markup remains LC; the existing React tool
app owns its footer composition; all new styles remain WindPress.

### Latest owner correction: reply typography

The real DE answer measured 14px/23.8px, 358px wide, 495 characters in a single
paragraph. Before: `computer-use/de-genie-real-answer-before-typography-390.png`.
After: `computer-use/de-genie-real-answer-after-typography-390.png`.
The dock now uses 16px/26px body, 20px insets and paragraph rhythm; workspace
retains 16px/28px reading type. Long plain prose is visually grouped only at
existing sentence boundaries with locale-native Intl.Segmenter. Canonical
answers, clipboard original, follow-up payloads and storage remain untouched;
no headings/emphasis/facts are invented. Long unformatted top-level Markdown paragraphs may also gain reading breaks;
paragraphs with inline formatting, lists, code and tables retain their structure. Test verifies the real
495-character response becomes three paragraphs with identical normalized text.

Secondary choices have a consistent 40/44px target; the email-conversation action
is a quiet icon/text control. Transcript content contains its trailing margins,
so an explicit jump reaches the true bottom; restored long answers start at
the reading position rather than jumping to the end. These are changes inside
the ruled Genie tool region, with no marketing/header/footer restyling.

The first moving reveal control was not reliably clickable: real browser click
retries observed growing text intercepting the pointer before the control vanished.
The final WindPress rule anchors it beside the answer label, outside body flow;
no force-click is used. The browser fixture now measures identical x/y coordinates
across 100ms of progressive body growth before performing the normal click.
Fixture cleanup always releases held responses before closing a video context.

### Review round 2: readable reply and controls

Before: replies/before-round2/*-answer.png (owner-identified composer clipping,
floating jump over text and keyboard focus ring in the capture). After:
replies/*-answer.png and *-latest.png, EN/DE x1440/390 x dock/workspace.
The reader, an opaque 48px control row (40px button +4px each side), and composer
are separate flex items. No text can paint through the bottom control area.
The last paragraph is fully reachable within the reader, above the composer. The transcript uses
:focus-visible for keyboard navigation and no outline during pointer reading.
Real-response Computer Use images are also under computer-use/*round2*.png.

## Final review additions

- Inquiry: the new registration anchor is its own line, using 29px of the
  existing space after the guest block. **This intermediate absolute placement
  was rejected by the owner** because it left only 3px before the draft card.
  `pixels-review2/*inquiry*` is retained as intermediate evidence, not the final
  visual acceptance. The superseding normal-flow repair is described below.
- Reply hierarchy: the existing first paragraph, Markdown heading levels,
  markers, tables, document cards and actual follow-up options get distinct
  type/spacing. Before: `computer-use/*round2*`; after:
  `computer-use/*round3*` and current `replies/*answer.png`/`*latest.png`.
- Reply reopening: native meta escaping preserves received Markdown instead
  of turning newlines into `nn`; no old history rewrite. Red/green route proof:
  `checks/roundtrip-red.log`, `checks/roundtrip-final.log`; real refreshed reply:
  `computer-use/de-genie-round3-dock-reopened-1440.png`.


## Owner corrections after round 2 (supersedes earlier inquiry placement)

| Ruled change | Before | Final after | Exact boundary |
|---|---|---|---|
| Inquiry registration spacing | `computer-use/en-inquiry-gap-rejected.png` | `computer-use/{en,de}-inquiry-gap-fixed-{1440,390}.png` | Normal-flow registration row; existing 32px column gap. Desktop only new anchor. Mobile new anchor and the exact following `.linker-inquiry-draft` card moving 29px. Full canvas/footer unchanged. |
| Real answer hierarchy | `computer-use/en-genie-structure-rejected.png`, `replies-real/before-format-contract/` | `replies-real/{en,de}-{1440,390}-{dock,workspace}.png` | Genie tool redraw region only. User approved EN/DE formatting contract; existing facts/short/special rules remain. |
| Recognisable immediate reply options | `computer-use/en-genie-structure-rejected.png` | `replies/*latest.png`, `computer-use/en-genie-format-dock-latest-{1440,390}.png` | Contained option group, send explanation, visible Send label; original option payload. Desktop narrow dock and mobile single column, wide workspace two columns. |
| Native filled-draft image capture | earlier image-only failures in `pixels-review2/` | final full-pair captures and `capture.json` cart image metadata | No new ruled region. Keep native lazy/srcset; decode visible images only. Comparator still exact RGB and exact dimensions. |

Comparison declaration is only `.linker-compare-table tbody tr:nth-child(2)>td`;
mobile navigation declaration is only `.tv-mobile-utility-row`. Neither an entire
`.sf-compare` nor the entire `#tv-mobile-panel` is declared. Historical 10 DE
header differences attributed to #229 remain in `pixel-results-before-review2.*`;
the fresh snapshot comparison reports its actual current numbers without a
header mask. No new breakpoint or engine exception is introduced.
