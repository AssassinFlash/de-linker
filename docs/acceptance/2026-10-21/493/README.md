# #493 engine contract sync: acceptance

2026-10-21. Branch `fix/493-compat-sync` (base `origin/main` 2cdc3e24). Not merged or deployed.

The engine reads its compatibility contract from
`LINKER_ENGINE_COMPATIBILITY=/opt/linker-engine/state/compatibility.json`
(`services/engine/src/linker_engine/app.py`), but only `state/feed.json` had a
sync. A contract change shipped with the site stayed stale on the VPS until a
hand `scp` and restart.

## Live evidence (2026-10-21 08:32 UTC)

`GET https://de-linker.com/wp-json/linker/v1/engineering-feed` returned the
top-level keys `compatibility_version`, `generated_at`, `overlay`, `products`,
`schema_version` — no `compatibility` key. `compatibility_version` was
`5d2a85676432d1501620997a21359782defcd8aa64b644c7799eb32d054a23b8`.
`origin/main`'s `EngineeringFeed` emitted only the version. The ticket's premise
("the feed already embeds the full compatibility section") did not hold, so the
site side had to carry the contract as part of this fix.

## What changed

- `plugins/linker-commerce/includes/Products/EngineeringFeed.php`: the feed
  envelope carries `data/compatibility.json` as `compatibility`; the key is
  absent when the file is unreadable, and the rest of the feed still serves.
- `EngineeringFeedController.php`: the OPTIONS schema names the key. The
  class/schema descriptions name the contract. Catalogs regenerated
  (`.pot`, German `.po`, `.mo`).
- `services/engine/schemas/feed.schema.json`: `compatibility` is an optional
  object. The binding validation stays in `compatibility.schema.json`, which
  the engine's `Compatibility.load` applies. Optional is what lets the new
  engine accept both the pre-#493 and post-#493 feed during the rollout.
- `services/engine/ops/sync-feed.py`: one fetch now refreshes both files:
  feed probe (`Products.load`), atomic swap; extract the contract, check its
  `version` against `compatibility_version`, probe (`Compatibility.load`),
  atomic swap beside the feed; one restart when anything swapped. Feed and
  contract fail independently; the contract is only attempted after a feed
  swap, so a rejected feed keeps both. Each outcome is a separate log line.
- Units and timer: same nightly run, comments/Description updated only.
- Deploy notes: `tools/cutover/src/linker_cutover/steps.py` and
  `docs/specs/17-cutover.md` name both host files and the stable script copy.
- `docs/specs/8-engineering-data.md`: target shape 5 carries the contract.

## Verification

| Check | Result |
| --- | --- |
| `services/engine`: `uv run --locked pytest -q` | 149 passed (7 in `tests/test_sync_feed.py`, 1 new feed-schema test) |
| `services/engine`: `ruff check .`, `ruff format --check .`, `mypy .` | clean, 45 files |
| `tools/cutover`: `pytest`, ruff, mypy | 159 passed, clean |
| `plugins/linker-commerce`: PHPUnit | 1316 tests, 5972 assertions, 155 skipped |
| `plugins/linker-commerce`: PHPCS, PHPStan | clean |
| `i18n-validity`, `i18n-coverage`, `german-copy`, `internal-home-urls` | clean |
| `git diff --check` | clean |

The sync harness is a local HTTP server plus the engine's real loaders in the
probe subprocess, so `fetch -> parse -> validate -> atomic write` is exercised
end to end. Cases: both files swap on success; contract rejected (and contract
version mismatch) keeps the old contract while the feed swaps and the engine
restarts; feed rejected and fetch failure keep both without a restart; a feed
without the key (today's live shape) swaps the feed and keeps the old contract;
the staging directory holds only the two target files afterwards.

`test_the_written_contract_keeps_the_shipped_contracts_content_hash` pushes the
shipped contract through the sync and asserts the written file's `version` is
the sha256 of the contract minus that key (sorted keys, compact separators) —
the ticket's "VPS contract version = content hash（对 {schema_version, pairs, requirements} 规范 JSON：sort_keys、紧凑分隔符、ensure_ascii=False，见 8-decisions §6）" condition, proven locally.

Manual regression against the live pre-deploy feed (temp state directory, no
production write): `feed refreshed (106 products, ...)`; `feed carries no
compatibility; previous contract preserved`; `engine restarted on the fresh
data`; feed file swapped, contract file byte-identical, exit 1.

Manual regression with the live feed shape plus the shipped contract:
`compatibility refreshed (version 5d2a8567…, 248 pairs)`, both files swapped,
version equal to the shipped content hash, exit 0.

## Deploy prerequisite

The timer runs the stable copy `/opt/linker-engine/ops/sync-feed.py`; it is not
installed by `just cutover services` (that ships `current/ops/` only). Copy
`services/engine/ops/sync-feed.py` (and, if changed, the unit files) to the
stable paths once. Order: services first, then the site. After that, a contract
change reaches the engine on the next nightly run or a manual
`systemctl start linker-engine-feed-sync.service`; no `scp` of
`compatibility.json`.

Post-deploy check (not run here; no deployment from this branch): read back
`state/compatibility.json` on the VPS and compare its `version` with the site's
feed `compatibility_version` and with `sha256` of the contract minus `version`.

## Inner two-axis review

Standards axis: no blockers. Spec axis: no functional blockers; its
regression-record finding is this file, and the stable-copy/deploy note was
added to `steps.py` and spec 17. Fixed from the nits: stale envelope
descriptions (and their catalogs), the redundant swap condition, the staging
cleanup assertion, and the shipped-contract identity test.
