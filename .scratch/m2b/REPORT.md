# M2 apply report (2026-10-16, live)

Read-only plan: `.scratch/m2b/plan-live-m2.txt` (exit 0; byte-identical to the
offline rehearsal `.scratch/m2/rehearsal-plan.txt`). 43-row table check:
`.scratch/m2/check-m2-table.py` → `43 rows checked, 0 failure(s)`.

Pre-apply backups on the host: `~/m2-pre-apply-20261016-034844.sql.gz`
(wp_posts + wp_postmeta, mysqldump direct, gzip -t verified — `wp db export`
is silently broken on this host), plus `~/n15-pre-faq-import-postmeta-20261016.sql.gz`
and the local `~/de-linker-data/cutover-20261015-1736/` set.

## Apply

- Run 1 (`.scratch/m2b/apply-live.txt`): content/title/SEO steps wrote
  (30 steps), then the German-source phase died: the 125 KB header partial in
  base64 as one ssh argument → `/bin/bash: Argument list too long`, exit 1.
  No source meta, no alt, no slug, no state had been written.
- Fix (`eval_php_embedded`): payload embedded in the PHP text, which rides
  stdin; verified against the host with a 130 KB probe.
- Run 2 (`.scratch/m2b/apply-live-rerun.txt`): a transient SSH drop at 6917
  ("Connection closed"), all steps idempotent, no writes lost.
- Run 3 (`.scratch/m2b/apply-live-rerun2.txt`): exit 0 — 46 steps
  "nothing to do"; **german source metas: 28 values refreshed**;
  **media alts: 30 refreshed**; 4 slugs already; **translation state: marked 23**.

## Verify (`.scratch/m2b/verify-live.txt`)

`verify: OK`, exit 0. Only output: the expected note `linker-planer-de: seo
title meta is absent (the i18n import wipes it)` (known, D4 of the inventory).

## Regression (read-only)

- Full-surface sweep (`.scratch/m2b/regress-grep.php`): 101 published
  surfaces + source metas + alts + drafts: **0 hits** of the six old names
  and four old addresses.
- Rendered samples (`.scratch/m2b/renders.sh`): 12 faces 200, 0 old tokens;
  new sentences render (listed in the PR body); retired addresses 301 to the
  language-correct new pages.
