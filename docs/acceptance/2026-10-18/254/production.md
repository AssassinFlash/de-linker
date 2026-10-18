# Claude deployment and readback

Only Claude runs these commands after review and merge. This implementation session has not deployed, merged or written production. Production WP-CLI runs over the existing SSH alias; no secret is copied into this repository.

The file deployment streams its own database snapshot to this Mac and retains the preceding file release. The full incremental backup below precedes the release and its address/title/link data migration (AGENTS.md §5, layered backup ruling). Keep the printed local backup/snapshot paths with the deployment evidence.

```bash
wp254() {
  ssh hostinger-de-linker /usr/local/bin/wp \
    --path=/home/u388076051/domains/de-linker.com/public_html "$@"
}

# Full incremental backup for the data migration, then the file release.
# Deploy also takes its own automatic database snapshot on this Mac.
just cutover backup
just cutover deploy

# Deploy runs present once. Retain that first pre-release presentation backup
# locally before the post-migration present replaces its last-run option.
ticket254_present_backup="$HOME/de-linker-254-present-$(date -u +%Y%m%dT%H%M%SZ).json"
wp254 option get linker_commerce_present_backup --format=json > "$ticket254_present_backup"

# Review the complete dry run before applying the data changes. Slugs and the seven curated title/name/SEO sets accept only their reviewed old or new values; resolve any reported drift before retrying.
wp254 linker-i18n german-urls --dry-run --user=1
wp254 linker-i18n german-urls --apply --user=1
wp254 linker-commerce present --allow-stale --user=1
wp254 rewrite flush --user=1
```

The file-publish step uses native `present --allow-stale`: a freshly installed volume is necessarily newer than the previous cache. This permits publication to proceed to the planned data migration and native browser compilation; final cache/presentation verification is still mandatory. Each `present` stores only its preceding run, so retain the local JSON export above as the pre-release rollback point.

In the native WindPress admin, open Settings → Performance → Generate. Wait for the generated timestamp and cache size to update, then clear the site's page cache. Do not run cache compilation alongside the acceptance fixtures. The migration invalidates only this WordPress site's option-cache keys before rebuilding native rewrite rules; no shared Redis database flush is needed.

If dry run reports unreviewed drift, stop application and represent the resolution in reviewed repeatable migration code/manifest before retrying. Do not adjust production fields by hand merely to satisfy the preflight. If dry run stops after the file release, restore its presentation/files using the rollback steps below while the conflict is resolved; skip migration rollback when no migration apply occurred.

```bash
wp254 linker-commerce check --user=1
wp254 linker-i18n german-urls --verify --user=1
just cutover verify
```

The deploy smoke now uses the existing model-only product paths `/product/saj-b2-10-0-hv1/` and `/de/produkt/saj-b2-10-0-hv1/`. Both are valid before and after this data migration. Do not run the older all-data migration batch merely to install this ticket.

Read back the entire reviewed public route set through Apify, using its existing environment token. The input and the local acceptance report document the exact route expectations. Verify the sitemap index and every child sitemap, the German language switch, canonical/hreflang/share URLs, titles and every historical first-hop 301. Reproduce the public Apify readback with these commands, retaining the run ID printed by `start`:

```bash
python3 docs/acceptance/2026-10-18/254/live-readback.py start
python3 docs/acceptance/2026-10-18/254/live-readback.py status --run RUN_ID_FROM_START
python3 docs/acceptance/2026-10-18/254/live-readback.py collect --run RUN_ID_FROM_START --output /tmp/254-live-readback.json
```

The script uses only the existing APIFY_TOKEN environment file and GET requests to the public site. Compare its first responses and metadata against the latest `round2/route-results.json`; every changed public old path must be 301 to its final new path and each canonical path must be 200. The XML responses must contain the new German locations and preserve the English set. The script was also exercised read-only before deployment, when historical addresses still served the original site. Account/detail/reset/logout states require the corresponding authorized customer session and valid native keys/nonces. Logout retains Woo's native action transition after the compatibility 301; it is not a separate document for title uniqueness. No test mail is sent from production.

## Rollback order

Use the same reviewed file release while restoring its data; its language-pair lookup still recognizes the migrated pages.

```bash
wp254 linker-i18n german-urls --rollback --dry-run --user=1
wp254 linker-i18n german-urls --rollback --apply --user=1
wp254 option update linker_commerce_present_backup --format=json < "$ticket254_present_backup"
wp254 linker-commerce rollback --user=1
just cutover rollback-deploy
wp254 rewrite flush --user=1
```

Rebuild native WindPress cache for the restored release, clear page cache, run `linker-commerce check`, and read back the original EN/DE routes and page types. The address migration keeps its first originals across repeated applies and rollbacks. A missing language pair, occupied destination, or an owned field changed outside the migration stops before writing; resolve the reported conflict before retrying. If application fails after a native write, use the retained originals to restore it before switching files back.
