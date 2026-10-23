# Homepage photo loading

The EN/DE LiveCanvas homepage stores sixteen IMG elements in its page content.
Fifteen have no loading attribute; the last scene-card photo is already lazy.
On the complete local snapshot at DE390, before scrolling, nineteen image
requests finish with 3,273,456 encoded bytes, including below-fold photos and
four hidden process steps. These are local transport measurements, not an
online performance claim. Verify the first-photo position at EN/DE1440/390/320
before applying the candidate to the owned current-source instance.

Add native `loading="lazy"` and `decoding="async"` to the sixteen audited
photos. Keep every original src, alt, dimension, class, paragraph, style,
script and language. Keep the header logo and CSS hero background unchanged.
No data-src hydration, observer, loading overlay, new CSS or image rewrite is
needed. Existing CSS reserves the photo containers; verify actual geometry
and shifts with the browser rather than assuming attributes cannot affect it.

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
attributes or conflicting loading/decoding instructions. It ignores IMG-like
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
