# Confirmation CTA centering + recalculate entry, production 2026-11-06

Executor: main session. Two fixes shipped in one cutover deploy
(`20261106T042001955109Z-9ccbe51ab`, EXIT=0, standard verification passed,
only the latest backup set retained).

## 1. Centered confirmation CTA (visual defect from owner screenshot)

- Root cause: the shared rule in `content/windpress/auth.css` carried
  `justify-self: start` for the contact form AND the proforma success card;
  the success card is `display:grid; justify-items:center`, so the CTA
  ("Create an account with this email") sat flush-left under centered text.
- Fix (one line, scoped): `#tv-woo-b2b-checkout .linker-proforma-success
  .linker-form-primary { … justify-self: center; }`. Contact form intent
  unchanged. Commit `9ccbe51ab` on main.
- Production proof: WindPress cache regenerated (`just
  windpress-compile-production`, mtime 1793849540 → 1793939159, body hash
  changed), and the served `wp-content/uploads/windpress/cache/tailwind.css`
  now contains exactly that rule with `justify-self: center` (the only
  `justify-self:center` in the file; start variant of the shared rule is
  overridden by the more specific scoped one).
- Pixel screenshot of the rendered confirmation card was not captured this
  session; the CSS-level evidence above is the production readback. The
  confirmation page used for any later visual check: existing record 8457
  (no new inquiry was created, no mail sent).

## 2. Recalculate-energy entry (PR #971, merged 3c30a8333)

- Decision (owner-delegated): no implicit recompute (spec 609 contract
  unchanged); on `report_inputs_changed` the error panel offers
  **Recalculate energy / Energie neu berechnen**, switching to the scenario
  view whose current inputs are already loaded. Old results stay frozen and
  selectable; a consistent historical pair always exists.
- Verification before merge: planner types/lint/prettier clean, 297/297
  tests, i18n compile, build::check all three packages; full CI green.
- Production readback: `planner-core--iUcr9H9.js` contains
  `Recalculate energy` (server file and HTTPS response); `Energie neu
  berechnen` present in the deployed `linker-tools-de_DE_formal.mo` and its
  JSON bundle.
- Process note: the first CI failure was prettier-only (local scope had
  missed `lint:format`); fixed in `10160b55e`. An interrupted earlier deploy
  left a staging state and a snapshot reservation; both were cleared without
  touching production (nothing had been uploaded), then resume-deploy
  completed cleanly.

## Cleanup / resources

- Temporary logs (/tmp deploy/CI files) removed; test orders 8615/8618 were
  already deleted before this batch; no new orders or mails were created by
  this batch's readback. Local new content: this record only.
