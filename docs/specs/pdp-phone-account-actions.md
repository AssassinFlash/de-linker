# Complete product actions and readable technical data

The owner requested a full EN/DE review of small misleading, crowded and missing
interactive surfaces. On the snapshot-backed product template, the phone dock's
two-line price clamp hides the registration link while leaving it in the
accessibility tree. DE390 has a 32.5px price box, 49px content and a registration
link beginning at the box's lower edge. EN and the narrower phone layout also
reproduce incomplete or inaccessible account entries. This is a presentation bug
in a working native destination, not a missing business capability.

Use the existing LiveCanvas product template, Woo price gate and destinations.
WindPress `pdp.css` owns the presentation changes. The guest dock has two rows:
two complete account links followed by the existing primary product action.
The existing 44px phone control minimum applies separately to both links, and
the primary retains the product surface's 48px minimum. Existing 8/10px spacing,
panel/control radii, paper, border and teal tokens keep the site's visual
language. Equal flexible account columns allow natural EN/DE wrapping; they
never ellipsize an interactive destination. Hover and keyboard focus make both
account actions perceptible. No new copy, route, JS, PHP layout, dependency or
Snippet is needed. This is the explicit owner-authorized visual bug exception
to unchanged product-page parity.

Keep the fixed dock within the device's CSS viewport: its maximum width is
100vw less the existing two 12px insets. A native DE320 sample has a 351px
layout viewport despite a 320px visual viewport, which otherwise puts the
fixed dock's right edge at339px. A subsequent actual DOM check locates the
overflow at the body heading's unbroken `(WLAN/Ethernet/Bluetooth)` text: the
280px title container has 331px scroll content, and its section propagates
351px page width. Allow phone section titles to wrap without suppressing page
overflow. The next actual browser run must independently confirm that the
page and fixed dock both return to the intended viewport.

The same inspection finds German technical labels overflowing their 46%
column into the value column, and a long conformity-document name exceeding
its text container. In the existing phone breakpoint, put each technical
label above its value, separated by the existing 4px spacing step, and allow
long labels, values and document names to wrap inside their containers. Keep
every specification, document destination and the desktop column structure intact.

Actual site fonts must succeed at the registered instance origin before visual
acceptance. A subsequent native-font DE1440 inspection finds two desktop labels
with 178/185px scroll content inside 171px tracks. The latter leaves only about
2px before its value. Let technical labels hyphenate according to the existing
document language and wrap within their track at every width. This explicit
desktop bug correction preserves the columns and values; a necessary extra
label line may increase that row and move subsequent content. Record that
intended reflow separately from unchanged surfaces. A prior localhost sample
with failed custom fonts cannot establish correct-font layout acceptance.

Remove the blanket phone price clamp as well: a logged-in pending/restricted
account's status must remain readable. Approved prices retain the existing
compact arrangement unless their real content requires additional height.
The existing ResizeObserver measures the dock, and auxiliary controls already
consume that height. A real wheel to the document end finds the footer's legal
links covered by the fixed dock: reserving its height inside the product
section only puts space before the footer. Keep the existing 52px product
clearance, and place the measured height plus that clearance and the native
safe-area inset in the existing footer container's bottom padding on phone
product pages. Do not replace the observer or hardcode a guest-only height.

Acceptance uses an owned complete snapshot instance, with source and database
backups before modification. Capture EN/DE anonymous 1440/390 and narrow320,
normal/hover/focus, real sign-in/registration destinations and native add to
solution draft. Confirm all link text and hit areas are visible, the actual
dock height feeds spacing, footer content remains reachable, desktop retains
its design with the declared long-label correction, and privacy source
hashes/backslashes are preserved. Exercise
existing pending and approved behavior with synthetic local account fixtures;
no production submission, registration, email or model call. Source review,
actual rendered checks, complete CI and production readback remain distinct
gates. Do not infer full-site or real-device acceptance from these states.


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
