# Genie paired release 2026-11-05: runtime 06e2b854 + new knowledge generation

Executor: main session. Completion criterion: production read-back of the new
runtime/index pair and a real customer Genie turn on the live site.

**Result: PASS.**

## What shipped

- Runtime current: `/opt/linker-genie/20261105T043742944830Z-06e2b854`
  (main `06e2b8549a93…`, includes PR938's bounded health-startup retry — the
  defect that failed the previous publish at 03:14).
- Index current: `20261105T045620Z-485248000` (296,595,456 B, 143 documents,
  19,193 chunks, all vectors cache-reused; rsync delta 95,008 B).
- Both `linker-genie` and `linker-genie-judge` active; actual PIDs' cwd = the
  new release; no journal warnings in the following 15 minutes.
- `/health` `{"status":"ok"}`, serving revision `3d33d5cb…` (unchanged: PR938
  touched ops only, not the serving source).
- Journal `paired-release.json` removed by the native success path (ready ACK
  + selector verification), not by hand.

## Interrupted predecessor recovery (no lease wait)

The failed 03:14 publish had left knowledge job `3c0bc7ed…` (epoch 93) with a
lease to 05:10:47Z. The native queue was inspected directly and the job read
back as `status=failed, lease_expires_at=0`, lease token removed — the native
interrupted-build cleanup had already retired it. Journal removal and the new
publish proceeded on that verified retirement, without waiting for the lease
timestamp.

## Real customer turn (production read-back)

Real Google Chrome (headed, normal browser presentation) on
`https://de-linker.com/genie/`, fresh session, question "What is the nominal
AC output power of the SAJ ATS1-T63-A?":

1. Probe turn `400` (untrusted identity) → the on-demand challenge ran
   **invisibly and completed by itself** — no interactive widget, no click.
2. Automatic retry `200` ~40s later.
3. Genie answered correctly from the current Woo-hosted datasheet: the SAJ
   ATS1-T63-A datasheet states no nominal AC output power, only a maximum
   input current of 63 A, with the datasheet link attached.

The earlier "stuck at checking/interactive with no widget" observations were
all in automation-flagged browsers (`navigator.webdriver`): Cloudflare stalls
those by design. The chain passes for normal browsers and for automation that
presents as a normal browser; no code change was needed or made.

## Resource report

- New VPS runtime 99 MB; previous `20261104T094242259491Z-8c9e6d80` retained as
  the paired rollback. Superseded unselected candidate `…-dafddafd` is stale
  (pre-PR938 ops) and unreferenced.
- Mac candidate `releases/06e2b8549a93` retained as this release's source;
  old `dafddafd0652` candidate superseded.
- launchd `com.linker.knowledge-publication` re-enabled (ordinary schedule).
