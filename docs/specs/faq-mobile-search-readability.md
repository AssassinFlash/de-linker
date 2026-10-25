# Readable narrow-screen library search

The actual EN/DE FAQ and download library has a fixed-height search row. Its
localized, non-wrapping counter competes with the input and clear button in
that same flex row. At DE320, the empty input is only 67.1953125px wide,
including 24px horizontal padding; its usable text width is about 43px. The
visible clear button is 22 by 22px. EN320 also contracts to 105.4765625px on
the recorded SAJ query. The native current paths are /faq-download/ and
/de/faq-dokumente/; their existing totals differ and must not be normalized.

Use the existing 520px WindPress breakpoint. Keep the 52px search row and
its existing suggestion anchor. Position the same counter below the row,
with its existing 28px height and 8px separation. Reserve 44px bottom margin
for that line plus its two 8px gaps. Use the existing is-enhanced state so
an unavailable library script does not reserve space for a hidden control.
Render the counter as plain informational text, retaining its existing
aria-live and unique ID. A suggestion popup may cover this noninteractive
metadata while open, as it covers other content below the input; dismissing
it must reveal the unchanged current count.

The native filtered search establishes the counter's containing block. Add
its existing 1px bottom border to the 8px offset, so measurement from the
search's visible outer edge is 8px rather than 7px. The first candidate's
7px measurement is retained as rejected spacing evidence.

Use the page's existing deep-ink token for this small text on the exposed
gradient. Native PNGs embed Display P3: diagnostic contrast calculations
must convert their background samples through that ICC profile to sRGB,
the space of the CSS colors. Preserve the initial unconverted calculations
as provisional observations. Corrected EN520 samples beside the actual
text line give about 4.418:1 and 4.475:1 for the muted token; the final ink
gives about 10.84:1 to 11.91:1 across the recorded narrow layouts. Nearby
samples are not measurements behind every glyph. Keep the 12px size and
plain background, and retain the original PNGs unchanged for pixel checks.

The wrapper already spaces the icon and input, so remove the input's extra
horizontal padding at that breakpoint. Enlarge the native clear button to
44 by 44px, matching the library's existing pager and Genie targets. Keep
its original label, font size, background, native focus and clear behavior.
The control must fit the existing row and remain separate from the input.

This is a scoped CSS repair, not a content or search rewrite. Keep the LC
markup, result-count semantics, questions, documents, localized text and
library-ui.js bytes. Above 520px the stylesheet must preserve the original
layout. The intended phone changes are the larger usable field and clear
target, and a separate count line that moves following content down 36px
relative to the previous 8px bottom margin. Do not rework unrelated headers,
footers, typography, tools, security or business data.

Work from a complete owned snapshot and back up its full database and exact
source before changes. The initial instance uses the deployed 1dce source
as a UI baseline; current production has since advanced to 08f12c03. This
older entire tree must never be deployed. Before publication, integrate the
small final patch with the actual then-current complete source and repeat
the applicable checks and online readback, preserving the parallel safety
work and existing privacy content/backslashes.

Validate EN/DE1440/390/320 and the 520/521 boundary. Record actual loaded
resources and font consumers separately, normal/search/empty states,
counter placement and contrast, native hover/focus and full clear hit area,
suggestion arrows/Enter/Escape, query retention, both tabs, type filters,
category anchors, actual FAQ answers and hosted document destinations. Read
the complete rendered page and lower controls as well as the first screen.
Block only the local library script to verify the original progressive
register remains usable, restoring the block list afterwards. Native
WindPress compilation/readback, existing meaningful JS fixtures, full
checks/CI, Spec/Standards review, pixel evidence and eventual production
verification remain separate gates. Local natural-network lifecycle timings
are diagnostic samples; this CSS repair does not establish significant
loading improvement or close the full-site performance objective.


## Bounded current-source delivery

This prepared correction is delivered with the font, product-phone and library
patches in one batch based on accepted source18c85c31 (production589). The
PDP contribution carries only pdp.css and its specification; old header code
from its original branch is excluded. Current header, authentication, legal
and marketing content stay protected by the scoped publication readback.

Under AGENTS.md section0.1, reuse the accepted original fixtures and rendered
evidence for unchanged implementation, inputs and runtime conditions. Do not
replay the original complete matrix, fallback experiment or repeated font
benchmarks. Reuse exact font/glyph proofs after source/output hash checks;
perform only current-base integration, affected real browser controls and
public font resource/consumer readback. Record actual production compressed
bytes separately from offline file savings; do not claim a Core Web Vitals or
whole-site speed result from this batch. All newly found unrelated gaps stay
in the existing full-site goal rather than expanding this release.
