# Load governance increment 2026-11-05: partial-read byte-hash cache

Companion to `docs/research/2026-11-04-load-governance-readback.md` §1.2's
residual point. Production before/after measurement of the same call.

**Result: `Publication::library_read()` 1.807s → 0.177s wall (10×), verified
on production after the deploy.**

## Residual fixed

The `/downloads/` library listing and the PDP's FAQ citation read hashed every
hosted PDF on each cold call (`begin_read()` without the cache). They could not
just enable the manifest's cache: its write-back replaced the option with only
the current read's files, so a partial projection would have evicted every
other document. PR947 added a partial mode to `DocumentFiles::begin_read()` —
reuse across requests, merge on write-back; the full manifest still forgets
removed files, and `allows_document()` keeps its uncached download
authorization. PR948 fixed the new test helper's phpcs docblock/alignment.

## Production evidence

- Baseline (2026-11-05, before): `library_read()` wall **1.807s**,
  88 products / 147 documents.
- After deploy `20261105T061939661046Z-9b54f756f` (main with PR947+948):
  **0.177s**, same 88/147 result. Post-deploy routes `/`, `/de/`,
  `/de/datenschutz/`, `/faq-download/` all 200; LiteSpeed purged by the deploy.
- The deploy's final `verify site` step failed on a local proxy tunnel
  (`Tunnel connection failed: 503`), not on the site; the route sweep above is
  the actual read-back.

## Process note (corrected in-flight)

PR947 was merged while its commerce lane was red: the CI watch pipeline
(`gh pr checks --watch | grep | tail && gh pr merge`) lacked `pipefail`, so the
failure was masked by `tail`'s exit 0. The red step was the new test helper's
phpcs docblock/alignment; fixed and merged as PR948 with real exit-code
verification. Subsequent watches run with `set -o pipefail`.

## Other residuals checked this round

- launchd `com.linker.planner-maintenance` now points at the current release
  (`releases/2a46efe5dadb…`); the stale in-memory plist from 11-04 is resolved.
- Planner native retention plans 19 unreferenced blobs (8.3 MiB, from today's
  delete test and release) — reclaimed by the scheduled 02 UTC native
  maintenance; no manual sweep needed or run.
- Tracked-file credential scan (keys/tokens/private-key patterns, excluding
  vendor/locks): zero hits.
