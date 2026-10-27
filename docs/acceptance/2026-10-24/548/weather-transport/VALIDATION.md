# Bounded Apify weather acquisition: component verification

This checkpoint implements and exercises the real transport and durable
orchestrator of the active unified-workbench goal. It does not install the
managed weather executor, native source/recovery controls or a production
workflow. The running p548 site retains its accepted earlier runtime.

## Source and behavior

Base `79e56ea9011d5e241e7ee05d45018b2e6df8b253`; initial source
`a37c4c16a0f0659214ea24791a2bcfd2747bd121`; first correction
`b9329c0e31db8ff42511ac66224e6ce0a00108f0`; final corrected source
`0187cc9210baacf51764bec50da42405a40ac71b`.
[Source fingerprints](source-pin.json) and the [acquisition specification](../../../../specs/548-weather-acquisition.md)
bind the component boundary. [Independent axes and corrections](REVIEWS.md)
retain the initial findings and corrected full-diff reviews separately.

The fixed-origin transport uses private header authentication and no implicit
retries. Redirects are rejected before their bodies are consumed. Encoded and
decoded byte counts are separately bounded; identity/gzip decoding has a
checkpoint between raw reads. Connection/read inactivity bounds and a durable
elapsed deadline are separate controls; blocking DNS/headers are not described
as immediately interruptible or a hard complete-response time guarantee.
Installed requests/urllib3 behavior was inspected before selecting the adapter
path. urllib3 was already locked at 2.8.0; it is now an explicit direct
dependency, with no package upgrade. `uv sync --locked --offline` accepted the
registration using the existing environment.

The existing SQLite journal commits one start permit, immediately retains a
verified acknowledgement and resumes that same remote task after transient
reads. An uncertain POST never repeats. Private recovery requires the known
run and exact unique intent nonce in the complete safe effective INPUT; it
does not requeue, extend the original deadline or grant publication authority.

Polling, dataset and original-record retrieval remain outside write
transactions. One exact origin record and the acknowledged run's own store
must match. Arbitrary dataset URLs, temporary signatures, HTML extraction,
unknown INPUT fields, unsafe hooks/proxies and malformed originals are refused.
Submitted wire JSON and exact verified effective INPUT are retained. Dataset
evidence is explicitly a selected safe projection with the full response's
hash/byte receipt. The existing strict TMY interpreter validates the entire
original before a capture reference is published. No owned asset or task
success is published by this component.

Cancellation and elapsed/poll limits attempt a known run's abort. A returned
ABORTING state remains ABORTING. Lost old leases do not abort work being
resumed by a replacement. Cleanup and cancellation-inspection failures cannot
replace the original exception. Failed network I/O also checks stop state,
because a socket exception can bypass the next read checkpoint. An ordinary
transient failure retains the same acknowledged task. Verified retained
captures can be reused after their network deadline under an active lease.

## Real external capture

[Primary-contract research](../../../../research/2026-10-24-weather-transport/FINDINGS.md)
used one docs-only pinned Actor. The owner then started two separate weather
tasks; each consumed exactly one durable permit. [Actual trials](ACTUAL-TRIAL.md)
explain the historical driver, original execution location and preserved data.

The first provider run SUCCEEDED, yet the origin was HTTP 200/text-html with a
rejection page. The component correctly refused it. A separate explicit local
task restored the header from the retained successful primary request. Its
original JSON passed effective-INPUT equality, nonce correlation, origin/store
identity, full source schema/units/time-axis validation and durable capture.
These observations establish neither header causality nor general availability.

The captured original is 1,268,118 bytes, SHA256
`5406a027f131e780d2a7a79a98d1f79b9e62c6ab7fe4b2f212a1829553321110`.
It equals the existing primary sample, so the [21 verified CAS references](actual/accepted/blob-references.json)
reuse that original instead of duplicate it. Individual research manifest
entries and their total are also verified. Credentials, account objects and
temporary access queries are absent from the retained files.

No real abort or lost acknowledgement was induced during these paid-provider
trials. Those paths use the labelled transport adapter and real SQLite/CAS
fixtures. No component trial is described as native or managed-worker proof.

## Verification and preservation

The [exact commands](commands.json), complete stdout and JUnit case list record
the checks at the final corrected source. Static checks cover the entire
planning source/test surface, and the engine regression covers the complete
engine suite.

| Check | Corrected result |
| --- | --- |
| Complete engine regression | 776 passed, no failures/errors/skips; pytest 73.25 seconds |
| Planning source/test lint | Passed |
| Planning source/test format | 146 files already formatted |
| Strict planning types | No issues in 112 source files |

The 60 new cases exercise bounded raw/gzip reads, malformed/foreign
responses, uncertain POST/recovery, nonce mismatch, exact originals, real
journal/lease races, cancellation, elapsed/poll caps, database and unexpected
cleanup errors, concurrent stop during failed I/O, lease replacement and
invalid original units. They do not claim field yield accuracy.

[Preservation readback](preservation.json) checks all 164 original projects,
the protected roof's saved revision 14 and input SHA, the unchanged runtime
policy and the running worker's module plus runtime/execution/storage/generation
arguments. The weather journal table remains absent from the live database.
No p548 install/restart, live database write, mail, inquiry or production action
was performed. There is no new site instance, worktree or full backup.

After verified evidence export, the isolated trial was retired and its
1,430,334-byte temporary directory removed. [Cleanup readback](cleanup.json)
retains its owner, purpose, exact path, original deduplication and disk readback.
The historical script is retained as text with its former location made clear.

## Work continuing in the same complete goal

The next integration is the frozen managed weather kernel and single registry,
operator recovery controls, explicit saved source selection and native
EN/DE 1440/390 source/model/task paths before paired installation. This
checkpoint does not waive detailed shading/electrical/real SKU/country work,
BOM/report/PDF, site/Genie/Woo/draft/inquiry consumers, migration, review-site
release or production readback. The complete goal remains active.
