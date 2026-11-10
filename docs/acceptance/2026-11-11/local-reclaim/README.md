# Local reclamation (2026-11-11)

Remediation of the two over-limit findings M5 and M6 in
[`../resource-load-baseline/baseline.json`](../resource-load-baseline/baseline.json),
under the boundaries in [`docs/agents/local-storage.md`](../../../agents/local-storage.md)
and `AGENTS.md` section 0.

Raw figures and every per-item decision: [`reclaim-report.json`](reclaim-report.json).

## Headline

`~/de-linker-local` went from **179.3 GB to 13.0 GB**. 52 registered instances
were retired through `just retire --write` and 3 unregistered stale directories
were removed, taking 58 instance directories down to the 3 that are actually
running. MySQL went from 55 `linker_*` schemas to 3, Redis prefixes from 58 to
4, and the SQL footprint from 3.0 GB to 245 MB.

`~/de-linker-data` moved only **285 MB**, and the reason is worth stating
plainly: the 4.2 GB site snapshots and cutover backups are `rsync --link-dest`
hard-link trees, so each copy owns only 17–52 MB of exclusive bytes. Deleting
one frees nothing until the last link goes. Reporting a 4.2 GB saving per
deleted snapshot would have been false.

| measure | before | after | change |
| --- | --- | --- | --- |
| instance directories | 58 | 3 | −55 |
| registry entries | 55 | 3 | −52 |
| MySQL `linker_*` schemas | 55 | 3 | −52 |
| SQL data | 2 980 MB | 245 MB | −2 735 MB |
| `~/de-linker-local` | 179.3 GB | 13.0 GB | −166.4 GB |
| `~/de-linker-data` | 39.13 GB | 38.85 GB | −285 MB |
| database snapshots | 18 | 10 | −8 |
| cutover backups | 6 | 4 | −2 |
| live-site pull snapshots | 4 | 3 | −1 |
| host volume available | 1 118 GiB | 1 292 GiB | +174 GiB |

The host-volume gain exceeds the sum of the two roots because other sessions on
this Mac freed space during the same window. The attributable part is the
166.4 GB from `~/de-linker-local`.

## How the instances were removed

Every registered instance went through the sanctioned path, never `rm -rf`:
`just retire <name> --write` stops the instance, unlinks its Redis prefix,
drops `linker_<name>`, removes the directory, removes the registry entry, and
re-reads each step. Each one returned `status: retired` with a key count;
105 186 Redis keys were unlinked that way.

Evidence decisions were explicit per instance. `logs`, `mail`, `snapshot.json`
and `wordpress` were recorded as discard — WordPress core and the local mail
sink are rebuilt by `just up`, and no acceptance record cites an instance's
`wordpress/` tree.

Readback after the last retirement:

- directories, `instances.toml` keys and `information_schema` schemas are all
  exactly `{review, c222, c332}`;
- no `.lifecycle/*.retiring.json` marker remains;
- all three survivors answer HTTP 200 on their PHP ports
  (`review` 8889, `c222` 8925, `c332` 9187).

## What was deliberately kept

- **`p548`'s evidence**, because it is cited by an accepted record:
  `docs/acceptance/2026-10-25/548/woo-source-native-install.json` points at
  `p548/final-consumer/browser/record.json`, `.../legacy/verdict.json` and
  `p548/try-again-evidence/report-final.json`. Seven directories — those two,
  both `production-acceptance-*`, `geometric-production-*`, `genie` and
  `planner` — were copied to
  `~/de-linker-data/retired-instance-evidence/p548/` and 4 907 files were
  sha256-compared with zero mismatches at copy time, before the instance was
  retired. The destination holds **4 674 regular files and 2 symlinks** today
  (632 MB). Those two counts differ by 233 files that this session could not
  account for, and the source no longer exists to re-compare against — see
  "Unresolved: the p548 evidence count" below.
- **`t7`, `t9-pre-stack-backup`, `t113`**: never registered, idle since
  2026-10-09/10-12, no database. Their small unique bytes (13 product-fact
  backups, 44 mail-sink messages, a prototype pointer whose target is gone)
  were copied to the same evidence root and `diff -r` verified first. The
  warning that these are `retire`-ineligible by design: the tool refuses
  unregistered resources because their ownership is unknown, so their removal
  is recorded here as a manual act with its evidence trail.
- **`linker_probe80`** (131 Redis keys): no repository origin and no owning
  process. The rule keeps prefixes of unknown ownership rather than guessing.
- **Research evidence** under `~/de-linker-data`:
  `privacy-visual-20261021` (6.4 GB), `incident-20261022` (5.2 GB),
  `weekly-20261108` (4.6 GB), `judge-models`, `pdf`, `planner-production` and
  the rest. Their size is the point, not a leak.

## Two real defects found on the way

**Database snapshot rotation has never worked.** `snapshot._prune` walks every
recorded snapshot and raises `CutoverError` if any record is incomplete. The
ledger holds one legacy record, `db-20261106T095015Z.sql.gz`, written as
`{bytes, created, reason}` with no `sha256`/`stamp`. That single record makes
every automatic rotation abort with "preserved older snapshots", which is why
18 accumulated against a 7-day rule. This pass applied the same
`select_retained()` function offline — same code path, same rule — and deleted
8 verified files. Fixing the ledger record or relaxing the precondition is a
code change outside a reclamation and is left open.

