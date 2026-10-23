# Woo preparation and private receipt retention

This worker refreshes derived engineering data. It never publishes a Woo product
or original document. Withdrawal continues to reject new work through current
Woo permission even while this worker is stopped or failing. Product drafts,
original documents and customer-owned historical reports are not deleted by
this worker.

## One writable cache for both units

The engine and `linker-engine-feed-sync.service` must both use
`LINKER_ENGINE_CACHE=/opt/linker-engine/state/cache`. The shipped units provide
that default. An `EnvironmentFile` value overrides that default, so update the
existing `/etc/linker-engine.env` explicitly. Do not assume installing a unit
has replaced an old `/root/.cache/linker-engine` value.

The sync unit keeps `ProtectHome=true`, `ProtectSystem=strict` and its existing
write allowance for `/opt/linker-engine/state`, `/var/log` and `/run/systemd`.
Do not make `/root` writable or disable `ProtectHome` to reach private receipts.
The script refuses an implicit, relative or resolved outside-state cache,
including a cache/private-data symlink that escapes the managed cache.

`--cache-preflight` creates and removes a private temporary SQLite database in
the actual cache directory. It checks journal/transaction writes; if the real
receipt database exists, it additionally obtains a write transaction and rolls
back an empty DELETE. It does not expire receipts, fetch Woo, restart a service
or claim/ack a preparation job. Deployment requires this check inside the
worker's real namespace. Neither unit adds a blocking cache `ExecStartPre`:
GC configuration must not prevent the worker from preparing data or restarting
an otherwise healthy engine. A failed check keeps the deployment unaccepted.

Normal sync and `--cleanup-receipts` expire only rows of
`cache/private/selections.sqlite` whose `expires < current UTC Unix second`.
The one-minute timer runs cleanup even when there is no pending Woo job. This
gives receipts their existing 24-hour usable lifetime and removes expired rows
on the next healthy timer pass. Missing/unreadable cache, a readonly/locked or
invalid database and SQLite errors are logged to the journal and produce a
nonzero exit. A one-second SQLite lock wait yields to the next minute's retry.

GC failure does not skip this pass's Woo claim/build/loaded-readback/ack. A
successful preparation alongside failed GC still exits nonzero. A failed
retention step therefore cannot look successful or prevent an independent
publication update. The sync unit intentionally has no cache `ExecStartPre`.

## Deployment sequence

This is a deployment contract, not evidence that migration or retention has
already run. Follow the repository's backup, rollback and retention rules.

1. Read the actual running version, executable, installed unit definitions,
   environment-file location, service user and active cache path. Output only
   the cache variable, never the complete environment or credentials. Preserve
   the current environment/unit/script definitions as part of the rollback
   metadata. Read the loaded engine source/compatibility versions through the
   authenticated service seam.
2. Before copying data, retain the required current backup. Stop the old engine
   and its feed timer/worker so no SQLite or cache writes are in flight. Copy
   the complete existing cache to `/opt/linker-engine/state/cache`, including
   any SQLite journals/WAL files and existing PVGIS/roof cache data. Check file
   counts/content hashes and SQLite integrity. Preserve the old source cache
   for this migration's rollback; do not delete customer data to make room.
3. Set the existing environment file's `LINKER_ENGINE_CACHE` to the new path.
   Preserve all other fields. Set ownership for the actual service user and
   retain private-directory 0700 / selection-database 0600 protection. Do not
   print the environment file or create a repository copy containing secrets.
4. Install this exact `sync-feed.py` at the stable path
   `/opt/linker-engine/ops/sync-feed.py`, together with both service definitions
   and `linker-engine-feed-sync.timer`. A release-tree update alone does not
   replace the stable worker or installed units. Install the script before
   running its new preflight option. Validate the full installed units:

   ```sh
   systemd-analyze verify \
     /etc/systemd/system/linker-engine.service \
     /etc/systemd/system/linker-engine-feed-sync.service \
     /etc/systemd/system/linker-engine-feed-sync.timer
   ```

5. Test SQLite writes inside the sync unit's actual protection boundary. With
   the shipped units' root service user, the following transient check uses
   the same environment file and filesystem restrictions; if the installed
   unit specifies another User/Group or additional namespace restrictions,
   reproduce those too. Do not substitute a root-shell write outside the unit.

   ```sh
   systemd-run --unit=linker-engine-cache-check --wait --pipe --collect \
     --property=Type=oneshot \
     --property=Environment=LINKER_ENGINE_CACHE=/opt/linker-engine/state/cache \
     --property=EnvironmentFile=/etc/linker-engine.env \
     --property=NoNewPrivileges=true \
     --property=PrivateTmp=true \
     --property=ProtectHome=true \
     --property=ProtectSystem=strict \
     --property='ReadWritePaths=/opt/linker-engine/state /var/log /run/systemd' \
     /usr/bin/python3 /opt/linker-engine/ops/sync-feed.py --cache-preflight
   ```

   Require exit 0 and a passed message naming the new cache's actual receipt
   path. Check that `.receipt-preflight-*` directories were removed. If the
   receipt database has not yet been created, record that explicitly; a
   successful future-directory write is not proof of an existing file's expiry.
6. Reload unit definitions, start the engine and verify its actual process
   reads the new cache. This prints only the one approved path value:

   ```sh
   systemctl daemon-reload
   systemctl start linker-engine.service
   python3 - <<'PY'
   import pathlib
   import subprocess
   pid = int(subprocess.check_output([
       'systemctl', 'show', '--property=MainPID', '--value', 'linker-engine.service'
   ]))
   values = pathlib.Path(f'/proc/{pid}/environ').read_bytes().split(b'\0')
   print(next(value.decode() for value in values
              if value.startswith(b'LINKER_ENGINE_CACHE=')))
   PY
   ```

   Require the new cache value, a healthy service and the actual expected
   loaded source/compatibility/prepared-products readback. Configuration text
   or disk files do not prove the running process loaded them.
7. Enable/start the timer. Require two real scheduled worker invocations with
   changed start/exit timestamps, including a no-pending-job pass. Inspect
   `Result`, `ExecMainStatus`, `LastTriggerUSec`, `NextElapseUSecMonotonic` and
   journal entries. Each successful GC entry names the actual SQLite path and
   deleted-row count. A manual `--cleanup-receipts` run can help diagnosis but
   does not prove periodic execution. Preserve this small readback in the
   acceptance evidence. When no expired rows exist, record zero rather than
   inventing an observed production deletion; native SQLite fixtures prove
   the expiry boundary and preserved current rows.
8. Confirm current Woo jobs were acknowledged only after the process loaded
   their source generation, and rerun the emergency EcoFlow withdrawal/PDF
   checks. Only then can the deployment's periodic-retention gate be reported
   complete. Installing a timer or passing local pytest is insufficient.

## Rollback

Stop the timer/worker and engine before restoring a consistent previous
code/feed/contract pair and its matching environment/unit definitions. Restore
the preserved original cache path or its verified recovery copy; do not combine
SQLite files from different snapshots. Reload units and read back the actual
runtime/cache and withdrawal protections again. The migration's extra cache
copy stays bounded to this rollback need and is reclaimed only after the
required accepted recovery point replaces it, under the repository's retention
rules.
