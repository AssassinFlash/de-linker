# LiveCanvas "Global JavaScript Code" partial (post 30) is an empty stock slot (2026-11-04)

Finding of the 2026-11-04 full-matrix acceptance pass (matrix row 30,
`empty-content-local-and-production`): the LiveCanvas partial titled
"Global JavaScript Code" (`lc_partial` post ID 30, slug
`global-javascript-code`, meta `is_global_js = 1`) has `LENGTH(post_content)
= 0` on production and on the local snapshot. This note records what the
partial is, the evidence that it was never populated, and why nothing is
restored. No production write.

## What the partial is in LiveCanvas

LiveCanvas manages site-wide custom JavaScript through this one partial:

- The LC editor's save action writes the editor panel's global-JS field into
  the partial: `lc_update_partial_by_cf( 'is_global_js', … )`
  (`livecanvas-plugin-index.php`, `lc_ajax_save_page_func` context). If the
  partial does not exist it is created with the title "Global JavaScript
  Code".
- The partial's content is printed verbatim on every page at `wp_footer`:
  `<script id="lc_script_tag" type="module">…</script>`
  (`lc_global_script_tag`, `livecanvas-plugin-index.php`).
- LC's own partial library REST listing deliberately hides this title from
  the editor's block library (`modules/rest-api.php` skips posts titled
  "Global JavaScript Code"), i.e. LC treats it as a system-managed slot, not
  a content partial a user browses.

With empty content the footer tag renders as an empty `<script>` element; no
code executes from it and none is expected to.

## Evidence it was never populated

- Pre-cutover production database dump `de-linker-data/cutover-20261021-2259/db.sql.gz`
  (the old live site, before the rebuild): the `wp_posts` row
  `(30, 1, '2026-05-25 16:58:04', …, 'Global JavaScript Code', …, publish, …,
  'global-javascript-code', …, 2026-07-13 22:57:14, …, lc_partial)` has an
  empty `post_content`. The partial was created empty on 2026-05-25, modified
  2026-07-13, and never carried code on the old site either.
- The old site's page-level JavaScript lived in inline `<script>` blocks
  inside page content (the same dump's Contact page row, directly preceding
  post 30's row, carries hundreds of lines of inline JS) and in old plugin
  assets — none of it ever went through the LC global-JS editor field.
- Every later snapshot and the current production inherit the same empty row;
  nothing was lost in the rebuild or at cutover.

## Resolution

The partial is an intentionally empty stock slot, not lost content. Nothing
is restored, and no new global JavaScript is invented for it (owner
directive for this defect: do not invent global JS). The site's real
site-wide JavaScript is served by the repo's plugin/theme assets
(`plugins/*` enqueue their own JS; the WindPress volume carries the styles),
which is where the coverage contract's "global JavaScript must prove code
execution and a consumer behavior" clause applies. The acceptance matrix row
for LC partial 30 should close as not-applicable on this evidence; the
main line records that ruling with the acceptance pass.

Re-check command (read-only, production SSH):
`wp db query "SELECT ID, LENGTH(post_content) FROM wp_posts WHERE ID=30"`
— expected `0` until someone deliberately saves global JS through the LC
editor.
