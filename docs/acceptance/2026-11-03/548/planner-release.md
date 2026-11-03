# Planner release 2026-11-03: `prepared` on products/current (fix ab368fd0b)

Executor: teammate `planner-release`. Completion criterion (sole): production
read-back of `prepared: true` on `POST /wp-json/linker/v1/planner/rpc/products/current`.

**Result: PASS — production read-back `prepared = true` (JSON `true`, previously `null`).**

## What shipped

Engine fix `ab368fd0b0769e5660adf6cc2062166055bff422` — `fix(engine): expose
prepared on the planner product catalog (#868)`, one line in
`services/engine/src/linker_engine/planning/product_sources.py` (`"prepared": True`
at line 505 of the release copy) — pushed to the production planner pair via a new
immutable planner release.

- New release (current): `/opt/linker-planner/releases/08256b932b3bec053a221c95d328152fe318859c86b5872600f518ec1c3946e6`
  (name = sha256 of the revision string `ab368fd0…422`, matching the existing
  naming convention verified against the old release)
- Rollback (previous, retained): `/opt/linker-planner/releases/ca2d1fb7814b6ff2c91851109e4a8e9b93ede164cd6817f76f4109bb17dff19f`
- Old previous `aa0610a2…` was retired by `planner_release.py activate`'s built-in
  retention (keeps current + exactly one rollback). Nothing was deleted by hand.
- `runtime_sha256`: `4ac94366fa1187c6317c904df42e73eb6cc71160bb1ac40bb50f1aff12ff25e8`
  (old: `f8959947…`; change confirms new code frozen). `storage_binding` unchanged
  (`f91b6338…` — same store, `storage_schema_version` 5 both sides, no migration).

## Backup (before any production write)

`workspace.sqlite` (438,272 bytes) copied via SQLite online-backup API on the VPS
→ scp to local `~/Documents/de-linker-vps-backups/2026-11-03-planner-release/workspace.sqlite`,
sha256 `43976fe70913c5430fe6eb7d947620df1ff0953059aa4ae0eb62bafbcdaa4555`.
Purpose: pre-activation recovery point for this release; owner: this ticket;
recycle when the lead confirms the release stable (or at the next planner
release, which takes a fresh point). VPS `/tmp` copy deleted after scp.

## Execution record (commands and key outputs)

All VPS work via `ssh linker-services` (root). Repo checkout: main @ `350ebed62`
(verified `ab368fd0b` is an ancestor; `ops/planner_{source,release}.py`,
`ops/legacy_release.py` byte-identical between ab368fd0 and HEAD, so the
`planner_source.py` self-identity check passes).

1. **Recon / status (old release healthy before start)**
   `python3 $OLD/ops/planner_release.py status $OLD/.deploy/spec.json` →
   `control {draining:false, pending:0}`, `ready.pid 485580`,
   identity runtime `f8959947…`. venv = `uv sync` layout
   (`linker_engine.pth` → release's own `src/`), uv 0.13.0 at `/root/.local/bin/uv`.
2. **Source closure → candidate** (from local repo):
   `python3 services/engine/ops/planner_source.py --repository . --revision ab368fd0b0769e5660adf6cc2062166055bff422 | ssh -T linker-services "mkdir '$CAND' && tar -xf - -C '$CAND'"`
   → manifest revision matches, 325 blob entries.
3. **First prepare attempt failed (self-inflicted, no production impact):**
   directory named with the 40-hex git sha → `ValueError: release must be a
   retained owned directory` (operator requires 64-hex name; `HASH = re.compile(r"[a-f0-9]{64}")`).
   Fix: renamed to sha256(revision) `08256b93…c3946e6`, rebuilt `.venv` at the
   final path (`/root/.local/bin/uv sync --locked --no-dev --project $CAND`),
   rewrote `.deploy/spec.json` (only `release` path differs; port 8911, prefix
   `linker-planner`, user `linker-planner`, 30s/30s budgets), copied
   `runtime.json` + `worker.json` from the old release.
4. **Prepare** (exit 0):
   `python3 $CAND/ops/planner_release.py prepare $CAND/.deploy/spec.json --source-environment $OLD/.deploy/http.env --publication-url https://de-linker.com/wp-json/linker/v1/publication/manifest`
   - `--source-environment` = the old release's `.deploy/http.env` (carries
     `GENIE_SERVICE_TOKEN`, `LINKER_ENGINE_FEED=/opt/linker-engine/state/feed.json`,
     `LINKER_ENGINE_COMPATIBILITY=/opt/linker-engine/state/compatibility.json`).
   - Output: `prepared: …/08256b93…/.deploy/spec.json`; executable
     `runtime_sha256 4ac94366…`, `storage_schema_version 5`, 13
     `project_input_contracts`. Prepare ran `check_source` (manifest verified),
     source-loader probe under the service UID, DB schema check, input floor,
     `systemd-analyze verify` on both rendered units, and froze `prepared.json`.
