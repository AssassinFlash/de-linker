# Header layout before its enhancement

The current-main QA baseline still contains the earlier button header. Its native
script-disabled Contact controls reproduce a document width of 1550px in English
and 1686px in German at a 1440px viewport, with the contact action outside the view.
The initial action labels are expanded until the footer enhancement measures
the row. This proves the initial-state dependency, not a production frequency,
an observed FCP change or a measured CLS cause.

Reuse the existing native disclosure and initial-layout implementation from
PR611, frozen at 197eae8aee1ca6f5181978324c7d021f4fa318e2. Its functional
reviews and original evidence remain retained, including its unresolved closed
page pixel controls. Import only its seven-file delta onto current main
ad20bad5d00d339f9392624913c7e08bf5584b98; do not import its older branch ancestry.
Do not build another menu or duplicate its links. Reuse its LC native
summary/panel, WindPress surface, enhancement and compatibility with the previous
button partial. The measurements below describe that retained implementation;
the current-main integration requires fresh native readback and browser proof.

Before the row has been measured, offer that existing native folded panel at
desktop widths too. Search, solution draft and language anchors stay usable;
the native panel supplies the account and contact links. Hide the inactive
desktop account disclosure until its enhancement runs. Use the existing1280px
desktop breakpoint, not a new guessed fit threshold. The first ready fit uses
an explicit false compact state to measure the same expanded action budget,
then the existing compact/fold calculation. Keep normal item sizes, relative
spacing, text, links, desktop breakpoints, language-independent fit and the
approved three-engine fold boundaries. The separately evidenced duplicate
desktop inset correction below moves that row left by one existing gutter;
record it as an explicit closed-header visual bug fix.

Keep the older button partial's desktop data-open guard limited to its direct
container-child panel. The native details panel must follow its parent's open
state even before the enhancement can supply a data-open attribute.

Native keyboard review also shows an opened group's first card touching the
summary's focus outline. Give every group body the existing 8px content gap at
its top, clearing the 2px outline and 2px offset. Keep the summary's target,
closed row geometry, content, and desktop menus unchanged. Recheck focused
groups and the final contact action after all five groups are expanded.

At 320px the two 140px product cards and their existing 10px gap exceed the
288px content width by 2px. Cap each card at the smaller of its existing width
and half the available rail width after the gap; let its image follow that
width. Reserve the existing outline's 4px footprint around the cards, offsetting
that reserve at the sides so card alignment stays unchanged. The card outline must be fully
visible, including its top and left edges; use the existing 12px card corner
radius and teal title on hover or keyboard focus.

Native review rejected both horizontal alternatives: selecting one focused
snap target traps a subsequent finger swipe, while suspending snapping still
leaves a partially visible keyboard target in the in-app browser. Let these
same cards wrap naturally when they cannot all fit. All three solution entries
then remain visible without an undisclosed horizontal gesture or another JS
scroll controller. Keep the existing card width, gaps and wider single-row
presentation; the existing panel supplies native vertical scrolling when
needed. This opened-panel bug fix is an explicit visual change; the closed
header and normal desktop menus retain their parity gate. Verify both card
groups, first/last focus, the third solution's real consumer and panel scroll
end in EN/DE with and without the enhancement.

The existing mobile CSS places Products above Solutions while both LC partials
put Solutions first in source order. Move each complete Products block before
Solutions, preserving every link, label and attribute. Native Tab, Shift+Tab
and reading order must follow the unchanged visual sequence; no positive
tabindex or JS keyboard reordering is needed.

The real native Tab sequence at 320px exposes another clipping case: after all
product links, the third solution card's border box ends at 899.0625px in the
900px viewport, cutting off its 2px outline plus 2px offset. Reserve that same
4px footprint with block scroll margins on the existing panel links and group
summaries. Independent DE desktop readback then shows the outline ending at
899.078125px while the client scrollport ends at899px. Native scrolling rounds
to whole CSS pixels, so use5px: the same4px footprint plus the smallest whole
pixel to protect against that rounding. Keep the strict boundary comparison;
do not add a tolerance or discard the failed stable originals. Verify the
actual scrollport's inner edges with native keys, without
programmatically focusing each target. Keep the failed original evidence.

