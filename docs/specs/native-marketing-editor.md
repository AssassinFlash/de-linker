# Use the native editor mode for designed marketing pages

The Utility and Services EN/DE pages use the theme's empty page template and
contain complete designed HTML. Their native `_lc_livecanvas_enabled` metadata
is absent, both on the snapshot-backed local instance and in a read-only
production check. The other eight marketing families already enable it.
LiveCanvas's installed `content-filtering.php` removes `wpautop` and related
WordPress content filters only for an enabled page. Without it, WordPress
inserts breaks and empty paragraphs inside existing grid/flex containers.

The saved Utility source has no `br` elements. Its rendered workflow becomes
two columns with333px empty slots, and formatting also distorts image-control
labels, chips, platform actions and summary controls. In a backed-up local
causal probe, enabling only1755's native flag removed all inserted formatting
items and restored the existing four-column grid with18px gaps. The four
images still have their existing explicit lazy-loading attributes. No page
content, typography, CSS, script, template or translation was edited.

Use the native metadata rather than adding a second content-filtering path.
The migration resolves the two English slugs and reciprocal German partners
through WordPress/Polylang. It requires published pages, their existing root
markers, the empty theme template and no dynamic-template assignment. An
explicit disabled metadata value is preserved as a reason to stop; an already
enabled page is a no-op. No other page family, post or product is eligible.

Before a write, retain a verified complete recovery baseline and the current
four full posts and metadata as a scoped increment, locally. `plan` is read
only. `apply` requires the reviewed state digest, which binds site identity,
all four post objects, all metadata, languages and pairings. All eligibility
checks precede mutation. Fresh planning makes a second apply a no-op; stale
plans fail. Read back the exact single-key change. Rollback requires the
current digest, original digest and exact `changed_ids`; its predicted state
must match the original digest before deleting any newly added flag.

Verify real local EN/DE1440/390 plus320 stress: native grids and labels,
image loading, hero/chapter links, tabs and arrows, summaries, contact context,
header/footer and keyboard focus. Normal and no-script states stay distinct.
Preserve raw content bytes, all unrelated metadata, languages and pairings,
privacy text/backslashes and all other pages/templates. Test stale-state,
rollback-subset and repeat-apply guards in the isolated runtime, with no
model, inquiry or mail submissions. Measure actual request/transfer behavior
separately; the metadata fix alone is no loading-speed claim. Production
backup, the sole writer's application and fresh online consumers are separate
gates. Earlier PR611/621 raster holds are not waived by this correction.
