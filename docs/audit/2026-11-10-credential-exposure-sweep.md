# Credential-exposure sweep (read-only, 2026-11-10 21:00 local)

Domain-D item "凭证材料意外输出/入库问题核查处理": a read-only sweep of the
production webroot, uploads, options, postmeta and order notes for secret
material. Nothing was modified.

## Webroot and uploads

- No `.env*`, `*.pem`, `*.key`, or config backups anywhere in the webroot
  (maxdepth sweep) — nothing to expose.
- `wp-content/uploads` top level holds no `.sql`/`.zip`/`.gz`/`.php` files —
  only media directories and small tool directories (windpress, wc-logs).
- `.htaccess` present (3 KB, Nov 1) — standard guard.

## Database

- `wp_options` secret-pattern sweep (API keys, `sk-` tokens, `apify_api_`,
  `ghp_`, private-key PEM headers, excluding transients): **one hit** —
  `seopress_instant_indexing_option_name`, which is the site's own licensed
  SEOPress PRO Bing indexing key stored by the plugin's native settings
  path. This is the plugin's designed storage (owner-licensed plugin per
  the 2026-10-09 ruling), not accidental output; it is not a third-party
  credential and not exposed in customer-visible responses.
- `wp_postmeta` sweep: **0 hits**.
- Order/comment notes sweep: **0 hits**.

## Verdict

No credential material is accidentally exposed or persisted. The only
secret-shaped value in the database is the licensed plugin's own setting
in its native location. No action required; recorded per the domain-D
brief ("不再暴露秘密" — nothing found exposing any).
