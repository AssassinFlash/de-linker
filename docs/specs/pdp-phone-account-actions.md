# Complete phone product actions

The owner requested a full EN/DE review of small misleading, crowded and missing
interactive surfaces. On the snapshot-backed product template, the phone dock's
two-line price clamp hides the registration link while leaving it in the
accessibility tree. DE390 has a 32.5px price box, 49px content and a registration
link beginning at the box's lower edge. EN and the narrower phone layout also
reproduce incomplete or inaccessible account entries. This is a presentation bug
in a working native destination, not a missing business capability.

Use the existing LiveCanvas product template, Woo price gate and destinations.
Only the WindPress `pdp.css` phone rules change. The guest dock has two rows:
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
fixed dock's right edge at339px. The initial cause of that expansion remains
unproven; this bounds the dock without hiding page overflow or its content.

Remove the blanket phone price clamp as well: a logged-in pending/restricted
account's status must remain readable. Approved prices retain the existing
compact arrangement unless their real content requires additional height.
The existing ResizeObserver measures the dock; page padding and auxiliary
controls already consume that height. Do not replace that native consumer or
hardcode a guest-only offset.

Acceptance uses an owned complete snapshot instance, with source and database
backups before modification. Capture EN/DE anonymous 1440/390 and narrow320,
normal/hover/focus, real sign-in/registration destinations and native add to
solution draft. Confirm all link text and hit areas are visible, the actual
dock height feeds spacing, footer content remains reachable, desktop stays
unchanged and the privacy source hashes/backslashes are preserved. Exercise
existing pending and approved behavior with synthetic local account fixtures;
no production submission, registration, email or model call. Source review,
actual rendered checks, complete CI and production readback remain distinct
gates. Do not infer full-site or real-device acceptance from these states.
