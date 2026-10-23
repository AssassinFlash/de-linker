# Header layout before its enhancement

The current QA baseline still contains the earlier button header. Its native
script-disabled controls reproduce a document width of1542px in English and
1678px in German at a1440px viewport, with the contact action outside the view.
The initial action labels are expanded until the footer enhancement measures
the row. This proves the initial-state dependency, not a production frequency,
an observed FCP change or a measured CLS cause.

Reuse the already reviewed native disclosure implementation from PR581, frozen
at94bb72dc209fda72121ff3db711dbd259d1ad082. Its original six-file implementation
and evidence remain retained. Do not build another menu or duplicate its links.
The present QA branch imports those exact six blobs before the additional
initial-layout change. Reuse its existing LC native summary/panel, WindPress
surface, enhancement and compatibility with the previous button partial.

Before the row has been measured, offer that existing native folded panel at
desktop widths too. Search, solution draft and language anchors stay usable;
the native panel supplies the account and contact links. Hide the inactive
desktop account disclosure until its enhancement runs. Use the existing1280px
desktop breakpoint, not a new guessed fit threshold. The first ready fit uses
an explicit false compact state to measure the same expanded action budget,
then the existing compact/fold calculation. Normal enhanced geometry, text,
links, desktop breakpoints, language-independent fit and the approved three-
engine fold boundaries must remain unchanged.

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