5. **Activate** (exit 0):
   `python3 $CAND/ops/planner_release.py activate $CAND/.deploy/spec.json` →
   ```json
   {"current": "/opt/linker-planner/releases/08256b932b3bec053a221c95d328152fe318859c86b5872600f518ec1c3946e6/.deploy/spec.json",
    "identity": {"execution_key": "3c697c43bbbdbbb2bdc3f58c9551215f957dc10222c56e5e2970ba15c148902d",
                 "runtime_sha256": "4ac94366fa1187c6317c904df42e73eb6cc71160bb1ac40bb50f1aff12ff25e8",
                 "storage_binding": "f91b6338e5204a220d7163fde4277f900fc0c12ca913edec9d7c1560f0eb06d4"},
    "previous": "/opt/linker-planner/releases/ca2d1fb7814b6ff2c91851109e4a8e9b93ede164cd6817f76f4109bb17dff19f/.deploy/spec.json",
    "schema_version": 1}
   ```
6. **Post-activation service checks (all green):**
   - `status` → ready pid `522001` (`production-linker-planner`),
     control `{draining:false, pending:0, quiescent:false}`,
     identity runtime `4ac94366…`.
   - `systemctl is-active linker-planner-http.service linker-planner-worker.service`
     → both `active`.
   - `curl http://127.0.0.1:8911/health` → `{"status":"ok"}`.
   - `journalctl -u linker-planner-http.service -u linker-planner-worker.service
     --since "-4 min" -p warning` → empty (no warnings/errors).
   - `/opt/linker-planner/releases/` contains exactly `08256b93…` + `ca2d1fb7…`.

## Production read-back (the completion criterion)

wp-admin cookie login (`857558227@qq.com`) → `admin-ajax.php?action=rest-nonce`
→ authenticated POST (headers `X-WP-Nonce`, `Origin: https://de-linker.com`,
`Referer: https://de-linker.com/wp-admin/`, body `{"schema_version":1}`):

```
POST https://de-linker.com/wp-json/linker/v1/planner/rpc/products/current → 200 (8.9 s)
```

```json
{
  "prepared": true,
  "schema_version": 1,
  "compatibility_origin": "woocommerce",
  "loaded_engine_version": "0ee9d0e2e0648b6fbfe96d9dbb79231065139080f22daf0146cf56ff496b4e5f",
  "loaded_source_revision": "113e8ad236d47e61d7b8af920fe6e0610d146b93bb4c4e0d4de477a0b9097534",
  "products": [ … 85 items … ]
}
```

`prepared` was `null` before this release; it is now JSON `true` in production.
(Nonce/cookie scratch files deleted after the check.)

## Rollback path (not needed)

`ssh linker-services 'python3 /opt/linker-planner/releases/ca2d1fb7814b6ff2c91851109e4a8e9b93ede164cd6817f76f4109bb17dff19f/ops/planner_release.py rollback /opt/linker-planner/releases/ca2d1fb7814b6ff2c91851109e4a8e9b93ede164cd6817f76f4109bb17dff19f/.deploy/spec.json'`
(drains, stops the new pair, restarts ca2d1fb7, restores selection.json).
Pre-change DB recovery point kept locally (see Backup).

## Resource report

- VPS `/`: 5.1G used / 43G free. New release 348 MB (source + fresh
  non-hardlinked `.venv`), previous retained 7.7 MB; `aa0610a2…` retired by the
  operator's own retention rule. No manual deletions.
- Local: +438 KB backup (`~/de-linker-vps-backups/2026-11-03-planner-release/`,
  single recovery point, recycle condition above) + this document.
  VPS `/tmp` scratch and local cookie/nonce files removed. No processes or
  terminals left running; no repo files committed.
