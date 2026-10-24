# Mobile navigation during loading

The current mobile menu renders a visible 44px button before its footer
enhancement arrives. A production first click was observed without a response.
In the snapshot-backed isolated instance, pausing only the actual header script
reproduces the boundary: the visible button stays collapsed during loading;
releasing that request makes the next click work. This controlled failure
demonstrates the dependency, not a measured frequency of production failures.

LiveCanvas already supplies ordinary links and native details/summary groups
inside the mobile panel. Extend that native disclosure to the panel itself.
The existing summary-sized control occupies the same place in the header;
its links can be opened before JavaScript, through normal activation and the
browser's native expanded state. Preserve all existing EN/DE wording, routes,
images and desktop menus. No PHP rendering, Snippet, duplicated link list or
new dependency is needed: LC owns composition and WindPress owns appearance.

The panel opens below the header as a bounded, scrollable surface. This
deliberately stops the opened navigation from growing the sticky header and
pushing the page content. Record that intended open-state layout change in
the visual evidence; the closed mobile header and page content retain their
layout. The desktop gutter correction is separately recorded in
`header-initial-layout.md` as an explicit closed-header visual bug fix.
Check width, full panel scroll reach, final contact action, keyboard targets,
focus visibility and stacking with existing page controls.
The existing Genie launcher is 50px high, 20px above the viewport bottom,
and visible above 860px (`plugins/linker-tools/src/genie/genie.css`). Its
footprint also overlaps the Services row before the panel reaches its end,
so bottom padding alone cannot protect the menu's full hit areas. While the
native panel is open, hide the whole collapsed dock through its direct
launcher's existing aria-expanded=false state and remove its pointer events.
Hiding just the button leaves the fixed parent intercepting the Services
arrow: a real native click closes the menu without following the link.
Check that exact former obstruction and arrow position, then restore the
dock when the panel closes; retain an
already open conversation and the menu's Genie link. The independent fixed
preview card is temporarily hidden by that same native open state; its timer,
visit memory and hidden flag are unchanged. Verify both an already visible
card and one whose timer becomes due while navigation is open.
Keep the existing12px
panel bottom gap. Check the whole Services and Contact actions, launcher
restoration and keyboard visibility, not just their centre points or bounds.
The actual expanded state remains native; the summary has an explicit button
role and controls reference so it remains discoverable when styled. The panel
also changes the hamburger glyph to a close glyph through native open-state
CSS, including while the enhancement is unavailable. Both glyphs are
decorative; the existing control label remains the accessible name. Its
closed glyph retains the original geometry.
The panel
height also subtracts the existing toolbar offset for staff sessions: reuse
the same 32px/46px values that position the sticky header, rather than letting
the final action fall below the viewport after scrolling to the end.

The existing enhancement adopts an already-open native disclosure without
closing it. It keeps Escape, outside click, focus departure and responsive
folding, synchronizing with the native open property. It does not handle the
same native click a second time. The existing button path remains supported
while the deployed LC partial is being replaced, without another controller.

Acceptance: EN/DE at 1440 and 390, anonymous snapshot-backed local first;
compare the closed header and page at matching native conditions. With the
header script paused or failed, actually open/close the mobile menu, expand
its native groups and follow a representative language-correct link. With
the script arriving after an early opening, verify that opening is retained,
then verify keyboard, Escape, outside click, mobile groups, deepest contact
action and responsive folded/unfolded transitions. Desktop menus retain
their keyboard and hover consumers. Record production readback separately,
coordinate the publication window and preserve the parallel security runtime.

This fix removes the mobile menu's loading dependency. It does not claim an
overall FCP gain or completion of the full-site performance/function goal.
