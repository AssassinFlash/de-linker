# Planner release 2026-11-05: production project delete (PR934 readback)

Executor: main session. Completion criterion (sole): production read-back of a
real UI project delete — `projects/delete` 200, the project gone from list and
workspace DB, and no new mail jobs.

**Result: PASS.**

## Defect

PR934's project delete shipped to WordPress and `/opt/linker-engine`, but the
production delete request returned `404 {"error":{"code":"not_found"}}` and the
project survived (evidence: real UI click with network capture, 2026-11-05
morning; planner journal shows the request).

## Root cause (evidence, not theory)

The WordPress gateway's write admission preflights every mutation with
`operations/replay/<path>` (`plugins/linker-tools/includes/Planner/Admission.php`,
`send()`), and forwards any 4xx replay reply verbatim. The private planner
pair — `linker-planner-http` / `linker-planner-worker`, loopback 8911 under
`/opt/linker-planner`, which is what WordPress actually talks to — was still
running release `afabd02348…`, activated **2026-11-04 18:48 UTC**, nine minutes
before PR934 merged (10:57 CST = 02:57 UTC). That release has no
`projects/delete` replay branch, so `HttpReplay.read` raised `NotFound`:

```
journalctl -u linker-planner-http:
Nov 05 03:47:19 "POST /planning/operations/replay/projects/delete" 404 Not Found
```

The 03:21 UTC engine deploy restarted `linker-engine` only; the planner pair is
a separate release namespace (docs/specs/548-service-hosting.md) and was not
touched. Nothing was wrong with PR934's code.

## Release (same reviewed channel as 2026-11-03)

- Backup first: `workspace.sqlite` (442,368 bytes, sha256
  `7fd70b4c5444e1f8dff5583c0b3855c5ab94850791748db907fbb0ed3f589916`) via
  SQLite online backup → `~/Documents/de-linker-vps-backups/2026-11-05-planner-release/`.
  Recycle at the next planner release (fresh point) or on confirmed stability.
- Source: main `f02e56d8e183e4cb153631ce4e01f29e3469c19f` (PR934/937/938 in),
  via `ops/planner_source.py` (325 blobs, manifest revision verified).
- New release (current):
  `/opt/linker-planner/releases/ca784637c19afc67233cea2a1cd2d0ea57f2496b67d652197ac8886cf151b45e`
  (sha256 of the revision string, per naming convention).
- `runtime_sha256` `8c936c5ea000d85ec96defbda0299ee233b68cbc6743dad6eb8a4d2a17142e4d`,
  `storage_binding` `f91b6338…` unchanged (schema 5, no migration).
  13 `project_input_contracts` prepared; prepare/activate/status all exit 0.
- Rollback (previous, retained by the operator's own retention):
  `afabd02348e06ba1c81e0d4bab45ad841a82de1389a1f8eb7e135fd2847a9c69`.
  Native rollback:
  `ssh linker-services 'python3 /opt/linker-planner/releases/ca784637…/ops/planner_release.py rollback /opt/linker-planner/releases/ca784637…/.deploy/spec.json'`.

## Production read-back (the completion criterion)

Real browser UI, logged in as the production test customer `delete934`
(user 50), owner `user:wp:1:user:50`, project `b5d00dd2e02c48f59e521f4608bbbd1e`
("Country rule readback 2026-11-05", revision 6):

1. Click Delete → confirm dialog → Delete project.
2. Planner journal:
   `operations/replay/projects/delete` **200**, `projects/delete` **200**,
   `projects/list` **200** (04:14:33–34 UTC window).
3. Workspace DB (read-only): project row `None`; user 50 projects `0`;
   revisions `0`.
4. UI: project disappears; clean empty "Project workspace" state, no error notice.
5. Mail jobs unchanged: 288 complete + 2 canceled, 0 pending (no new rows).
6. Cleanup read back: user 50 deleted via wp-cli, `wp user get delete934` →
   invalid (gone). Browser tab closed.

## Systemic finding (recorded for the release checklist)

A "deployed to the engine" claim does not reach the planner pair: they are
separate release namespaces with separate lifecycles. Any ticket that changes
`services/engine/src/linker_engine/planning/**` consumed by WordPress must
release BOTH `/opt/linker-engine` (feed worker entry) and the
`/opt/linker-planner` pair, and read back `/planning/version` from the
planner's own port (8911), not from the engine's. PR934's acceptance read back
the wrong listener. The engine `verify --wait-worker-seconds` SSH window defect
found during that deploy is fixed by PR940.