**`retire` cannot drain an instance whose planner release points at a deleted
worktree.** `p548`'s `planner/runtime-releases/*/.venv` symlinks target a
worktree removed in October, so `engine_project()` refuses to verify the
selection. The planner state was preserved first, then `runtime.json` was
removed so the instance retired as stateless. Any instance built before a
worktree cleanup will hit this.

## Blockers that were fixed rather than skipped

| item | symptom | resolution |
| --- | --- | --- |
| `g511` | `registered port still in use` | port 9210 has been held by an unrelated QQ process for weeks; its three ports were reallocated inside the registry lock to a measured-free 9450/9451/9452, then it retired through the same path |
| `g511` marker | `registration changed; retirement stopped` | the failed attempt left a marker with the old ports; after confirming directory, schema and processes were intact, the stale marker was archived and the retirement re-run (10 614 keys) |
| planner group | `ModuleNotFoundError: pydantic` | this worktree's `services/engine/.venv` had never been synced; `uv sync --locked --offline`, then serial retries because the drain control call takes ~9 s against a 10 s budget |
| `p548` | `owned engine release selection could not be verified` | see the defect above |

## What this changes about the baseline verdict

M5 was recorded as `OBSERVATIONAL - OVER LIMIT` with the note that reclamation
was the owner's decision. That decision is now executed and the boundary holds
at 3 directories for 3 running instances, which is exactly what
`docs/agents/local-storage.md` allows.

M6 is at the boundary for database snapshots (10 files: 7 by the 3+7+1 rule,
2 held by stale cutover-workspace references, 1 legacy record) and below it for
site copies. It cannot be tightened further without deleting a recovery point
the rule requires.

## Left open

- The snapshot ledger still contains the legacy `db-20261106T095015Z` record,
  so the next automatic rotation will abort again. It needs either a real
  `sha256`/`stamp` written into the record or a `_prune` that tolerates a
  legacy entry.
- `db-20261108T061315Z` and `db-20261108T111200Z` are held only by
  `.deploy.json.stale-*` files in `cutover-workspace/staging/`. They are
  deletable once those stale staging files are triaged.
- 64 empty `.lifecycle/*.lock` inodes remain for retired names. They are 0-byte
  by design (`retirement.lock_path` says the inode must survive a concurrent
  waiter), so they are not a leak, but the directory is now much larger than
  the 3 live instances.
- Repository documents still cite `/Users/chesterjohn/de-linker-local/p548/...`
  paths. Those citations were checked one by one after the merge and only the
  three acceptance files below need repointing; everything else is either
  reproducible or was already gone.

## Cited p548 paths, checked one by one

`docs/` cites 105 paths under `p548/wordpress/`. Read back after the retirement:

| cited | count | state |
| --- | --- | --- |
| `wp-content/uploads/…` | 83 | all 83 present in the retained live-site snapshot `20261105-1208/uploads/`, so the bytes are one `cp` away |
| `wp-content/plugins/…`, `wp-includes/…` | 15 | WooCommerce and WordPress source; rebuilt by `just up` from released packages |
| `wp-content/mu-plugins/…` | 6 | temporary fixtures whose own acceptance records state they were already removed |
| evidence files under `final-consumer/` and `try-again-evidence/` | 3 | **need repointing** to `~/de-linker-data/retired-instance-evidence/p548/` |

The six mu-plugins were checked by their removal records rather than assumed:

- `linker-planner-cua-recovery-548.php` and `linker-planner-cua-ack-548.php` —
  `docs/acceptance/2026-10-22/548/handover-native/*-cleanup.json` each carry
  `"fixture_removed": true` with a 2026-10-23 timestamp;
- `548-genie-ui-1101.php` — its INDEX entry reads "temporary controller/MU
  removed" and "absent";
- `linker-native-claim-775b68665fdf.php` — its INDEX entry reads "One
  temporary MU…absent";
- `548-genie-race-1102.php` — its INDEX entry reads "MU85B removed";
- `000-linker-local-isolation.php` — not a fixture: `just up` writes it into
  every instance, so it is regenerated rather than lost.

So the only real citation debt is those three acceptance files, and the record
above replaces the earlier blanket claim that every `p548/...` path needed
repointing.

## Unresolved: the p548 evidence count

The copy was verified as 4 907 files with zero sha256 mismatches, and all three
cited evidence files (`final-consumer/browser/record.json`,
`final-consumer/legacy/verdict.json`, `try-again-evidence/report-final.json`)
are present and readable. But the destination now holds 4 674 regular files and
2 symlinks. 233 files are unaccounted for.

What is known: the gap is not a missing directory — no directory under the
destination is empty, `planner/workspace` (1 710 files), `planner/runtime-releases`
(548) and `planner/managed-reference-native` (143) all carry content, and
`runtime.json` survived. The likely explanation is the `-shm`/`-wal` companion
files of `workspace.sqlite`, whose counts change as SQLite touches them, plus
counting differences between the copy-time walk and today's. It is a hypothesis,
not a finding.

It cannot be settled here: the source instance was deleted in this session, so
there is no second copy to re-hash against. This is exactly the kind of claim
that should not be asserted without a check, which is why it is recorded as
open rather than rounded to a confident number. Anyone needing the byte-level
guarantee should treat the three cited files (verified present) as the evidence
that matters, and re-derive any other file's authenticity from
`20261105-1208` or from Git history.
