# EPC media loading and deliberate playback

The actual EPC pages download offscreen media during the initial load. Two
videos declare autoplay/preload auto; their five-second controller starts
regardless of gallery visibility, document visibility or reduced motion.
Native reads show its counter advancing at scrollY zero with the workbench
over four thousand pixels below the viewport and changing the document height.
Fourteen original images lack intrinsic dimensions, and the mobile photo helper
creates another four without copying sizing/loading attributes. Several unloaded
native lazy images have zero height. German video sources/posters initially
point at English originals until the final script replaces them.

Retain the existing hero source and eager/high-priority policy, customer text,
links, photo sources and existing five-second dwell. Use verified hosted-file
dimensions for all fourteen original images; use native lazy/async loading for
non-hero images. Pass the same attributes to the four derived EPC images before
setting their sources and when selecting another image. The shared photo helper
must preserve About and Services behavior. This follows the existing homepage
native-image migration rather than creating an image loader.

Keep video sources/posters, muted inline loops and native playback. Remove
autoplay and use preload none. German saved HTML uses its existing German media
from the start, including without JavaScript. Playback has one lifecycle entry:
only the current slide's video may play when the actual gallery intersects the
viewport, the document is visible, motion is permitted and the user has not
paused. Other videos pause. If autoplay is declined or IntersectionObserver is
unavailable, native video controls retain an on-demand path. No eager-play
fallback. The retained German localization path cannot independently play video.

Replicate the existing Solution page's visible/document/reduced-motion scheduling
pattern. Distinguish persistent user pause from pointer/focus suspension. Derive
interaction blocking from both causes; touch cannot create a stuck hover. An
explicit Play action may override the current reduced/interaction condition;
new pointer/focus/reduced/visibility blockers withdraw that permission, without
erasing an explicit Pause. Leaving the pointer cannot resume while focus remains.

Replace the three clickable div bars with native buttons and an ARIA tablist,
roving focus, Left/Right/Home/End and current panel state. Labels reuse existing
panel h2 text. Preserve the 3px visual bars while providing 44px hit areas, using
the existing site's 44px control scale. Add an explicit native Play/Pause button.
WindPress reserves the maximum real pane height with one overlapping grid;
inactive panes remain in layout through visibility, inert and aria-hidden.
No fixed text height or hidden/display-none shortcut. Without enhancement, hide
the inoperative controls and show all three original descriptions in order.

Approved action copy after adversarial review: **Play slideshow / Pause
slideshow** and **Diashow abspielen / Diashow pausieren**. The native tab group
adds **Planning tools / Planungswerkzeuge**; review this short group label with
the fixed source. No other customer copy changes.

The pure planner only accepts a complete audited old or final EN/DE pair. Use
the existing reviewed-pair writer and native translation-baseline adoption,
verified full recovery baseline and current exact pair/meta increment. Reject
drift; prove repeat/no-op, rollback and reapply, all saved bytes and backslashes.
Preserve every unrelated page, template, partial, privacy text, user and inquiry.

Verify EN/DE at1440/390,320 and the native760/800 boundaries where relevant:
all three choices, focus/hover/pointer/touch, actual visible images and videos,
manual keys, permanent pause across exits, explicit Play, reduced-motion changes,
late/no-script language and reading order, and no downstream height movement
between choices. Recheck shared About/Services. Compare the same native Chrome,
cache-disabled524288B/s download,262144B/s upload and100ms latency, with unchanged
CPU, against the twelve original successful local samples. Retain the rejected
timeout and earlier diagnostic gaps. Report actual observed media/transfer and
native navigation metrics separately; no guessed FCP/LCP/CLS, full-file bytes,
production CWV or guaranteed speed claim. Source, CI, native fixture, rendered
states, performance and production acceptance remain separate gates.
