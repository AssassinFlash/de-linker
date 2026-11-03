# Installer entry scroll

Opening `/for-installer/` or `/de/fuer-installateur/` without a fragment must
leave the initial viewport at the page heading. The current published pages
instead scroll into the timeline: their shared inline `tabSet()` initializes
with `show(0)`, and `show()` unconditionally calls `scrollIntoView()`.

The correction preserves the existing page, copy, layout, media, selected tab,
ARIA state and keyboard behavior. `show(index, revealTab = false)` changes
scroll position only when a click or arrow-key selection explicitly passes
`true`. The initial `show(0)` still selects the first tab without scrolling.
Existing fragment links and browser history remain native.

The presentation already lives in the two LiveCanvas page records (826 and
6869, verified through production WP-CLI). No PHP page, second tab controller,
Snippet, additional stylesheet or new dependency is needed. The narrow
`tools/migrate/repair-installer-initial-scroll.py` corrects only four known
script expressions in that existing controller. It rejects another page,
ambiguous controllers and mixed/partial source; a second run is unchanged.
All bytes outside that script remain intact.

Before a production data write, take the required complete incremental
backup. The command additionally writes a private page-level backup, uses the
existing transactional writer with locked-source comparison and `wp_slash()`,
then independently reads both records. The writer suppresses
`wp_after_insert_post`, so this script-only repair does not enqueue automatic
translation; verify language pairing and translation state before/after.
Do not bypass the exact-source check when another writer has changed a page.

Rollback uses the same writer: read the current two records, require them to
equal the planned repaired contents, then save changes with `before` equal
to those repaired bytes and `after` equal to the saved page-backup contents.
Read both records again, including their language pairing and SHA256. A
source mismatch stops rollback and requires inspection rather than replacing
someone else's edit.

The shared CLI writer also needs a connection boundary. Native WordPress can
reconnect and replay an UPDATE after error 2006, losing the transaction and
row locks. The repair requires native `wpdb`/mysqli, keeps mysqli in
ERROR/STRICT mode with reconnect attempts disabled during the transaction,
and guards the original handle and thread before each query. All modes and
the query filter are restored in `finally`. Rollback failure diagnostics do
not replace the original error. A failure during COMMIT is explicitly an
unknown outcome: read both records independently before retrying or rollback.
Neither a new connection's successful ROLLBACK nor a pre-COMMIT disconnect
proves what happened after a possibly accepted COMMIT.

The opt-in real WordPress fixture uses a dedicated local instance and only
its own disposable private pages. It covers ordinary saves, source drift,
second-page failure, disconnects before START/first UPDATE/COMMIT, a committed
transaction whose acknowledgement is not observed, and connection replacement.
It verifies content, connection identity, exception mode, reconnect settings,
query-filter restoration and fixture cleanup. It never kills another task's
connection or writes production. Separate stub-controller tests or source
existence do not replace these storage fixtures or browser acceptance.

Acceptance requires EN/DE at 1440 and 390: fresh navigation stays at the top;
each timeline and demonstration tab still changes its actual panel by click;
ArrowLeft/ArrowRight wraps and moves focus; the selected mobile tab remains
visible; links with existing fragments still land at their intended section.
Compare the page at the same scroll position for unchanged typography,
spacing and content. Separate local, review, CI and production readback.
The full-site goal remains active after this bounded repair.
