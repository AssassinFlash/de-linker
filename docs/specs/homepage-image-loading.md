# Homepage photo loading

The EN/DE LiveCanvas homepage stores sixteen IMG elements in its page content.
Fifteen have no loading attribute; the last scene-card photo is already lazy.
On the complete local snapshot at DE390, before scrolling, nineteen image
requests finish with 3,273,456 encoded bytes, including below-fold photos and
four hidden process steps. These are local transport measurements, not an
online performance claim. Verify the first-photo position at EN/DE1440/390/320
before applying the candidate to the owned current-source instance.

Add native `loading="lazy"`, `decoding="async"`, and intrinsic `width`/`height`
to the sixteen audited photos. Their sizes must match the decoded browser
images and native file metadata from the complete snapshot. Keep every
original src, alt, existing matching dimension, class, paragraph, style,
script and language. Keep the header logo and CSS hero background unchanged.
No data-src hydration, observer, loading overlay, new CSS or image rewrite is
needed. The first lazy/async-only candidate failed initial layout: in DE1440,
the residential image height fell from 406.672 to 350px and the commercial
image from 693.273 to 408.094px before loading, moving later sections up by
341.852px. Loaded screenshots missed this issue. The existing CSS relies on
intrinsic ratios in those rows. Reserve them through native dimensions, then
verify initial and loaded geometry at all six EN/DE1440/390/320 layouts.
Retain the earlier candidate's measurements as rejected layout evidence; do
not reuse them as acceptance of the revised candidate.

Use the existing transactional content writer, which checks original bytes,
locks both rows, supplies wp_slash, uses native wp_update_post and reads the
saved bytes back. It disables wp_after_insert_post for these paired content
writes, avoiding an automatic translation job between EN and DE. The existing
pre-update baseline observer still runs: capture translation metadata and
queued actions before and after and investigate changes. Do not run a model,
translation queue, registration, inquiry or mail test for this repair.

The first source review found that the shared writer in the complete base
could let wpdb reconnect during a disconnected transaction. Bring across only
the previously developed connection guard and native fault fixture, and
verify them again on this owned instance: no disconnected write may replay
on a new handle without its row locks. Restore the caller's connection report
mode, retry count and query filter afterwards. A failed COMMIT acknowledgment
has an unknown outcome; independently read both pages before any retry or
rollback. Never promise that a catch-block ROLLBACK undoes a committed write.

The migration refuses a changed image set, an unknown photo, duplicate
attributes or conflicting loading/decoding/dimension instructions. It ignores IMG-like
strings inside scripts and comments and is idempotent. A production write
requires a verified complete local backup; retain a separate native database
backup and exact content backup before the local write too. Rollback supplies
the saved original contents to the same guarded writer, with then-current
content as the expected source. Keep all original failure records.

Acceptance includes the same original content with attributes removed,
script/style/slash hashes, native pair and privacy readback, action/mail
counts, normal and fast scrolling, all accordion photos and five process
steps, testimonial carousel, final scene, and JavaScript-unavailable native
image loading. Verify actual image responses, decode/natural sizes and real
font consumers, EN/DE1440/390/320. Compare initial request counts and encoded
bytes before/after without a scroll, plus predeclared repeated, interleaved
loading measurements with identical browser/cache/network conditions.
FCP, LCP, load and layout shifts have separate evidence boundaries; do not
claim one improved because another metric fell. Complete pixel, source,
runtime, CI, integration, production and full-site coverage gates remain
separate. This candidate starts from complete security tracking e442a423;
it does not publish the other held UI candidates or replace the production
writer's current complete tree.