At the1280px folded desktop boundary, Escape focuses the native summary at
x1236px with width44px; its outline ends at1284px outside the1280px viewport.
The ordinary desktop Contact action also ends at the viewport edge between
1283px and1300px; actual native Tab at1283px cuts off its4px focus footprint.
Both arise from the same full-width content-box frame: the container already
owns1rem gutters, while the frame adds another16px start padding and shifts
the whole row into the end gutter. Remove the duplicate frame inline padding,
using the existing container inset on both sides. Its old client width minus
16px start padding equals the new client width minus zero padding, retaining
the measured content width, item spacing and native fit budget. Remove the
interim native-only end margin; the common gutter now contains both targets.
The desktop row moves left16px as this explicit closed-header bug fix; mobile
geometry stays unchanged. Verify both languages and the existing three-engine
fold boundaries, native initial opening and script adoption. Keep the recorded
bug delta distinct from unaffected pixel controls.

When Products is open on desktop, the fixed50px Genie launcher overlaps the
Services row's right end by50px by44.7109375px. Testing only the row's centre
misses that blocked area. Temporarily hide the resting dock while native
navigation is open, using its direct launcher's existing aria-expanded=false
state. Hiding only the child leaves the fixed parent intercepting clicks:
the actual click at1235,857.64453125 closes navigation but leaves Home instead
of following Services. Hide the whole collapsed container and remove its
pointer events. Verify the original positive-area intersection and arrow
position with actual hit tests and native clicks; a95% row sample does not
reach this former50px obstruction on a1248px row. The same
menu still offers its Genie link; closing navigation restores the launcher,
and an already open conversation is unchanged. The separately fixed preview
card follows the same temporary visibility rule, including when its existing
timer fires while the menu is open. Preserve its hidden flag, visit memory
and timer; do not dismiss the card or reset the visitor's data. Check a real
visible preview through menu opening/closing as well as a pending preview.
Remove the special82px panel
bottom padding that only protected Contact and keep the existing12px bottom
breathing room. Verify the whole affected row's hit area, all group states,
Contact at scroll end, and launcher restoration in both languages; do not
start a model conversation for this navigation check.

The secondary product and all-items rows override the generic link text's
existing 44px minimum with zero, rendering 36.5px and 40.796875px anchors.
Restore that existing minimum with border-box sizing on those text containers;
retain their padding, typography and centred labels. This is an explicit
opened-panel target-size fix. Verify actual anchor boxes of at least 44px,
the complete native Tab sequence and scroll-end contact after the extra height.

If someone has already opened the native panel at a desktop width while the
enhancement is pending, keep it available until they close it. A fit that has
room for the ordinary row must not dismiss that active menu. After it closes,
re-run the existing fit. If its summary held keyboard focus and becomes hidden,
move focus to the first visible primary disclosure; do not take focus from an
outside field or button. Normal mobile resizing and disclosure behavior remain
as in the reviewed native implementation. No PHP, new text, link inventory,
dependency or extra rendering/styling channel is introduced.

Retain scoped LC/style preimages and the active recovery baseline before local
application. Update only the two header partial contents through the guarded
native writer and chrome.css through the existing volume; keep metadata,
language pairs, other templates/styles and home/privacy prose exact. Use
official Generate and read back the actual compiled file, then log out before
anonymous browser checks. Do not run full present over unrelated surfaces.

Verify EN/DE1440/390 plus desktop fit boundaries and320px: native opening,
closing, groups, account/contact targets and no clipping with scripts disabled;
normal-JS geometry against the existing baseline; and actual held/released
header requests with early desktop/mobile opening. Check late adoption,
keyboard focus after close, Escape, outside focus, scroll-end contact targeting
and normal responsive transitions. Keep the existing three-engine fit suite
unchanged. Earlier native pixel evidence does not replace new combined-source
checks. Local source review, real native/browser checks, CI and protected
production integration/readback remain separate. No overall speed gain or
full-site completion follows from making this initial state usable.
