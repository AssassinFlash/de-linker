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
Render the counter as muted informational text, retaining its existing
aria-live and unique ID. A suggestion popup may cover this noninteractive
metadata while open, as it covers other content below the input; dismissing
it must reveal the unchanged current count.

The native filtered search establishes the counter's containing block. Add
its existing 1px bottom border to the 8px offset, so measurement from the
search's visible outer edge is 8px rather than 7px. The first candidate's
7px measurement is retained as rejected spacing evidence.

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
